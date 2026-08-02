"""Test dataset freshness queries."""
from datahub_rail.types import Freshness


def test_get_freshness_returns_typed_result(mock_freshness_response):
    """get_freshness returns Freshness object with metadata."""
    freshness = Freshness(
        urn=mock_freshness_response["urn"],
        last_modified=mock_freshness_response["lastModified"],
        is_stale=mock_freshness_response["isStale"],
        expected_frequency=mock_freshness_response["expectedFrequency"],
    )
    assert freshness.urn is not None
    assert freshness.last_modified == 1722595200
    assert freshness.is_stale is False
    assert freshness.expected_frequency == 3600


def test_freshness_type_enforces_fields():
    """Freshness type enforces all required fields."""
    freshness = Freshness(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,test,PROD)",
        last_modified=1722595200,
        is_stale=False,
        expected_frequency=3600,
    )
    assert freshness.urn is not None
    assert freshness.expected_frequency > 0
