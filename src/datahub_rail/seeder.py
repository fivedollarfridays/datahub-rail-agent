"""Demo dataset seeder for DataHub with planted faults."""
from typing import Optional
import aiohttp
from datetime import datetime, timezone


class DatasetSeeder:
    """Seed DataHub with synthetic datasets and deliberately planted faults."""

    def __init__(self, gms_url: str = "http://localhost:8080"):
        self.gms_url = gms_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> None:
        """Initialize HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def disconnect(self) -> None:
        """Close HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def ingest_dataset(
        self,
        urn: str,
        name: str,
        platform: str,
        owner: str,
        last_modified: Optional[int] = None,
    ) -> dict:
        """Ingest a dataset via GraphQL mutation."""
        if not self.session:
            await self.connect()

        if last_modified is None:
            last_modified = int(datetime.now(timezone.utc).timestamp() * 1000)

        mutation = """
        mutation UpsertDataset($input: DatasetInput!) {
            upsertDataset(input: $input) {
                urn
            }
        }
        """

        variables = {
            "input": {
                "urn": urn,
                "name": name,
                "platform": platform,
                "owner": owner,
                "lastModified": last_modified,
            }
        }

        return await self._call_graphql(mutation, variables)

    async def add_schema(
        self,
        dataset_urn: str,
        fields: list[dict],
        description: str = "",
    ) -> dict:
        """Add schema metadata to a dataset."""
        if not self.session:
            await self.connect()

        mutation = """
        mutation AddSchema($input: SchemaInput!) {
            addSchema(input: $input) {
                urn
            }
        }
        """

        variables = {
            "input": {
                "datasetUrn": dataset_urn,
                "fields": fields,
                "description": description,
            }
        }

        return await self._call_graphql(mutation, variables)

    async def create_lineage(
        self,
        upstream_urn: str,
        downstream_urn: str,
    ) -> dict:
        """Create a lineage edge between two datasets."""
        if not self.session:
            await self.connect()

        mutation = """
        mutation CreateLineage($input: LineageInput!) {
            createLineage(input: $input) {
                upstreamUrn
                downstreamUrn
            }
        }
        """

        variables = {
            "input": {
                "upstreamUrn": upstream_urn,
                "downstreamUrn": downstream_urn,
            }
        }

        return await self._call_graphql(mutation, variables)

    async def delete_dataset(self, urn: str) -> dict:
        """Delete a dataset (for creating broken lineage faults)."""
        if not self.session:
            await self.connect()

        mutation = """
        mutation DeleteDataset($urn: String!) {
            deleteDataset(urn: $urn)
        }
        """

        variables = {"urn": urn}

        return await self._call_graphql(mutation, variables)

    async def _call_graphql(self, query: str, variables: dict) -> dict:
        """Call DataHub GraphQL API."""
        if not self.session:
            raise RuntimeError("Not connected. Call connect() first.")

        payload = {
            "query": query,
            "variables": variables,
        }

        async with self.session.post(
            f"{self.gms_url}/api/graphql",
            json=payload,
            headers={"Content-Type": "application/json"},
        ) as resp:
            return await resp.json()
