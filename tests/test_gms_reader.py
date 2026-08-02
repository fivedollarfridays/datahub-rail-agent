"""GMSReader: aspect reads the MCP tool surface does not expose.

mcp-server-datahub v3.4.5 returns entity properties without
``lastModified``, and ``get_lineage`` only returns upstreams that still
resolve. Capture-based freshness and dangling-edge detection therefore read
the ``datasetProperties`` and ``upstreamLineage`` aspects straight from GMS.
"""
import pytest
from unittest.mock import MagicMock

from datahub_rail.gms import GMSReader

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
UP = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.raw_events_old,PROD)"


class _Response:
    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload or {}

    async def json(self):
        return self._payload

    async def text(self):
        return str(self._payload)


class _Get:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return False


def _reader(response):
    session = MagicMock()
    session.get = MagicMock(return_value=_Get(response))
    reader = GMSReader(gms_url="http://localhost:8080")
    reader.session = session
    return reader, session


@pytest.mark.asyncio
async def test_get_freshness_reads_last_modified_time():
    """Freshness comes from datasetProperties.lastModified.time."""
    payload = {"urn": URN, "datasetProperties": {"value": {"lastModified": {"time": 1700000000000}}}}
    reader, _ = _reader(_Response(payload=payload))

    freshness = await reader.get_freshness(URN)

    assert freshness.urn == URN
    assert freshness.last_modified == 1700000000000


@pytest.mark.asyncio
async def test_get_freshness_urlencodes_the_urn():
    """The URN must be percent-encoded into the entity path."""
    payload = {"urn": URN, "datasetProperties": {"value": {"lastModified": {"time": 1}}}}
    reader, session = _reader(_Response(payload=payload))

    await reader.get_freshness(URN)

    url = session.get.call_args[0][0]
    assert "/openapi/v3/entity/dataset/" in url
    assert "%3A" in url and " " not in url


@pytest.mark.asyncio
async def test_get_freshness_missing_aspect_raises():
    """A dataset with no lastModified must fail loud, not report fresh."""
    reader, _ = _reader(_Response(payload={"urn": URN}))

    with pytest.raises(RuntimeError):
        await reader.get_freshness(URN)


@pytest.mark.asyncio
async def test_get_declared_upstreams_returns_edge_targets():
    """Declared edges come from the upstreamLineage aspect."""
    payload = {
        "urn": URN,
        "upstreamLineage": {"value": {"upstreams": [{"dataset": UP, "type": "TRANSFORMED"}]}},
    }
    reader, _ = _reader(_Response(payload=payload))

    assert await reader.get_declared_upstreams(URN) == [UP]


@pytest.mark.asyncio
async def test_get_declared_upstreams_empty_when_aspect_absent():
    """A source dataset declares no upstream and yields an empty list."""
    reader, _ = _reader(_Response(payload={"urn": URN}))

    assert await reader.get_declared_upstreams(URN) == []


@pytest.mark.asyncio
async def test_declared_upstreams_empty_on_404():
    """A missing entity yields no declared edges rather than raising."""
    reader, _ = _reader(_Response(status=404, payload={"error": "not found"}))

    assert await reader.get_declared_upstreams(URN) == []
