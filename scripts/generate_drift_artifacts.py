#!/usr/bin/env python3
"""Generate schema-drift fix artifacts from seeded demo data."""
import asyncio
import sys
from pathlib import Path

from datahub_rail.drift_artifacts import DriftArtifactGenerator


async def generate_drift_artifacts() -> int:
    """Generate sample fix artifacts for schema-drift fault class."""
    generator = DriftArtifactGenerator()

    # Schema-drift fault from seed_demo_estate:
    # upstream transactions has amount: int
    # downstream transactions_warehouse expects amount: decimal(12,2)
    drift_info = {
        "field_name": "amount",
        "expected_type": "decimal(12,2)",
        "actual_type": "int",
        "downstream_dataset": "transactions_warehouse",
        "downstream_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)",
        "upstream_dataset": "transactions",
        "upstream_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)",
        "upstream_owner": "@data-eng",
    }

    # Generate artifacts to outbox
    outbox_dir = Path.cwd() / "outbox"
    outbox_dir.mkdir(exist_ok=True)

    try:
        artifacts = await generator.generate_all_artifacts(drift_info, outbox_dir)

        print("✓ Schema-drift fix artifacts generated")
        print(f"  Patch file: {artifacts['patch'].name}")
        print(f"  Diff file:  {artifacts['diff'].name}")
        print(f"  Message:    {artifacts['message'].name}")

        # Also generate the other fault types for completeness
        artifacts_stale = await generate_stale_artifacts(generator, outbox_dir)
        print(f"  (Stale artifact also generated: {artifacts_stale['message'].name})")

        artifacts_lineage = await generate_lineage_artifacts(generator, outbox_dir)
        print(f"  (Lineage artifact also generated: {artifacts_lineage['message'].name})")

        return 0

    except Exception as e:
        print(f"✗ Failed to generate artifacts: {e}", file=sys.stderr)
        return 1


async def generate_stale_artifacts(generator, outbox_dir):
    """Generate fix artifacts for stale-freshness fault."""
    drift_info = {
        "field_name": "refresh_frequency",
        "expected_type": "24h",
        "actual_type": "45d",
        "downstream_dataset": "orders_archive",
        "downstream_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)",
        "upstream_dataset": "orders_archive",
        "upstream_owner": "@data-eng",
    }

    return await generator.generate_all_artifacts(drift_info, outbox_dir)


async def generate_lineage_artifacts(generator, outbox_dir):
    """Generate fix artifacts for broken-lineage fault."""
    drift_info = {
        "field_name": "upstream_reference",
        "expected_type": "exists",
        "actual_type": "deleted",
        "downstream_dataset": "events",
        "downstream_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)",
        "upstream_dataset": "raw_events_old",
        "upstream_owner": "@data-eng",
    }

    return await generator.generate_all_artifacts(drift_info, outbox_dir)


async def main() -> int:
    """Entry point."""
    return await generate_drift_artifacts()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
