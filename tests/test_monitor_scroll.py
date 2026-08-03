"""Scrolling the estate for rail write-back markers.

The liveness check has to see every dataset the agent could have written to,
without an MCP server in the loop — a monitor check that needs the full agent
toolchain is one more thing that can die quietly.
"""
import pytest
from unittest.mock import MagicMock

from datahub_rail.gms import GMSReader


class _Response:
    def __init__(self, payload, status=200):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload


class _Get:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return False


def _reader(pages):
    """Reader whose session replays a fixed sequence of scroll pages."""
    session = MagicMock()
    responses = [_Get(_Response(p)) for p in pages]
    session.get = MagicMock(side_effect=responses)
    reader = GMSReader(gms_url="http://localhost:8080")
    reader.session = session
    return reader, session


@pytest.mark.asyncio
async def test_scroll_follows_pages_until_exhausted():
    """Every page of the estate is walked, not just the first."""
    reader, _ = _reader(
        [
            {"scrollId": "page2", "entities": [{"urn": "urn:a"}]},
            {"scrollId": None, "entities": [{"urn": "urn:b"}]},
        ]
    )

    entities = await reader.scroll_datasets(["structuredProperties"], count=1)

    assert [e["urn"] for e in entities] == ["urn:a", "urn:b"]


@pytest.mark.asyncio
async def test_scroll_always_requests_the_key_aspect():
    """GMS returns zero entities for an aspect-only scroll — datasetKey anchors it.

    Verified against DataHub 1.5 quickstart: requesting only
    ``structuredProperties`` returns ``entities: []`` with a non-zero
    ``totalCount``. Adding ``datasetKey`` returns the estate.
    """
    reader, session = _reader([{"scrollId": None, "entities": []}])

    await reader.scroll_datasets(["structuredProperties"])

    url = session.get.call_args[0][0]
    assert "aspects=datasetKey" in url
    assert "aspects=structuredProperties" in url
    assert "/openapi/v3/entity/dataset?" in url


@pytest.mark.asyncio
async def test_scroll_stops_on_an_error_response():
    """A failing GMS yields no entities rather than an infinite loop."""
    reader, _ = _reader([{"scrollId": "next", "entities": []}])

    assert await reader.scroll_datasets(["structuredProperties"]) == []
