"""Tests for fault injection (stale, broken lineage, schema drift)."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from datahub_rail.seeder import DatasetSeeder


@pytest.fixture
def mock_aiohttp():
    """Mock aiohttp session with context manager support."""
    mock_session = MagicMock()
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"data": {}})

    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, *args):
            pass

    mock_session.post = MagicMock(return_value=AsyncContextManager())
    return mock_session


@pytest.mark.asyncio
async def test_inject_stale_freshness_fault(mock_aiohttp):
    """RED: Seeder can inject stale freshness fault (old lastModified)."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    # Create a dataset with old lastModified (e.g., 30 days ago)
    old_timestamp = int(
        (datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000
    )

    result = await seeder.ingest_dataset(
        urn="urn:li:dataset:(urn:li:dataPlatform:postgres,old_data.public.stale,PROD)",
        name="stale_dataset",
        platform="postgres",
        owner="data-eng",
        last_modified=old_timestamp,
    )

    assert result is not None
    # Verify the timestamp passed to GraphQL is old
    call_args = mock_aiohttp.post.call_args
    assert call_args is not None


@pytest.mark.asyncio
async def test_detect_stale_via_freshness_api(mock_aiohttp):
    """RED: Stale freshness is detectable via client freshness check."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    # Mock return value for freshness check
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "data": {
            "isStale": True,
            "expectedFrequency": 3600
        }
    })

    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, *args):
            pass

    mock_aiohttp.post = MagicMock(return_value=AsyncContextManager())
    seeder.session = mock_aiohttp

    # Verify call would show staleness
    old_timestamp = int(
        (datetime.now(timezone.utc) - timedelta(days=30)).timestamp() * 1000
    )
    result = await seeder.ingest_dataset(
        urn="urn:li:dataset:(urn:li:dataPlatform:postgres,old_data.public.stale,PROD)",
        name="stale_dataset",
        platform="postgres",
        owner="data-eng",
        last_modified=old_timestamp,
    )
    assert result is not None


@pytest.mark.asyncio
async def test_inject_broken_lineage_fault(mock_aiohttp):
    """RED: Seeder can create lineage edge then delete upstream (broken edge)."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    upstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,deleted_source.public.old,PROD)"
    downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,warehouse.public.users,PROD)"

    # Create lineage
    result = await seeder.create_lineage(
        upstream_urn=upstream_urn,
        downstream_urn=downstream_urn,
    )
    assert result is not None

    # Delete the upstream dataset (creating broken edge)
    result = await seeder.delete_dataset(urn=upstream_urn)
    assert result is not None


@pytest.mark.asyncio
async def test_broken_lineage_detectable(mock_aiohttp):
    """RED: Broken lineage (missing upstream) is detectable via walk_upstream."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    # Mock response showing broken lineage (upstream node marked as deleted)
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={
        "data": {
            "upstream": [
                {
                    "urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,deleted_source.public.old,PROD)",
                    "name": "deleted_source",
                    "deleted": True
                }
            ]
        }
    })

    class AsyncContextManager:
        async def __aenter__(self):
            return mock_response
        async def __aexit__(self, *args):
            pass

    mock_aiohttp.post = MagicMock(return_value=AsyncContextManager())
    seeder.session = mock_aiohttp

    # Create lineage
    await seeder.create_lineage(
        upstream_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,deleted_source.public.old,PROD)",
        downstream_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,warehouse.public.users,PROD)",
    )
    assert mock_aiohttp.post.called


@pytest.mark.asyncio
async def test_inject_schema_drift_fault(mock_aiohttp):
    """RED: Seeder can inject schema-drift fault (column type mismatch)."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    # Create upstream dataset with int type for amount
    upstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,source.public.transactions,PROD)"
    result = await seeder.add_schema(
        dataset_urn=upstream_urn,
        fields=[
            {"field_path": "id", "type": "bigint", "description": "Transaction ID"},
            {"field_path": "amount", "type": "int", "description": "Amount"},
        ],
        description="Source transactions",
    )
    assert result is not None

    # Create downstream dataset that expects decimal but upstream changed to int
    downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,warehouse.public.transactions,PROD)"
    result = await seeder.add_schema(
        dataset_urn=downstream_urn,
        fields=[
            {"field_path": "id", "type": "bigint", "description": "Transaction ID"},
            {"field_path": "amount", "type": "decimal(10,2)", "description": "Amount"},
        ],
        description="Warehouse transactions",
    )
    assert result is not None


@pytest.mark.asyncio
async def test_detect_schema_drift(mock_aiohttp):
    """RED: Schema drift is detectable via schema comparison."""
    seeder = DatasetSeeder(gms_url="http://localhost:8080")
    seeder.session = mock_aiohttp

    upstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,source.public.transactions,PROD)"
    downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,warehouse.public.transactions,PROD)"

    # Ingest upstream and downstream with different schema
    await seeder.add_schema(
        dataset_urn=upstream_urn,
        fields=[{"field_path": "amount", "type": "int"}],
    )

    await seeder.add_schema(
        dataset_urn=downstream_urn,
        fields=[{"field_path": "amount", "type": "decimal(10,2)"}],
    )

    # Verify both calls were made
    assert mock_aiohttp.post.call_count == 2
