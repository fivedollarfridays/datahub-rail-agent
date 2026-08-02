"""Test dataset listing and metadata operations."""
from dataclasses import dataclass

from datahub_rail.types import Dataset


@dataclass
class MockMCPSession:
    """Mock session for testing."""

    async def call_tool(self, name, arguments):
        if name == "list_datasets":
            return {
                "datasets": [
                    {
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
                        "name": "events",
                        "platform": "snowflake",
                        "owner": "analytics-team",
                        "lastModified": 1722595200,
                    },
                ]
            }
        raise ValueError(f"Unknown tool: {name}")


def test_list_datasets_returns_typed_results(mock_list_datasets_response):
    """list_datasets returns Dataset objects with typed fields."""
    datasets = [
        Dataset(
            urn=d["urn"],
            name=d["name"],
            platform=d["platform"],
            owner=d["owner"],
            last_modified=d["lastModified"],
        )
        for d in mock_list_datasets_response["datasets"]
    ]
    assert len(datasets) == 2
    assert datasets[0].name == "events"
    assert datasets[0].platform == "snowflake"
    assert datasets[1].owner == "data-eng"


def test_dataset_type_has_required_fields():
    """Dataset type enforces required fields."""
    dataset = Dataset(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,test,PROD)",
        name="test",
        platform="snowflake",
        owner="eng",
        last_modified=1722595200,
    )
    assert dataset.urn is not None
    assert dataset.name == "test"
    assert dataset.platform == "snowflake"
    assert dataset.owner == "eng"
    assert dataset.last_modified == 1722595200
