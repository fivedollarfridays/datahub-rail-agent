"""MCP client wrapper for DataHub context graph reads.

Adapts the tool surface actually exposed by mcp-server-datahub (v3.4.5):
``search``, ``get_entities``, ``get_lineage``, ``list_schema_fields``.
Tool results arrive as JSON in text content blocks.
"""
import json
import os
from contextlib import AsyncExitStack
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .types import Dataset, LineageResult, SchemaMetadata
from .urns import name_from_urn, platform_from_urn

#: `search` spans every entity type, so an estate token that fuzzy-matches a
#: tag or glossary term would be probed as a dataset. Notably the agent's own
#: write-back tags (`urn:li:tag:rail.status.*`) match a `rail`-shaped estate
#: token and rank above real datasets.
_DATASET_ENTITY_FILTER = "entity_type = dataset"

_DATASET_URN_PREFIX = "urn:li:dataset:"


class MCPClient:
    """Typed MCP client for DataHub context graph operations."""

    def __init__(
        self,
        command: str = "uvx",
        args: Optional[list[str]] = None,
        gms_url: str = "http://localhost:8080",
        token: str = "",
    ):
        self.command = command
        self.args = args or ["mcp-server-datahub@latest"]
        self.gms_url = gms_url
        self.token = token
        self.session: Optional[ClientSession] = None
        self._stack: Optional[AsyncExitStack] = None

    async def connect(self) -> None:
        """Establish MCP session to the DataHub server over stdio."""
        if self.session is not None:
            return

        params = StdioServerParameters(
            command=self.command,
            args=self.args,
            env={
                **os.environ,
                "DATAHUB_GMS_URL": self.gms_url,
                "DATAHUB_GMS_TOKEN": self.token,
            },
        )
        self._stack = AsyncExitStack()
        read, write = await self._stack.enter_async_context(stdio_client(params))
        self.session = await self._stack.enter_async_context(ClientSession(read, write))
        await self.session.initialize()

    async def disconnect(self) -> None:
        """Close MCP session and the underlying transport."""
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
        self.session = None

    async def __aenter__(self):
        """Async context manager entry: connects the session."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit: closes the session."""
        await self.disconnect()

    def __enter__(self):
        """Sync context manager entry (no session established)."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Sync context manager exit."""
        return None

    async def _call(self, tool: str, arguments: dict) -> Any:
        """Call an MCP tool and parse its JSON text payload."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        result = await self.session.call_tool(tool, arguments)
        for block in getattr(result, "content", []):
            text = getattr(block, "text", None)
            if not text:
                continue
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                continue
        return {}

    async def list_datasets(self, query: str = "*", num_results: int = 50) -> list[Dataset]:
        """List datasets via the `search` tool, constrained to dataset entities.

        The entity-type filter is applied server-side; the URN check is a
        second line of defence so a filter regression cannot silently feed
        tags or glossary terms into the probe loop.
        """
        payload = await self._call(
            "search",
            {
                "query": query,
                "filter": _DATASET_ENTITY_FILTER,
                "num_results": num_results,
            },
        )
        datasets = []
        for hit in payload.get("searchResults", []):
            entity = hit.get("entity", {})
            urn = entity.get("urn", "")
            if not urn.startswith(_DATASET_URN_PREFIX):
                continue
            props = entity.get("properties") or {}
            datasets.append(
                Dataset(
                    urn=urn,
                    name=props.get("name") or name_from_urn(urn),
                    platform=platform_from_urn(urn),
                    owner="",
                    last_modified=0,
                )
            )
        return datasets

    async def get_entity(self, dataset_urn: str) -> dict:
        """Fetch entity detail (name, platform, owner) via `get_entities`."""
        payload = await self._call("get_entities", {"urns": [dataset_urn]})
        records = payload if isinstance(payload, list) else payload.get("entities", [])
        if not records:
            return {"urn": dataset_urn, "name": name_from_urn(dataset_urn),
                    "platform": platform_from_urn(dataset_urn), "owner": ""}

        record = records[0]
        platform = (record.get("platform") or {}).get("name") or platform_from_urn(dataset_urn)
        owners = ((record.get("ownership") or {}).get("owners")) or []
        owner_names = [
            (o.get("owner") or {}).get("urn", "").split(":")[-1] for o in owners
        ]
        return {
            "urn": record.get("urn", dataset_urn),
            "name": record.get("name") or name_from_urn(dataset_urn),
            "platform": platform,
            "owner": ", ".join(n for n in owner_names if n),
            "description": (record.get("properties") or {}).get("description", ""),
        }

    async def fetch_schema(self, dataset_urn: str) -> SchemaMetadata:
        """Fetch schema fields via `list_schema_fields`."""
        payload = await self._call("list_schema_fields", {"urn": dataset_urn})
        fields = [
            {
                "field_path": f.get("fieldPath", ""),
                "type": f.get("nativeDataType", ""),
                "description": f.get("description", "") or "",
            }
            for f in payload.get("fields", [])
        ]
        return SchemaMetadata(
            urn=payload.get("urn", dataset_urn),
            fields=fields,
            description="",
        )

    async def walk_upstream(self, dataset_urn: str, hops: int = 1) -> LineageResult:
        """Walk upstream lineage via `get_lineage`."""
        return await self._lineage(dataset_urn, hops, upstream=True)

    async def walk_downstream(self, dataset_urn: str, hops: int = 1) -> LineageResult:
        """Walk downstream lineage via `get_lineage`."""
        return await self._lineage(dataset_urn, hops, upstream=False)

    async def _lineage(self, dataset_urn: str, hops: int, upstream: bool) -> LineageResult:
        """Shared lineage reader for both directions."""
        payload = await self._call(
            "get_lineage",
            {"urn": dataset_urn, "upstream": upstream, "max_hops": hops},
        )
        key = "upstreams" if upstream else "downstreams"
        block = payload.get(key) or {}
        nodes = []
        for hit in block.get("searchResults", []):
            entity = hit.get("entity", {})
            urn = entity.get("urn", "")
            nodes.append(
                {
                    "urn": urn,
                    "name": entity.get("name") or name_from_urn(urn),
                    "platform": (entity.get("platform") or {}).get("name")
                    or platform_from_urn(urn),
                }
            )
        return LineageResult(
            urn=dataset_urn,
            upstream=nodes if upstream else [],
            downstream=[] if upstream else nodes,
        )

