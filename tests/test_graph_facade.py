"""GraphClient: probe-facing facade over MCP + GMS, recording provenance.

Every read is journalled as (tool, dataset_urn, timestamp) so incident
reports can prove each claim traces back to a graph read.
"""
import pytest

from datahub_rail.graph import GraphClient
from datahub_rail.types import Freshness, LineageResult, SchemaMetadata

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
UP = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.raw_events_old,PROD)"


class _FakeMCP:
    async def list_datasets(self, query="*", num_results=50):
        return []

    async def get_entity(self, urn):
        return {"urn": urn, "name": "orders_archive", "platform": "postgres", "owner": "data-eng"}

    async def fetch_schema(self, urn):
        return SchemaMetadata(urn=urn, fields=[{"field_path": "id", "type": "bigint", "description": ""}], description="")

    async def walk_upstream(self, urn, hops=1):
        return LineageResult(urn=urn, upstream=[], downstream=[])


class _FakeGMS:
    async def get_freshness(self, urn):
        return Freshness(urn=urn, last_modified=1700000000000, is_stale=False, expected_frequency=0)

    async def get_declared_upstreams(self, urn):
        return [UP]


def _graph():
    return GraphClient(mcp=_FakeMCP(), gms=_FakeGMS())


@pytest.mark.asyncio
async def test_freshness_delegates_to_gms():
    """Freshness is a GMS aspect read."""
    g = _graph()
    assert (await g.get_freshness(URN)).last_modified == 1700000000000


@pytest.mark.asyncio
async def test_declared_upstreams_delegates_to_gms():
    """Declared edges are a GMS aspect read."""
    assert await _graph().get_declared_upstreams(URN) == [UP]


@pytest.mark.asyncio
async def test_schema_and_lineage_delegate_to_mcp():
    """Schema and resolved lineage come from MCP tools."""
    g = _graph()
    assert (await g.fetch_schema(URN)).fields[0]["field_path"] == "id"
    assert (await g.walk_upstream(URN)).upstream == []


@pytest.mark.asyncio
async def test_every_read_is_recorded_in_provenance():
    """Each graph read appends a provenance entry naming its source tool."""
    g = _graph()
    await g.get_freshness(URN)
    await g.fetch_schema(URN)
    await g.walk_upstream(URN)
    await g.get_declared_upstreams(URN)

    tools = [p.tool for p in g.provenance]
    assert tools == [
        "gms:datasetProperties.lastModified",
        "mcp:list_schema_fields",
        "mcp:get_lineage",
        "gms:upstreamLineage",
    ]
    assert all(p.dataset_urn == URN for p in g.provenance)
    assert all(p.timestamp for p in g.provenance)


@pytest.mark.asyncio
async def test_provenance_for_filters_by_dataset():
    """Provenance can be scoped to one dataset for its incident report."""
    g = _graph()
    await g.get_freshness(URN)
    await g.get_freshness("urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)")

    assert len(g.provenance_for(URN)) == 1
