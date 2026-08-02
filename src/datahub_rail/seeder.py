"""Demo dataset seeder for DataHub with planted faults.

Writes go through DataHub's OpenAPI v3 entity endpoint (the supported ingest
path for aspects). Every write is checked: a non-2xx status or an ``error``
key in the body raises :class:`SeedError`. Fail loud on outage — a seeder that
reports success while writing nothing is the exact failure mode this project
exists to catch.
"""
from typing import Optional
import aiohttp
from datetime import datetime, timezone

from .urns import platform_urn_from_dataset

_ACTOR = "urn:li:corpuser:datahub"

# DataHub schema field types are a union; map native SQL types onto the
# closest com.linkedin.schema type so the UI renders them correctly.
_TYPE_CLASSES = {
    "int": "NumberType",
    "bigint": "NumberType",
    "decimal": "NumberType",
    "double": "NumberType",
    "float": "NumberType",
    "varchar": "StringType",
    "string": "StringType",
    "text": "StringType",
    "boolean": "BooleanType",
    "timestamp": "TimeType",
    "date": "DateType",
}


class SeedError(RuntimeError):
    """Raised when a DataHub write fails. Never swallowed."""


def _type_class(native_type: str) -> str:
    """Map a native SQL type onto a DataHub schema type class."""
    base = native_type.split("(")[0].strip().lower()
    return _TYPE_CLASSES.get(base, "StringType")


class DatasetSeeder:
    """Seed DataHub with synthetic datasets and deliberately planted faults."""

    def __init__(self, gms_url: str = "http://localhost:8080", token: Optional[str] = None):
        self.gms_url = gms_url.rstrip("/")
        self.token = token
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
        description: str = "",
    ) -> dict:
        """Upsert a dataset with properties and ownership."""
        if last_modified is None:
            last_modified = int(datetime.now(timezone.utc).timestamp() * 1000)

        aspects = {
            "datasetProperties": {
                "value": {
                    "name": name,
                    "description": description,
                    "customProperties": {},
                    "lastModified": {"time": last_modified},
                }
            },
            "ownership": {
                "value": {
                    "owners": [
                        {"owner": f"urn:li:corpuser:{owner}", "type": "DATAOWNER"}
                    ],
                    "lastModified": {"time": 0, "actor": _ACTOR},
                }
            },
            "status": {"value": {"removed": False}},
        }
        return await self._post_aspects(urn, aspects)

    async def add_schema(
        self,
        dataset_urn: str,
        fields: list[dict],
        description: str = "",
    ) -> dict:
        """Attach schema metadata to a dataset."""
        schema_fields = [
            {
                "fieldPath": f["field_path"],
                "nativeDataType": f["type"],
                "description": f.get("description", ""),
                "type": {"type": {f"com.linkedin.schema.{_type_class(f['type'])}": {}}},
            }
            for f in fields
        ]
        aspects = {
            "schemaMetadata": {
                "value": {
                    "schemaName": description or dataset_urn,
                    "platform": platform_urn_from_dataset(dataset_urn),
                    "version": 0,
                    "hash": "",
                    "platformSchema": {
                        "com.linkedin.schema.OtherSchema": {"rawSchema": ""}
                    },
                    "fields": schema_fields,
                }
            }
        }
        return await self._post_aspects(dataset_urn, aspects)

    async def create_lineage(
        self,
        upstream_urn: str,
        downstream_urn: str,
    ) -> dict:
        """Create a lineage edge (upstreamLineage aspect on the downstream)."""
        aspects = {
            "upstreamLineage": {
                "value": {
                    "upstreams": [
                        {
                            "auditStamp": {"time": 0, "actor": _ACTOR},
                            "dataset": upstream_urn,
                            "type": "TRANSFORMED",
                        }
                    ]
                }
            }
        }
        return await self._post_aspects(downstream_urn, aspects)

    async def delete_dataset(self, urn: str) -> dict:
        """Soft-delete a dataset, leaving downstream lineage edges dangling."""
        return await self._post_aspects(urn, {"status": {"value": {"removed": True}}})

    async def _post_aspects(self, urn: str, aspects: dict) -> dict:
        """POST aspects to the OpenAPI v3 entity endpoint. Raises on failure."""
        if not self.session:
            await self.connect()

        url = f"{self.gms_url}/openapi/v3/entity/dataset?async=false"
        payload = [{"urn": urn, **aspects}]
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        async with self.session.post(url, json=payload, headers=headers) as resp:
            status = resp.status
            try:
                body = await resp.json()
            except Exception as exc:  # non-JSON body on failure
                raise SeedError(f"Write failed for {urn}: HTTP {status} (unparseable body)") from exc

            if status >= 400:
                raise SeedError(f"Write failed for {urn}: HTTP {status} — {body}")
            if isinstance(body, dict) and body.get("error"):
                raise SeedError(f"Write failed for {urn}: {body.get('error')} — {body.get('message', '')}")
            return body

