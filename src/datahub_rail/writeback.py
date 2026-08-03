"""Publish probe verdicts back into DataHub, onto the datasets themselves.

Opt-in (``--writeback``). Two surfaces, both confirmed to persist and render
in the DataHub 1.5 UI:

* ``globalTags`` — a bounded ``rail.status.*`` tag (PASS / NEW-FAIL /
  CHRONIC / RECOVERED). Renders as a chip on the dataset page and is
  searchable, so "which assets are chronically failing" becomes a facet query.
* ``structuredProperties`` — the detail another agent wants to read: the full
  delta-aware verdict (``CHRONIC-day-3``), the probe that judged it, the run
  timestamp, and the incident-report filename when one exists.

Both aspects are replace-on-write, so every payload is read-merged: rail's own
markers are replaced (never stacked), foreign tags and properties survive.
Write-back is fail-soft — a fault here is logged loudly and the probe run
still completes, because the probe run is the product.
"""
import logging
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import aiohttp

from .rail_markers import (
    PROPERTY_KEYS,
    RAIL_PROPERTY_PREFIX,
    RAIL_TAG_PREFIX,
    STATUS_CLASSES,
    merge_properties,
    merge_tags,
    property_definition,
    property_values,
    tag_entity,
    tag_urn,
)
from .state_history import StateHistory
from .verdicts import verdict_for_dataset

logger = logging.getLogger(__name__)

__all__ = [
    "DataHubWriteBack",
    "WriteBackError",
    "PROPERTY_KEYS",
    "RAIL_PROPERTY_PREFIX",
    "RAIL_TAG_PREFIX",
    "STATUS_CLASSES",
    "find_incident_report",
    "merge_properties",
    "merge_tags",
    "property_values",
    "publish_run",
    "tag_urn",
]


class WriteBackError(RuntimeError):
    """A write-back call failed. Caught at the run boundary, never propagated."""


class DataHubWriteBack:
    """Writes rail verdicts onto DataHub dataset entities via OpenAPI v3."""

    def __init__(self, gms_url: str = "http://localhost:8080", token: Optional[str] = None):
        """Configure the target GMS. No connection is opened until used."""
        self.gms_url = gms_url.rstrip("/")
        self.token = token
        self.session: Optional[aiohttp.ClientSession] = None

    async def connect(self) -> None:
        """Open the HTTP session."""
        if self.session is None:
            self.session = aiohttp.ClientSession()

    async def disconnect(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None

    @property
    def _headers(self) -> dict:
        """Auth and content headers; the local quickstart needs no token."""
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _post(self, entity: str, payload: list[dict]) -> dict:
        """POST entity aspects. Raises WriteBackError on non-2xx or an error body."""
        if not self.session:
            await self.connect()

        url = f"{self.gms_url}/openapi/v3/entity/{entity}?async=false"
        async with self.session.post(url, json=payload, headers=self._headers) as resp:
            status = resp.status
            try:
                body = await resp.json()
            except Exception as exc:
                raise WriteBackError(f"{entity} write failed: HTTP {status}") from exc
            if status >= 400:
                raise WriteBackError(f"{entity} write failed: HTTP {status} — {body}")
            if isinstance(body, dict) and body.get("error"):
                raise WriteBackError(f"{entity} write failed: {body['error']}")
            return body

    async def _read_aspect(self, urn: str, aspect: str) -> dict:
        """Read one aspect. A missing aspect is not an error — returns {}."""
        if not self.session:
            await self.connect()

        url = f"{self.gms_url}/openapi/v3/entity/dataset/{quote(urn, safe='')}/{aspect}"
        async with self.session.get(url, headers=self._headers) as resp:
            if resp.status != 200:
                return {}
            try:
                return (await resp.json()).get("value") or {}
            except Exception:
                return {}

    async def ensure_schema(self) -> None:
        """Create the tag entities and structured-property definitions rail writes."""
        await self._post("tag", [tag_entity(status) for status in STATUS_CLASSES])
        await self._post(
            "structuredProperty", [property_definition(key) for key in PROPERTY_KEYS]
        )

    async def apply(
        self,
        dataset_urn: str,
        verdict,
        run_timestamp: str,
        incident_file: Optional[str] = None,
    ) -> dict:
        """Read-merge-write this dataset's rail tag and properties."""
        existing_tags = (await self._read_aspect(dataset_urn, "globalTags")).get("tags") or []
        existing_props = (
            await self._read_aspect(dataset_urn, "structuredProperties")
        ).get("properties") or []

        values = property_values(verdict, run_timestamp, incident_file)
        payload = {
            "urn": dataset_urn,
            "globalTags": {"value": {"tags": merge_tags(existing_tags, verdict.status_class)}},
            "structuredProperties": {
                "value": {"properties": merge_properties(existing_props, values)}
            },
        }
        await self._post("dataset", [payload])
        return payload


def find_incident_report(outbox: Path | str, dataset_name: str) -> Optional[str]:
    """Newest incident report filename for a dataset, or None if it has none."""
    outbox = Path(outbox)
    if not outbox.is_dir():
        return None
    reports = sorted(outbox.glob(f"incident_{dataset_name}_*.md"))
    return reports[-1].name if reports else None


async def publish_run(
    report: dict,
    *,
    history_path: Path | str,
    outbox: Path | str,
    writer: "DataHubWriteBack",
    run_timestamp: str,
) -> dict:
    """Publish every probed dataset's verdict back into DataHub. Never raises."""
    entries = StateHistory(history_path).load()
    counts = {"written": 0, "failed": 0, "skipped": 0}

    for dataset in report.get("datasets", []):
        verdict = verdict_for_dataset(entries, dataset["urn"])
        if verdict is None:
            counts["skipped"] += 1
            continue
        incident = find_incident_report(outbox, dataset.get("name", ""))
        try:
            await writer.apply(dataset["urn"], verdict, run_timestamp, incident)
            counts["written"] += 1
        except Exception as exc:
            counts["failed"] += 1
            logger.error(
                "WRITE-BACK FAILED for %s: %s — probe results are unaffected",
                dataset["urn"],
                exc,
            )

    return counts
