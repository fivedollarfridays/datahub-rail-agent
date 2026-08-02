"""Transport-level seeder tests: real DataHub OpenAPI v3 writes, fail-loud on errors."""
import pytest
from unittest.mock import MagicMock

from datahub_rail.seeder import DatasetSeeder, SeedError


class _FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload if payload is not None else [{"urn": "x"}]

    async def json(self):
        return self._payload

    async def text(self):
        return str(self._payload)


class _FakePost:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return False


def _session_returning(response):
    session = MagicMock()
    session.post = MagicMock(return_value=_FakePost(response))
    return session


URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)"


@pytest.mark.asyncio
async def test_ingest_posts_to_openapi_v3_entity_endpoint():
    """Writes must target the OpenAPI v3 dataset endpoint, not a GraphQL mutation."""
    session = _session_returning(_FakeResponse())
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session

    await seeder.ingest_dataset(urn=URN, name="users", platform="postgres", owner="data-eng")

    url = session.post.call_args[0][0]
    assert url == "http://localhost:8080/openapi/v3/entity/dataset?async=false"


@pytest.mark.asyncio
async def test_ingest_sends_dataset_properties_and_ownership_aspects():
    """The payload must carry real DataHub aspects keyed by URN."""
    session = _session_returning(_FakeResponse())
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session

    await seeder.ingest_dataset(
        urn=URN, name="users", platform="postgres", owner="data-eng", last_modified=1700000000000
    )

    body = session.post.call_args[1]["json"]
    assert isinstance(body, list) and body[0]["urn"] == URN
    assert body[0]["datasetProperties"]["value"]["name"] == "users"
    assert body[0]["datasetProperties"]["value"]["lastModified"]["time"] == 1700000000000
    owners = body[0]["ownership"]["value"]["owners"]
    assert owners[0]["owner"] == "urn:li:corpuser:data-eng"


@pytest.mark.asyncio
async def test_ingest_raises_on_http_error_status():
    """Fail loud: an HTTP error must raise, never return a fake success."""
    session = _session_returning(_FakeResponse(status=400, payload={"error": "Validation Error"}))
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session

    with pytest.raises(SeedError) as exc:
        await seeder.ingest_dataset(urn=URN, name="users", platform="postgres", owner="data-eng")

    assert "400" in str(exc.value)


@pytest.mark.asyncio
async def test_ingest_raises_when_body_carries_error_key():
    """Fail loud: a 200 with an error body must still raise."""
    session = _session_returning(_FakeResponse(status=200, payload={"error": "Unknown aspect"}))
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session

    with pytest.raises(SeedError):
        await seeder.ingest_dataset(urn=URN, name="users", platform="postgres", owner="data-eng")


@pytest.mark.asyncio
async def test_create_lineage_writes_upstream_lineage_on_downstream():
    """Lineage edges are an upstreamLineage aspect on the downstream entity."""
    session = _session_returning(_FakeResponse())
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session
    up = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.raw_events_old,PROD)"
    down = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)"

    await seeder.create_lineage(upstream_urn=up, downstream_urn=down)

    body = session.post.call_args[1]["json"]
    assert body[0]["urn"] == down
    assert body[0]["upstreamLineage"]["value"]["upstreams"][0]["dataset"] == up


@pytest.mark.asyncio
async def test_add_schema_sends_native_data_types():
    """Schema fields must carry nativeDataType so type drift is detectable."""
    session = _session_returning(_FakeResponse())
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session

    await seeder.add_schema(
        dataset_urn=URN,
        fields=[{"field_path": "amount", "type": "decimal(12,2)", "description": "amt"}],
        description="tbl",
    )

    fields = session.post.call_args[1]["json"][0]["schemaMetadata"]["value"]["fields"]
    assert fields[0]["fieldPath"] == "amount"
    assert fields[0]["nativeDataType"] == "decimal(12,2)"


@pytest.mark.asyncio
async def test_delete_dataset_soft_deletes_via_status_aspect():
    """Deleting sets the status aspect removed=true (creates the dangling upstream)."""
    session = _session_returning(_FakeResponse())
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = session

    await seeder.delete_dataset(urn=URN)

    body = session.post.call_args[1]["json"]
    assert body[0]["status"]["value"]["removed"] is True
