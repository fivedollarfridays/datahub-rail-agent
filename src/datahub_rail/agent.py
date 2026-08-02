"""Agent entrypoint: run the probe registry over a DataHub estate.

    python -m datahub_rail.agent --config config/probes.yaml \
        --datahub-url http://localhost:8080

Each run probes every discovered dataset, appends results to the state
history, renders the delta-aware digest (NEW / CHRONIC day N / RECOVERED),
and writes incident reports plus schema-drift fix artifacts to the outbox.
"""
import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

import yaml

from .drift_artifacts import DriftArtifactGenerator
from .graph import GraphClient
from .probes import ProbeRegistry
from .state_history import StateDigest, StateHistory
from .triage import TriageEngine


def load_config(path: Path | str) -> dict:
    """Load the probe registry config from YAML."""
    with open(path) as handle:
        return yaml.safe_load(handle) or {}


def _select_probes(config: dict, dataset_urn: str) -> dict:
    """Probe config for one dataset, skipping contract probes it opts out of."""
    contract_datasets = config.get("schema_contract_datasets")
    probes = []
    for probe in config.get("probes", []):
        if probe.get("type") == "schema" and contract_datasets is not None:
            if dataset_urn not in contract_datasets:
                continue
        probes.append(probe)
    return {"probes": probes}


async def _probe_dataset(graph, config: dict, dataset) -> dict:
    """Run every applicable probe against one dataset."""
    registry = ProbeRegistry(_select_probes(config, dataset.urn))
    results = await registry.check_dataset(graph, dataset.urn)
    failures = {name: r for name, r in results.items() if r.status == "fail"}
    return {
        "urn": dataset.urn,
        "name": dataset.name,
        "status": "fail" if failures else "pass",
        "results": results,
        "failures": failures,
    }


def _format_line(entry: dict) -> str:
    """One terminal line summarising a dataset's probe results."""
    if entry["status"] == "pass":
        checks = ", ".join(f"{n} OK" for n in entry["results"])
        return f"[PASS] {entry['name']} — {checks}"
    first = next(iter(entry["failures"].items()))
    return f"[FAIL] {entry['name']} — {first[0]}: {first[1].message}"


async def _write_incident(graph, engine, entry: dict, outbox: Path) -> None:
    """Generate the owner-addressed incident report for a failing dataset."""
    probe_name, result = next(iter(entry["failures"].items()))
    entity = await graph.get_entity(entry["urn"])
    await engine.generate_incident_report(
        client=graph,
        failing_dataset_urn=entry["urn"],
        failing_dataset_name=entry["name"],
        dataset_owner=entity.get("owner", ""),
        probe_name=probe_name,
        probe_status=result.status,
        probe_message=result.message,
        outbox_dir=outbox,
        provenance=graph.provenance_for(entry["urn"]),
    )


async def _write_drift_artifacts(graph, config: dict, entry: dict, outbox: Path) -> bool:
    """Emit PR-ready fix artifacts when a schema contract has drifted."""
    schema_failures = [
        (n, r) for n, r in entry["failures"].items() if "drift" in r.message.lower()
    ]
    if not schema_failures:
        return False

    expected = {}
    for probe in config.get("probes", []):
        if probe.get("type") == "schema":
            expected = probe.get("params", {}).get("expected_fields", {}) or {}
    if not expected:
        return False

    field_name = next(iter(expected))
    schema = await graph.fetch_schema(entry["urn"])
    actual = next(
        (f["type"] for f in schema.fields if f["field_path"] == field_name), "unknown"
    )
    downstream = config.get("drift_downstream_name", f"{entry['name']}_warehouse")
    contract_path = config.get(
        "drift_contract_path", f"contracts/{downstream}.schema.yaml"
    )
    contract_file = Path(contract_path)
    contract_text = contract_file.read_text() if contract_file.exists() else None

    await DriftArtifactGenerator().generate_all_artifacts(
        {
            "field_name": field_name,
            "expected_type": expected[field_name],
            "actual_type": actual,
            "upstream_dataset": entry["name"],
            "downstream_dataset": downstream,
            "upstream_owner": (await graph.get_entity(entry["urn"])).get("owner", ""),
            "contract_path": contract_path,
            "contract_text": contract_text,
        },
        outbox,
    )
    return True


async def execute(
    graph,
    config: dict,
    outbox: Path | str = "outbox",
    history_path: Path | str = "state_history.jsonl",
) -> dict:
    """Probe the estate, persist history, and emit reports. Returns a summary."""
    outbox = Path(outbox)
    history = StateHistory(history_path)
    engine = TriageEngine()

    datasets = await graph.list_datasets(query=config.get("discovery_query", "*"))
    datasets = sorted(datasets, key=lambda d: d.name)
    entries = [await _probe_dataset(graph, config, d) for d in datasets]

    for entry in entries:
        for probe_name, result in entry["results"].items():
            history.append(entry["urn"], probe_name, result.status, result.message)

    artifacts = False
    for entry in entries:
        if entry["status"] != "fail":
            continue
        await _write_incident(graph, engine, entry, outbox)
        artifacts = await _write_drift_artifacts(graph, config, entry, outbox) or artifacts

    digest = StateDigest(history_path).render()
    failed = [e for e in entries if e["status"] == "fail"]
    return {
        "datasets": entries,
        "digest": digest,
        "artifacts_written": artifacts,
        "exit_code": 1 if failed else 0,
    }


async def run(args: argparse.Namespace) -> int:
    """Wire a live graph client and execute one run."""
    config = load_config(args.config)
    graph = GraphClient.create(gms_url=args.datahub_url, token=args.token)

    await graph.connect()
    try:
        report = await execute(graph, config, outbox=args.outbox, history_path=args.history)
    finally:
        await graph.disconnect()

    for entry in report["datasets"]:
        print(_format_line(entry))

    print("\n--- Delta-aware state digest ---")
    print(report["digest"] or "(no history yet)")
    print(f"\n[INFO] Incident reports and fix artifacts: {args.outbox}/")
    print(f"[INFO] State history: {args.history}")
    return report["exit_code"]


def main(argv: Optional[list[str]] = None) -> int:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(prog="python -m datahub_rail.agent")
    parser.add_argument("--config", default="config/probes.yaml", help="probe registry YAML")
    parser.add_argument("--datahub-url", default="http://localhost:8080", help="GMS base URL")
    parser.add_argument("--token", default="", help="DataHub token (empty for local quickstart)")
    parser.add_argument("--outbox", default="outbox", help="directory for reports and artifacts")
    parser.add_argument("--history", default="state_history.jsonl", help="state history JSONL")
    args = parser.parse_args(argv)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
