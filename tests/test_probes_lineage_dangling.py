"""LineageProbe: declared-vs-resolved edge comparison.

A source dataset with no declared upstream is healthy (it is the origin).
A dataset that *declares* an upstream edge which no longer resolves is the
broken-lineage fault: the edge points at a deleted entity.
"""
import pytest

from datahub_rail.probes import LineageProbe
from datahub_rail.types import LineageResult

UP = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.raw_events_old,PROD)"


class _Client:
    def __init__(self, declared, resolved):
        self._declared = declared
        self._resolved = resolved

    async def get_declared_upstreams(self, urn: str) -> list[str]:
        return self._declared

    async def walk_upstream(self, urn: str, hops: int = 1) -> LineageResult:
        return LineageResult(urn=urn, upstream=self._resolved, downstream=[])


@pytest.mark.asyncio
async def test_source_dataset_with_no_declared_upstream_passes():
    """Healthy control: a source table declares no upstream and must PASS."""
    probe = LineageProbe()
    result = await probe.check(_Client(declared=[], resolved=[]), "urn:test")

    assert result.status == "pass"
    assert "no declared upstream" in result.message.lower()


@pytest.mark.asyncio
async def test_declared_edge_that_does_not_resolve_fails():
    """Broken lineage: declared upstream missing from resolved graph."""
    probe = LineageProbe()
    result = await probe.check(_Client(declared=[UP], resolved=[]), "urn:test")

    assert result.status == "fail"
    assert "missing" in result.message.lower()
    assert "raw_events_old" in result.message


@pytest.mark.asyncio
async def test_declared_edge_that_resolves_passes():
    """Intact lineage: declared upstream resolves in the graph."""
    resolved = [{"urn": UP, "name": "raw_events_old", "platform": "postgres"}]
    probe = LineageProbe()
    result = await probe.check(_Client(declared=[UP], resolved=resolved), "urn:test")

    assert result.status == "pass"
    assert "verified" in result.message.lower()


@pytest.mark.asyncio
async def test_dangling_message_names_every_missing_upstream():
    """All missing upstreams are named so triage can act on them."""
    other = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.gone,PROD)"
    probe = LineageProbe()
    result = await probe.check(_Client(declared=[UP, other], resolved=[]), "urn:test")

    assert result.status == "fail"
    assert "raw_events_old" in result.message and "gone" in result.message
