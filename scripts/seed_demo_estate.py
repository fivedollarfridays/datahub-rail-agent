#!/usr/bin/env python3
"""Seed demo data estate with 3 fault classes and healthy controls."""
import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

from datahub_rail.seeder import DatasetSeeder


async def seed_healthy_control(seeder: DatasetSeeder) -> list[dict]:
    """Seed healthy control dataset (users table with current freshness)."""
    healthy_controls = []
    healthy_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)"
    await seeder.ingest_dataset(
        urn=healthy_urn,
        name="users",
        platform="postgres",
        owner="data-eng",
    )
    await seeder.add_schema(
        dataset_urn=healthy_urn,
        fields=[
            {"field_path": "id", "type": "bigint", "description": "User ID"},
            {"field_path": "email", "type": "varchar", "description": "User email"},
        ],
        description="Users table with current data",
    )
    healthy_controls.append({"urn": healthy_urn, "name": "users"})
    return healthy_controls


async def seed_stale_fault(seeder: DatasetSeeder) -> dict:
    """Seed stale freshness fault (orders_archive, 45 days old)."""
    stale_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
    old_timestamp = int(
        (datetime.now(timezone.utc) - timedelta(days=45)).timestamp() * 1000
    )
    await seeder.ingest_dataset(
        urn=stale_urn,
        name="orders_archive",
        platform="postgres",
        owner="data-eng",
        last_modified=old_timestamp,
    )
    await seeder.add_schema(
        dataset_urn=stale_urn,
        fields=[
            {"field_path": "id", "type": "bigint", "description": "Order ID"},
            {"field_path": "total", "type": "decimal", "description": "Order total"},
        ],
        description="Archived orders (stale: not updated in 45 days)",
    )
    return {
        "type": "stale",
        "urn": stale_urn,
        "description": "Dataset last modified 45 days ago (beyond SLA)",
    }


async def seed_broken_lineage_fault(seeder: DatasetSeeder) -> dict:
    """Seed broken lineage fault (delete upstream after creating edge)."""
    deleted_src_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.raw_events_old,PROD)"
    broken_downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)"

    await seeder.ingest_dataset(
        urn=deleted_src_urn,
        name="raw_events_old",
        platform="postgres",
        owner="data-eng",
    )

    await seeder.ingest_dataset(
        urn=broken_downstream_urn,
        name="events",
        platform="postgres",
        owner="data-eng",
    )

    await seeder.create_lineage(
        upstream_urn=deleted_src_urn,
        downstream_urn=broken_downstream_urn,
    )

    await seeder.delete_dataset(urn=deleted_src_urn)

    return {
        "type": "broken_lineage",
        "upstream_urn": deleted_src_urn,
        "downstream_urn": broken_downstream_urn,
        "description": "Upstream dataset was deleted; lineage edge is broken",
    }


async def seed_schema_drift_fault(seeder: DatasetSeeder) -> dict:
    """Seed schema-contract drift (type mismatch between up/downstream)."""
    drift_src_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)"
    drift_dst_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)"

    await seeder.ingest_dataset(
        urn=drift_src_urn,
        name="transactions",
        platform="postgres",
        owner="data-eng",
    )
    await seeder.add_schema(
        dataset_urn=drift_src_urn,
        fields=[
            {"field_path": "id", "type": "bigint", "description": "Transaction ID"},
            {"field_path": "amount", "type": "int", "description": "Amount (changed from decimal)"},
        ],
        description="Source transactions table",
    )

    await seeder.ingest_dataset(
        urn=drift_dst_urn,
        name="transactions_warehouse",
        platform="postgres",
        owner="analytics",
    )
    await seeder.add_schema(
        dataset_urn=drift_dst_urn,
        fields=[
            {"field_path": "id", "type": "bigint", "description": "Transaction ID"},
            {"field_path": "amount", "type": "decimal(12,2)", "description": "Amount (expects decimal)"},
        ],
        description="Warehouse transactions (expects decimal amount)",
    )

    await seeder.create_lineage(
        upstream_urn=drift_src_urn,
        downstream_urn=drift_dst_urn,
    )

    return {
        "type": "schema_drift",
        "upstream_urn": drift_src_urn,
        "downstream_urn": drift_dst_urn,
        "description": "Upstream column 'amount' changed from decimal to int; downstream still expects decimal",
    }


async def seed_demo_estate(gms_url: str = "http://localhost:8080") -> dict:
    """Seed demo data estate with 3 fault classes and healthy controls."""
    seeder = DatasetSeeder(gms_url=gms_url)
    await seeder.connect()

    try:
        healthy_controls = await seed_healthy_control(seeder)
        fault_classes = []

        # 2. Stale freshness fault
        fault_classes.append(await seed_stale_fault(seeder))

        # 3. Broken lineage fault
        fault_classes.append(await seed_broken_lineage_fault(seeder))

        # 4. Schema-contract drift fault
        fault_classes.append(await seed_schema_drift_fault(seeder))

        return {
            "status": "success",
            "healthy_controls": healthy_controls,
            "fault_classes": fault_classes,
        }

    finally:
        await seeder.disconnect()


async def main() -> int:
    """Run the seed script."""
    gms_url = os.environ.get("DATAHUB_GMS_URL", "http://localhost:8080")
    try:
        result = await seed_demo_estate(gms_url=gms_url)
        print("✓ Seeded dataset: users (healthy control)")
        print("✓ Seeded dataset: orders_archive (stale: 45 days old)")
        print("✓ Seeded dataset: events (broken lineage: upstream soft-deleted)")
        print("✓ Seeded dataset: transactions (schema drift: int vs decimal(12,2))")
        print("✓ Seeded dataset: transactions_warehouse (downstream consumer)")
        print(
            f"\nSeeded {len(result['healthy_controls'])} healthy control(s) "
            f"and {len(result['fault_classes'])} fault class(es) into {gms_url}"
        )
        return 0
    except Exception as e:
        print(f"✗ Seed failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
