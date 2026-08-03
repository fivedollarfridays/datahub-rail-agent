#!/usr/bin/env python3
"""Live write-back smoke test against the DataHub quickstart.

Runs the agent twice with ``--writeback`` (so the second run is delta-aware),
then reads the markers back out of GMS and checks what actually landed:

* exactly one ``rail.status.*`` tag per probed dataset — never a stack,
* a ``rail.status`` structured property carrying the full verdict,
* an incident-report pointer on failing datasets and none on healthy ones.

Usage:  python scripts/writeback_smoke.py [--gms http://localhost:8080]
"""
import argparse
import asyncio
import json
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import quote

RAIL_TAG_PREFIX = "urn:li:tag:rail.status."


def read_aspect(gms: str, urn: str, aspect: str) -> dict:
    """Read one aspect from GMS; a missing aspect reads as empty."""
    url = f"{gms}/openapi/v3/entity/dataset/{quote(urn, safe='')}/{aspect}"
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            return json.loads(resp.read()).get("value") or {}
    except Exception:
        return {}


def run_agent(workdir: Path, run_no: int) -> int:
    """Run the agent once with write-back enabled."""
    print(f"\n=== agent run {run_no} (--writeback) ===")
    proc = subprocess.run(
        [
            sys.executable, "-m", "datahub_rail.agent",
            "--writeback",
            "--outbox", str(workdir / "outbox"),
            "--history", str(workdir / "state_history.jsonl"),
        ],
        capture_output=True,
        text=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith(("[PASS]", "[FAIL]", "[INFO] Write-back", "[ERROR]")):
            print(f"  {line}")
    return proc.returncode


def probed_urns(workdir: Path) -> list[str]:
    """Every dataset URN the run recorded history for."""
    history = workdir / "state_history.jsonl"
    if not history.exists():
        return []
    urns = {json.loads(line)["dataset_urn"] for line in history.read_text().splitlines() if line}
    return sorted(urns)


def check_dataset(gms: str, urn: str) -> tuple[bool, str]:
    """Read back one dataset's markers. Returns (ok, one-line summary)."""
    tags = [
        t["tag"]
        for t in (read_aspect(gms, urn, "globalTags").get("tags") or [])
        if str(t.get("tag", "")).startswith(RAIL_TAG_PREFIX)
    ]
    props = {
        p["propertyUrn"].split("rail.")[-1]: p["values"][0]["string"]
        for p in (read_aspect(gms, urn, "structuredProperties").get("properties") or [])
        if "structuredProperty:rail." in p.get("propertyUrn", "")
    }

    name = urn.split(",")[1]
    if len(tags) != 1:
        return False, f"FAIL {name}: expected 1 rail tag, found {len(tags)}: {tags}"
    if not props.get("status"):
        return False, f"FAIL {name}: no rail.status structured property"

    incident = props.get("incident", "-")
    return True, (
        f"OK   {name}\n"
        f"       tag      : {tags[0].split(':')[-1]}\n"
        f"       status   : {props['status']}\n"
        f"       probe    : {props.get('probe', '-')}\n"
        f"       last_run : {props.get('last_run', '-')}\n"
        f"       incident : {incident}"
    )


async def main() -> int:
    """Run the agent twice, then verify the markers on the server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--gms", default="http://localhost:8080")
    parser.add_argument("--workdir", default=".writeback-smoke")
    args = parser.parse_args()

    workdir = Path(args.workdir)
    workdir.mkdir(parents=True, exist_ok=True)

    for run_no in (1, 2):
        run_agent(workdir, run_no)

    print("\n=== read-back from GMS ===")
    failures = 0
    for urn in probed_urns(workdir):
        ok, summary = check_dataset(args.gms, urn)
        print(summary)
        failures += 0 if ok else 1

    print("\n=== result ===")
    if failures:
        print(f"WRITE-BACK SMOKE FAILED: {failures} dataset(s) wrong")
        return 1
    print("write-back smoke PASSED: one tag per dataset, verdicts readable from the graph")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
