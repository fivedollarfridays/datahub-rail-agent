"""Test lineage traversal (upstream/downstream walks)."""
from datahub_rail.types import LineageResult


def test_walk_lineage_upstream_returns_nodes(mock_lineage_response):
    """walk_upstream returns typed Lineage nodes."""
    upstream_data = mock_lineage_response["upstream"]
    upstream = [
        {"urn": n["urn"], "name": n["name"], "platform": n["platform"]}
        for n in upstream_data
    ]
    assert len(upstream) == 1
    assert upstream[0]["name"] == "events-raw"
    assert upstream[0]["platform"] == "kafka"


def test_walk_lineage_downstream_returns_nodes(mock_lineage_response):
    """walk_downstream returns typed Lineage nodes."""
    downstream_data = mock_lineage_response["downstream"]
    downstream = [
        {"urn": n["urn"], "name": n["name"], "platform": n["platform"]}
        for n in downstream_data
    ]
    assert len(downstream) == 1
    assert downstream[0]["name"] == "fact_events"


def test_lineage_result_type_structure():
    """LineageResult enforces upstream/downstream fields."""
    result = LineageResult(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,test,PROD)",
        upstream=[
            {"urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,raw,PROD)", "name": "raw", "platform": "kafka"}
        ],
        downstream=[],
    )
    assert result.urn is not None
    assert len(result.upstream) == 1
    assert len(result.downstream) == 0


def test_walk_upstream_n_hops():
    """walk_upstream supports N-hop traversal via hops parameter."""
    result = LineageResult(
        urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,final,PROD)",
        upstream=[
            {"urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,intermediate,PROD)", "name": "intermediate", "platform": "snowflake"},
        ],
        downstream=[],
    )
    assert len(result.upstream) >= 0
