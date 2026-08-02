"""MCP client wrapper for DataHub context graph reads."""
from typing import Optional

from mcp import ClientSession, StdioServerParameters, stdio_client

from .types import Dataset, Freshness, LineageResult, SchemaMetadata


class MCPClient:
    """Typed MCP client for DataHub context graph operations."""

    def __init__(
        self,
        command: str = "uvx",
        args: Optional[list[str]] = None,
    ):
        self.command = command
        self.args = args or ["mcp-server-datahub@latest"]
        self.session: Optional[ClientSession] = None

    async def connect(self) -> None:
        """Establish MCP session to DataHub server."""
        if self.session is not None:
            return

        params = StdioServerParameters(
            command=self.command,
            args=self.args,
        )
        transport, self.session = await stdio_client(params)

    async def disconnect(self) -> None:
        """Close MCP session."""
        if self.session:
            await self.session.close()
            self.session = None

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

    async def list_datasets(self) -> list[Dataset]:
        """List all datasets in DataHub with platform and owner."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        result = await self.session.call_tool("list_datasets", {})
        return [
            Dataset(
                urn=d["urn"],
                name=d["name"],
                platform=d["platform"],
                owner=d["owner"],
                last_modified=d["lastModified"],
            )
            for d in result.get("datasets", [])
        ]

    async def get_freshness(self, dataset_urn: str) -> Freshness:
        """Get freshness metadata for a dataset."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        result = await self.session.call_tool(
            "get_freshness", {"dataset_urn": dataset_urn}
        )
        return Freshness(
            urn=result["urn"],
            last_modified=result["lastModified"],
            is_stale=result["isStale"],
            expected_frequency=result["expectedFrequency"],
        )

    async def fetch_schema(self, dataset_urn: str) -> SchemaMetadata:
        """Fetch schema and description for a dataset."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        result = await self.session.call_tool(
            "fetch_schema", {"dataset_urn": dataset_urn}
        )
        fields = [
            {
                "field_path": f["fieldPath"],
                "type": f["type"],
                "description": f["description"],
            }
            for f in result["schemaMetadata"]["fields"]
        ]
        return SchemaMetadata(
            urn=result["urn"],
            fields=fields,
            description=result["description"],
        )

    async def walk_upstream(self, dataset_urn: str, hops: int = 1) -> LineageResult:
        """Walk upstream lineage N hops."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        result = await self.session.call_tool(
            "walk_upstream", {"dataset_urn": dataset_urn, "hops": hops}
        )
        upstream = [
            {"urn": n["urn"], "name": n["name"], "platform": n["platform"]}
            for n in result.get("upstream", [])
        ]
        return LineageResult(
            urn=result["urn"],
            upstream=upstream,
            downstream=[],
        )

    async def walk_downstream(self, dataset_urn: str, hops: int = 1) -> LineageResult:
        """Walk downstream lineage N hops."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")
        result = await self.session.call_tool(
            "walk_downstream", {"dataset_urn": dataset_urn, "hops": hops}
        )
        downstream = [
            {"urn": n["urn"], "name": n["name"], "platform": n["platform"]}
            for n in result.get("downstream", [])
        ]
        return LineageResult(
            urn=result["urn"],
            upstream=[],
            downstream=downstream,
        )
