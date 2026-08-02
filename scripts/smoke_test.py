#!/usr/bin/env python3
"""Smoke test against live DataHub quickstart instance."""
import asyncio
import sys

from datahub_rail.client import MCPClient


async def main() -> int:
    """Run smoke test against DataHub MCP server."""
    client = MCPClient()
    try:
        print("Connecting to DataHub MCP server...")
        await client.connect()

        print("\n1. Listing datasets...")
        datasets = await client.list_datasets()
        print(f"   Found {len(datasets)} datasets")
        if datasets:
            d = datasets[0]
            print(f"   - {d.name} ({d.platform}) owned by {d.owner}")

            print(f"\n2. Checking freshness of {d.name}...")
            freshness = await client.get_freshness(d.urn)
            print(f"   Last modified: {freshness.last_modified}")
            print(f"   Is stale: {freshness.is_stale}")
            print(f"   Expected frequency: {freshness.expected_frequency}s")

            print(f"\n3. Fetching schema for {d.name}...")
            schema = await client.fetch_schema(d.urn)
            print(f"   Description: {schema.description}")
            print(f"   Fields: {len(schema.fields)}")
            for f in schema.fields[:3]:
                print(f"     - {f['field_path']}: {f['type']}")

            print(f"\n4. Walking upstream lineage for {d.name}...")
            upstream = await client.walk_upstream(d.urn, hops=1)
            print(f"   Upstream: {len(upstream.upstream)} node(s)")
            for n in upstream.upstream:
                print(f"     - {n['name']} ({n['platform']})")

            print(f"\n5. Walking downstream lineage for {d.name}...")
            downstream = await client.walk_downstream(d.urn, hops=1)
            print(f"   Downstream: {len(downstream.downstream)} node(s)")
            for n in downstream.downstream:
                print(f"     - {n['name']} ({n['platform']})")

        print("\n✓ All smoke tests passed")
        return 0

    except Exception as e:
        print(f"\n✗ Smoke test failed: {e}", file=sys.stderr)
        return 1
    finally:
        await client.disconnect()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
