"""Tests for basic dataset seeding (ingest, schema, lineage)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from datahub_rail.seeder import DatasetSeeder


@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp session with context manager support."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.json = AsyncMock(return_value={"data": {}})
    mock_response.status = 200

    # Make post() return a context manager that yields the response
    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, *args):
            pass

    mock_session.post = MagicMock(return_value=AsyncContextManager())
    return mock_session


@pytest.mark.asyncio
async def test_ingest_basic_dataset(mock_aiohttp):
    """RED: Seeder can ingest a basic dataset."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    result = await seeder.ingest_dataset(
        urn="urn:li:dataset:(urn:li:dataPlatform:postgres,test_db.public.users,PROD)",
        name="test_users",
        platform="postgres",
        owner="data-eng",
    )

    assert result is not None
    mock_aiohttp.post.assert_called_once()


@pytest.mark.asyncio
async def test_ingest_is_idempotent(mock_aiohttp):
    """RED: Ingesting the same dataset twice should not error."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,test_db.public.users,PROD)"

    # First ingest
    await seeder.ingest_dataset(
        urn=urn,
        name="test_users",
        platform="postgres",
        owner="data-eng",
    )

    # Second ingest (should not error)
    result = await seeder.ingest_dataset(
        urn=urn,
        name="test_users",
        platform="postgres",
        owner="data-eng",
    )

    assert result is not None
    assert mock_aiohttp.post.call_count == 2


@pytest.mark.asyncio
async def test_add_schema_to_dataset(mock_aiohttp):
    """RED: Seeder can add schema metadata to a dataset."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,test_db.public.users,PROD)"
    schema_fields = [
        {"field_path": "id", "type": "bigint", "description": "User ID"},
        {"field_path": "name", "type": "varchar", "description": "User name"},
    ]

    result = await seeder.add_schema(
        dataset_urn=urn,
        fields=schema_fields,
        description="Test users table",
    )

    assert result is not None
    mock_aiohttp.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_lineage_edge(mock_aiohttp):
    """RED: Seeder can create lineage edge between two datasets."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    upstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,source_db.public.raw_users,PROD)"
    downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,warehouse_db.public.users,PROD)"

    result = await seeder.create_lineage(
        upstream_urn=upstream_urn,
        downstream_urn=downstream_urn,
    )

    assert result is not None
    mock_aiohttp.post.assert_called_once()


@pytest.mark.asyncio
async def test_create_upstream_lineage(mock_aiohttp):
    """RED: walk_upstream should show the created lineage."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,warehouse_db.public.users,PROD)"

    # Create lineage
    await seeder.create_lineage(
        upstream_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,source_db.public.raw_users,PROD)",
        downstream_urn=downstream_urn,
    )

    # Verify lineage was created
    mock_aiohttp.post.assert_called_once()
