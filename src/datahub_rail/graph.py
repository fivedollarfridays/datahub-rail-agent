"""Probe-facing graph facade: MCP tools plus the GMS aspects MCP omits.

Every read is journalled as a :class:`Provenance` entry so an incident report
can show that each claim came from a specific graph read rather than an LLM.
"""
from datetime import datetime, timezone
from typing import Optional

from .client import MCPClient
from .gms import GMSReader
from .triage import Provenance
from .types import Dataset, Freshness, LineageResult, SchemaMetadata


class GraphClient:
    """Single read interface the probes and triage engine talk to."""

    def __init__(self, mcp, gms):
        self.mcp = mcp
        self.gms = gms
        self.provenance: list[Provenance] = []

    @classmethod
    def create(
        cls,
        gms_url: str = "http://localhost:8080",
        token: str = "",
        mcp_command: str = "uvx",
        mcp_args: Optional[list[str]] = None,
    ) -> "GraphClient":
        """Build a facade over a real MCP server and GMS endpoint."""
        return cls(
            mcp=MCPClient(command=mcp_command, args=mcp_args, gms_url=gms_url, token=token),
            gms=GMSReader(gms_url=gms_url, token=token or None),
        )

    async def connect(self) -> None:
        """Connect both underlying readers."""
        await self.mcp.connect()
        await self.gms.connect()

    async def disconnect(self) -> None:
        """Disconnect both underlying readers."""
        await self.gms.disconnect()
        await self.mcp.disconnect()

    def _record(self, tool: str, dataset_urn: str) -> None:
        """Journal a graph read."""
        self.provenance.append(
            Provenance(
                tool=tool,
                dataset_urn=dataset_urn,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )

    def provenance_for(self, dataset_urn: str) -> list[Provenance]:
        """Provenance entries recorded for one dataset."""
        return [p for p in self.provenance if p.dataset_urn == dataset_urn]

    async def list_datasets(self, query: str = "*", num_results: int = 50) -> list[Dataset]:
        """List datasets (MCP `search`)."""
        datasets = await self.mcp.list_datasets(query=query, num_results=num_results)
        self._record("mcp:search", query)
        return datasets

    async def get_entity(self, dataset_urn: str) -> dict:
        """Entity detail incl. owner (MCP `get_entities`)."""
        entity = await self.mcp.get_entity(dataset_urn)
        self._record("mcp:get_entities", dataset_urn)
        return entity

    async def fetch_schema(self, dataset_urn: str) -> SchemaMetadata:
        """Schema fields (MCP `list_schema_fields`)."""
        schema = await self.mcp.fetch_schema(dataset_urn)
        self._record("mcp:list_schema_fields", dataset_urn)
        return schema

    async def walk_upstream(self, dataset_urn: str, hops: int = 1) -> LineageResult:
        """Resolved upstream lineage (MCP `get_lineage`)."""
        lineage = await self.mcp.walk_upstream(dataset_urn, hops=hops)
        self._record("mcp:get_lineage", dataset_urn)
        return lineage

    async def get_freshness(self, dataset_urn: str) -> Freshness:
        """Capture-based freshness (GMS `datasetProperties.lastModified`)."""
        freshness = await self.gms.get_freshness(dataset_urn)
        self._record("gms:datasetProperties.lastModified", dataset_urn)
        return freshness

    async def get_declared_upstreams(self, dataset_urn: str) -> list[str]:
        """Declared lineage edges (GMS `upstreamLineage`)."""
        upstreams = await self.gms.get_declared_upstreams(dataset_urn)
        self._record("gms:upstreamLineage", dataset_urn)
        return upstreams
