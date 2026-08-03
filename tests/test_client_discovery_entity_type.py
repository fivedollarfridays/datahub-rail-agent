"""Discovery must return datasets and nothing else.

The MCP ``search`` tool is a search across *all* entity types. An estate
token that fuzzy-matches a tag, glossary term or domain drags those entities
back as discovery hits, and the agent then probes them as if they were
datasets — they have no ``datasetProperties``, so every one reports a bogus
"No lastModified timestamp" failure.

This is self-inflicted: the write-back feature creates ``urn:li:tag:rail.*``
tags, so the agent's own output pollutes its next discovery pass. Verified
live against the local quickstart: the bare query ``rail`` returns the four
``rail.status.*`` tags ranked *above* every real dataset, and
``entity_type = dataset`` removes exactly those four while leaving all 14
datasets in place.
"""
import json

import pytest

from datahub_rail.client import MCPClient

RAIL_TAGS = [
    "urn:li:tag:rail.status.PASS",
    "urn:li:tag:rail.status.NEW-FAIL",
    "urn:li:tag:rail.status.CHRONIC",
    "urn:li:tag:rail.status.RECOVERED",
]
FINGERPRINT = "urn:li:dataset:(urn:li:dataPlatform:file,data/voice/fingerprint.json,PROD)"
INTERACTIONS = "urn:li:dataset:(urn:li:dataPlatform:sqlite,ops.db.interactions,PROD)"


class _Text:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, payload):
        self.content = [_Text(json.dumps(payload))]
        self.is_error = False


class _RecordingSession:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return _Result(self.payload)


def _client(payload):
    client = MCPClient()
    session = _RecordingSession(payload)
    client.session = session
    return client, session


@pytest.mark.asyncio
async def test_search_is_constrained_to_dataset_entities():
    """The server-side filter is what keeps non-datasets out of the results."""
    client, session = _client({"searchResults": []})

    await client.list_datasets(query="rail")

    tool, arguments = session.calls[0]
    assert tool == "search"
    assert arguments["filter"] == "entity_type = dataset"
    assert arguments["query"] == "rail"


@pytest.mark.asyncio
async def test_writeback_tags_are_never_discovered_as_datasets():
    """Regression: the agent's own rail.status tags must never be probed."""
    payload = {
        "searchResults": (
            [{"entity": {"urn": urn, "properties": {"name": urn.split(":")[-1]}}} for urn in RAIL_TAGS]
            + [
                {"entity": {"urn": FINGERPRINT, "properties": {"name": "data/voice/fingerprint.json"}}},
                {"entity": {"urn": INTERACTIONS, "properties": {"name": "ops.db.interactions"}}},
            ]
        )
    }
    client, _ = _client(payload)

    datasets = await client.list_datasets(query="rail")

    assert [d.urn for d in datasets] == [FINGERPRINT, INTERACTIONS]
    assert not [d for d in datasets if ":tag:" in d.urn]


@pytest.mark.asyncio
async def test_demo_discovery_query_still_passes_through():
    """The verified demo query is unchanged — only the entity filter is new."""
    orders = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
    payload = {"searchResults": [{"entity": {"urn": orders, "properties": {"name": "orders_archive"}}}]}
    client, session = _client(payload)

    datasets = await client.list_datasets(query="demo.public", num_results=50)

    assert session.calls[0][1]["query"] == "demo.public"
    assert session.calls[0][1]["num_results"] == 50
    assert [d.name for d in datasets] == ["orders_archive"]
