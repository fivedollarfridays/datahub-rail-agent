#!/usr/bin/env python3
"""Regenerate sample-outputs/ from a real run against a live DataHub.

Judges compare committed samples against what the code actually produces, so
these must never be hand-written. This runs the agent end to end and promotes
the resulting artifacts, stripping the run timestamp from incident filenames
so the committed set is stable across runs.

    DATAHUB_GMS_URL=http://localhost:8080 python scripts/refresh_sample_outputs.py
"""
import asyncio
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

from datahub_rail.agent import execute, load_config
from datahub_rail.graph import GraphClient

SAMPLES = Path("sample-outputs")
_STAMP = re.compile(r"_\d{8}_\d{6}\.md$")


async def main() -> int:
    """Run the agent and copy its artifacts into sample-outputs/."""
    gms_url = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")
    config = load_config(os.environ.get("PROBE_CONFIG", "config/probes.yaml"))
    graph = GraphClient.create(gms_url=gms_url, token=os.environ.get("DATAHUB_GMS_TOKEN", ""))

    with tempfile.TemporaryDirectory() as tmp:
        outbox = Path(tmp) / "outbox"
        history = Path(tmp) / "state_history.jsonl"

        await graph.connect()
        try:
            # Two runs: the second gives the digest its "still failing (day 2)" state.
            await execute(graph, config, outbox=outbox, history_path=history)
            report = await execute(graph, config, outbox=outbox, history_path=history)
        finally:
            await graph.disconnect()

        if not report["datasets"]:
            print("✗ No datasets discovered — is the demo estate seeded?", file=sys.stderr)
            return 1

        SAMPLES.mkdir(exist_ok=True)
        for stale in SAMPLES.glob("*"):
            if stale.is_file():
                stale.unlink()

        seen = set()
        for artifact in sorted(outbox.iterdir()):
            target = SAMPLES / _STAMP.sub(".md", artifact.name)
            if target.name in seen:
                continue
            seen.add(target.name)
            shutil.copyfile(artifact, target)
            print(f"✓ {target}")

        (SAMPLES / "state_digest.txt").write_text(report["digest"] + "\n")
        print(f"✓ {SAMPLES / 'state_digest.txt'}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
