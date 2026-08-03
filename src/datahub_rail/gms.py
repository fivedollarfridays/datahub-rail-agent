"""Direct GMS aspect reads for facts the MCP tool surface does not expose.

mcp-server-datahub v3.4.5 returns entity properties without ``lastModified``,
and ``get_lineage`` only returns upstreams that still resolve — a soft-deleted
upstream simply vanishes. Capture-based freshness and dangling-edge detection
therefore read the ``datasetProperties`` and ``upstreamLineage`` aspects from
the same DataHub instance over its OpenAPI v3 read endpoint.
"""
from typing import Optional
from urllib.parse import quote

import aiohttp

from .types import Freshness


class GMSReader:
    """Read dataset aspects straight from the DataHub metadata service."""

    def __init__(self, gms_url: str = "http://localhost:8080", token: Optional[str] = None):
        self.gms_url = gms_url.rstrip("/")
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> None:
        """Initialize the HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def disconnect(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    async def _get_entity(self, dataset_urn: str) -> dict:
        """Fetch the raw aspect envelope for a dataset, or {} if absent."""
        if not self.session:
            await self.connect()

        encoded = quote(dataset_urn, safe="")
        url = f"{self.gms_url}/openapi/v3/entity/dataset/{encoded}"
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with self.session.get(url, headers=headers) as resp:
            if resp.status >= 400:
                return {}
            try:
                return await resp.json()
            except Exception:
                return {}

    async def get_freshness(self, dataset_urn: str) -> Freshness:
        """Read capture-based freshness from datasetProperties.lastModified."""
        entity = await self._get_entity(dataset_urn)
        props = (entity.get("datasetProperties") or {}).get("value") or {}
        last_modified = (props.get("lastModified") or {}).get("time")

        if last_modified is None:
            raise RuntimeError(
                f"No lastModified timestamp on {dataset_urn}: freshness is unverifiable"
            )

        return Freshness(
            urn=dataset_urn,
            last_modified=last_modified,
            is_stale=False,
            expected_frequency=0,
        )

    async def scroll_datasets(
        self,
        aspects: list[str],
        count: int = 100,
        max_pages: int = 50,
    ) -> list[dict]:
        """Page through every dataset entity, returning the requested aspects.

        ``datasetKey`` is always requested: on DataHub 1.5 a scroll asking
        only for a sparse aspect returns an empty ``entities`` list despite a
        non-zero ``totalCount``. A page that comes back empty ends the walk,
        so an error response cannot spin.
        """
        if not self.session:
            await self.connect()

        wanted = ["datasetKey"] + [a for a in aspects if a != "datasetKey"]
        query = "&".join(f"aspects={a}" for a in wanted)
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        entities: list[dict] = []
        scroll_id: Optional[str] = None
        for _ in range(max_pages):
            url = f"{self.gms_url}/openapi/v3/entity/dataset?count={count}&{query}"
            if scroll_id:
                url = f"{url}&scrollId={quote(scroll_id, safe='')}"
            async with self.session.get(url, headers=headers) as resp:
                if resp.status >= 400:
                    return entities
                try:
                    page = await resp.json()
                except Exception:
                    return entities

            batch = page.get("entities") or []
            entities.extend(batch)
            scroll_id = page.get("scrollId")
            if not batch or not scroll_id:
                return entities

        return entities

    async def get_declared_upstreams(self, dataset_urn: str) -> list[str]:
        """Read declared upstream edge targets from the upstreamLineage aspect."""
        entity = await self._get_entity(dataset_urn)
        lineage = (entity.get("upstreamLineage") or {}).get("value") or {}
        return [u["dataset"] for u in lineage.get("upstreams", []) if u.get("dataset")]
