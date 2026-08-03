"""Shared fixtures for recorded MCP responses, and the suite's network block."""
from pathlib import Path

import pytest

from tests.hermetic import install as install_network_block


@pytest.fixture(autouse=True)
def _hermetic(request, monkeypatch):
    """Block sockets for every test unless it opts out with allow_network."""
    if request.node.get_closest_marker("allow_network"):
        return
    install_network_block(monkeypatch)


@pytest.fixture
def fixtures_dir():
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def mock_list_datasets_response():
    """Recorded response from DataHub MCP Server for list_datasets."""
    return {
        "datasets": [
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
                "name": "events",
                "platform": "snowflake",
                "owner": "analytics-team",
                "lastModified": 1722595200,
            },
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.users,PROD)",
                "name": "users",
                "platform": "snowflake",
                "owner": "data-eng",
                "lastModified": 1722595000,
            },
        ]
    }


@pytest.fixture
def mock_freshness_response():
    """Recorded response for dataset freshness."""
    return {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        "lastModified": 1722595200,
        "isStale": False,
        "expectedFrequency": 3600,
    }


@pytest.fixture
def mock_schema_response():
    """Recorded response for dataset schema."""
    return {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        "schemaMetadata": {
            "fields": [
                {
                    "fieldPath": "event_id",
                    "type": "BINARY",
                    "description": "Unique event identifier",
                },
                {
                    "fieldPath": "timestamp",
                    "type": "TIMESTAMP",
                    "description": "Event timestamp in UTC",
                },
            ]
        },
        "description": "Canonical events table for the analytics warehouse",
    }


@pytest.fixture
def mock_lineage_response():
    """Recorded response for upstream/downstream lineage."""
    return {
        "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        "upstream": [
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
                "name": "events-raw",
                "platform": "kafka",
            }
        ],
        "downstream": [
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.fact_events,PROD)",
                "name": "fact_events",
                "platform": "snowflake",
            }
        ],
    }


@pytest.fixture
def mock_client(monkeypatch):
    """Mock MCP client for testing (synchronous fixture)."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.walk_upstream = AsyncMock()
    client.get_freshness = AsyncMock()
    client.fetch_schema = AsyncMock()
    client.list_datasets = AsyncMock()

    # Default: single hop upstream
    client.walk_upstream.return_value = MagicMock(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        upstream=[
            {
                "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
                "name": "events-raw",
                "platform": "kafka",
            }
        ],
        downstream=[],
    )

    client.get_freshness.return_value = MagicMock(
        urn="urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
        last_modified=1722595200,
        is_stale=False,
        expected_frequency=3600,
    )

    return client


@pytest.fixture
def mock_client_deep_lineage(monkeypatch):
    """Mock client with 3-hop lineage chain."""
    from unittest.mock import AsyncMock, MagicMock

    client = MagicMock()
    client.walk_upstream = AsyncMock()

    # Simulate multi-hop walk: each call returns next level
    async def multi_hop_walk(urn, hops=1):
        """Simulate walking upstream multiple times."""
        # For this test, simulate a chain: events -> events-raw -> kafka-source -> raw-source
        if "events" in urn and "fact" not in urn:
            return MagicMock(
                urn=urn,
                upstream=[
                    {
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
                        "name": "events-raw",
                        "platform": "kafka",
                    }
                ],
            )
        elif "events-raw" in urn:
            return MagicMock(
                urn=urn,
                upstream=[
                    {
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:s3,kafka-source,PROD)",
                        "name": "kafka-source",
                        "platform": "s3",
                    }
                ],
            )
        elif "kafka-source" in urn:
            return MagicMock(
                urn=urn,
                upstream=[
                    {
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:s3,raw-source,PROD)",
                        "name": "raw-source",
                        "platform": "s3",
                    }
                ],
            )
        else:
            return MagicMock(urn=urn, upstream=[])

    client.walk_upstream = AsyncMock(side_effect=multi_hop_walk)
    return client
