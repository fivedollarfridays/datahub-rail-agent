"""Lineage walk triage: collect upstream nodes with distances."""
import pytest
from datahub_rail.triage import TriageEngine


@pytest.mark.asyncio
async def test_walk_upstream_single_hop(mock_client):
    """Walk 1 hop upstream, collect nodes with distance."""
    engine = TriageEngine()
    nodes = await engine._walk_upstream_with_distance(
        mock_client,
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        max_hops=1
    )

    # Should return list of (node_dict, distance) tuples
    assert len(nodes) == 1
    node, distance = nodes[0]
    assert node["urn"] == "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)"
    assert distance == 1


@pytest.mark.asyncio
async def test_walk_upstream_multiple_hops(mock_client_deep_lineage):
    """Walk multiple hops upstream, accumulate all nodes."""
    engine = TriageEngine()
    nodes = await engine._walk_upstream_with_distance(
        mock_client_deep_lineage,
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        max_hops=3
    )

    # Should return nodes at increasing distances
    distances = {node["name"]: dist for node, dist in nodes}
    assert "events-raw" in distances
    assert distances["events-raw"] == 1


@pytest.mark.asyncio
async def test_filter_failing_nodes(mock_client):
    """Filter upstream nodes to only those with failed probes."""
    engine = TriageEngine()

    # Mock probe results: events-raw failed freshness
    failing_urns = {
        "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)"
    }

    nodes = await engine._walk_upstream_with_distance(
        mock_client,
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        max_hops=1
    )

    failing_nodes = [
        (node, dist) for node, dist in nodes
        if node["urn"] in failing_urns
    ]

    assert len(failing_nodes) == 1
    assert failing_nodes[0][0]["name"] == "events-raw"


@pytest.mark.asyncio
async def test_filter_no_failing_nodes(mock_client):
    """When no nodes failed, return empty list."""
    engine = TriageEngine()

    nodes = await engine._walk_upstream_with_distance(
        mock_client,
        "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
        max_hops=1
    )

    failing_nodes = [
        (node, dist) for node, dist in nodes
        if node["urn"] in set()  # Empty failing set
    ]

    assert len(failing_nodes) == 0
