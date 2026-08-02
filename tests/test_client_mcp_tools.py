"""MCPClient adapts the real mcp-server-datahub tool surface.

The server exposes search / get_entities / get_lineage / list_schema_fields
and returns JSON as text content. These tests pin the parsing against
responses recorded from mcp-server-datahub v3.4.5.
"""
import json

import pytest

from datahub_rail.client import MCPClient

ORDERS = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
EVENTS = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)"
TX = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)"


class _Text:
    def __init__(self, text):
        self.text = text


class _Result:
    def __init__(self, payload):
        self.content = [_Text(json.dumps(payload))]
        self.is_error = False


class _FakeSession:
    """Records calls and replays recorded server payloads."""

    def __init__(self, payloads):
        self.payloads = payloads
        self.calls = []

    async def call_tool(self, name, arguments):
        self.calls.append((name, arguments))
        return _Result(self.payloads[name])


SEARCH_PAYLOAD = {
    "start": 0, "count": 10, "total": 2,
    "searchResults": [
        {"entity": {"urn": ORDERS, "properties": {"name": "orders_archive"}}},
        {"entity": {"urn": EVENTS, "properties": {"name": "events"}}},
    ],
}

ENTITIES_PAYLOAD = [{
    "urn": ORDERS,
    "name": "orders_archive",
    "platform": {"urn": "urn:li:dataPlatform:postgres", "name": "postgres"},
    "properties": {"name": "orders_archive", "description": ""},
    "ownership": {"owners": [{"owner": {"urn": "urn:li:corpuser:data-eng"}, "type": "DATAOWNER"}]},
    "schemaMetadata": {"fields": [{"fieldPath": "id", "nativeDataType": "bigint", "description": "Order ID"}]},
}]

FIELDS_PAYLOAD = {
    "urn": TX,
    "fields": [
        {"fieldPath": "amount", "nativeDataType": "int", "description": "Amount"},
        {"fieldPath": "id", "nativeDataType": "bigint", "description": "Transaction ID"},
    ],
    "totalFields": 2,
}

LINEAGE_EMPTY = {"upstreams": {"total": 0}}
LINEAGE_ONE = {
    "upstreams": {
        "total": 1,
        "searchResults": [
            {"entity": {"urn": TX, "name": "transactions",
                        "platform": {"name": "postgres"}}}
        ],
    }
}


def _client(payloads):
    c = MCPClient()
    c.session = _FakeSession(payloads)
    return c


@pytest.mark.asyncio
async def test_list_datasets_uses_search_tool():
    """Dataset discovery goes through the real `search` tool."""
    c = _client({"search": SEARCH_PAYLOAD})
    datasets = await c.list_datasets()

    assert c.session.calls[0][0] == "search"
    assert [d.name for d in datasets] == ["orders_archive", "events"]
    assert datasets[0].urn == ORDERS


@pytest.mark.asyncio
async def test_get_entity_extracts_owner_from_ownership_aspect():
    """Owner comes from the ownership aspect, not a fabricated field."""
    c = _client({"get_entities": ENTITIES_PAYLOAD})
    entity = await c.get_entity(ORDERS)

    assert c.session.calls[0][0] == "get_entities"
    assert entity["owner"] == "data-eng"
    assert entity["name"] == "orders_archive"
    assert entity["platform"] == "postgres"


@pytest.mark.asyncio
async def test_fetch_schema_uses_list_schema_fields_native_types():
    """Schema types come from nativeDataType so drift is comparable."""
    c = _client({"list_schema_fields": FIELDS_PAYLOAD})
    schema = await c.fetch_schema(TX)

    assert c.session.calls[0][0] == "list_schema_fields"
    amount = [f for f in schema.fields if f["field_path"] == "amount"][0]
    assert amount["type"] == "int"


@pytest.mark.asyncio
async def test_walk_upstream_parses_get_lineage_search_results():
    """Resolved upstreams are read out of get_lineage searchResults."""
    c = _client({"get_lineage": LINEAGE_ONE})
    result = await c.walk_upstream(EVENTS)

    name, args = c.session.calls[0]
    assert name == "get_lineage"
    assert args["upstream"] is True
    assert result.upstream[0]["urn"] == TX
    assert result.upstream[0]["name"] == "transactions"


@pytest.mark.asyncio
async def test_walk_upstream_handles_zero_upstreams():
    """A soft-deleted upstream resolves to nothing without raising."""
    c = _client({"get_lineage": LINEAGE_EMPTY})
    result = await c.walk_upstream(EVENTS)

    assert result.upstream == []


@pytest.mark.asyncio
async def test_call_tool_requires_connection():
    """Calling before connect() fails loudly rather than silently no-op."""
    c = MCPClient()
    with pytest.raises(RuntimeError):
        await c.list_datasets()
