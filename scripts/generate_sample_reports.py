"""Generate sample incident reports against DHA.2 seeded faults."""
import asyncio
from pathlib import Path
from datahub_rail.client import MCPClient
from datahub_rail.triage import TriageEngine


async def main():
    """Generate sample reports for seeded faults."""
    client = MCPClient()
    await client.connect()

    engine = TriageEngine()
    outbox = Path("sample-outputs")
    outbox.mkdir(exist_ok=True)

    try:
        # DHA.2 plants three faults:
        # 1. stale-dataset (freshness fault)
        # 2. broken-lineage-dataset (lineage fault)
        # 3. schema-drift-dataset (schema fault)

        datasets = await client.list_datasets()

        for dataset in datasets:
            urn = dataset.urn
            name = dataset.name

            # Check freshness for each dataset
            try:
                freshness = await client.get_freshness(urn)
                if freshness.is_stale:
                    # Generate report for stale dataset
                    report = await engine.generate_incident_report(
                        client,
                        failing_dataset_urn=urn,
                        failing_dataset_name=name,
                        dataset_owner=dataset.owner,
                        probe_name="freshness",
                        probe_status="fail",
                        probe_message=f"Dataset is stale (last_modified: {freshness.last_modified})",
                        outbox_dir=outbox,
                    )
                    print(f"✓ Generated report for stale dataset: {name}")
            except Exception as e:
                print(f"  Skipped freshness check for {name}: {e}")

            # Check lineage for each dataset
            try:
                lineage = await client.walk_upstream(urn, hops=1)
                if not lineage.upstream:
                    report = await engine.generate_incident_report(
                        client,
                        failing_dataset_urn=urn,
                        failing_dataset_name=name,
                        dataset_owner=dataset.owner,
                        probe_name="lineage",
                        probe_status="fail",
                        probe_message="Dataset has no upstream dependencies (lineage missing or broken)",
                        outbox_dir=outbox,
                    )
                    print(f"✓ Generated report for broken lineage: {name}")
            except Exception as e:
                print(f"  Skipped lineage check for {name}: {e}")

    finally:
        await client.disconnect()

    print(f"\n✓ All sample reports saved to {outbox}/")
    print(f"  Files: {len(list(outbox.glob('*.md')))}")


if __name__ == "__main__":
    asyncio.run(main())
