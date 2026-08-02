"""Provenance verification: facts computed from graph reads only."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datahub_rail.triage import TriageEngine


@pytest.mark.asyncio
async def test_lineage_fact_sourced_from_walk_upstream():
    """Lineage path fact comes directly from walk_upstream calls."""
    engine = TriageEngine()
    client = MagicMock()

    # Mock walk_upstream
    client.walk_upstream = AsyncMock(return_value=MagicMock(
        urn="test",
        upstream=[
            {"urn": "up1", "name": "upstream-node", "platform": "kafka"}
        ],
    ))

    # Walk upstream
    nodes = await engine._walk_upstream_with_distance(client, "test", max_hops=1)

    # Verify walk_upstream was called (provenance)
    assert client.walk_upstream.called
    assert len(nodes) > 0
    assert nodes[0][0]["name"] == "upstream-node"


@pytest.mark.asyncio
async def test_freshness_fact_sourced_from_get_freshness():
    """Freshness fact comes directly from get_freshness call."""
    engine = TriageEngine()
    client = MagicMock()

    # Mock get_freshness
    client.get_freshness = AsyncMock(return_value=MagicMock(
        urn="dataset-urn",
        last_modified=1722595200,
        is_stale=True,
        expected_frequency=3600,
    ))

    # Gather evidence
    evidence = await engine._gather_evidence(client, "dataset-urn")

    # Verify get_freshness was called (provenance)
    assert client.get_freshness.called
    assert evidence["last_modified"] == 1722595200
    assert evidence["is_stale"]


@pytest.mark.asyncio
async def test_report_markdown_cites_provenance_note():
    """Report footer states all facts sourced from graph reads."""
    engine = TriageEngine()

    report_data = {
        "failing_dataset": {"name": "test", "owner": "owner"},
        "root_cause": {"name": "root", "owner": "root-owner", "distance": 1},
        "lineage_path": [],
        "probe_message": "test",
        "last_modified": None,
    }

    markdown = engine._render_report(report_data)

    # Should include provenance note
    assert "All facts in this report sourced from DataHub context graph reads" in markdown


def test_root_cause_selection_deterministic():
    """Root-cause tie-breaking is deterministic (URN-sorted)."""
    engine = TriageEngine()

    # Same distance, different URNs
    failing_nodes = [
        ({"urn": "urn:z", "name": "z-node"}, 2),
        ({"urn": "urn:a", "name": "a-node"}, 2),
        ({"urn": "urn:m", "name": "m-node"}, 2),
    ]

    root_cause = engine._pick_root_cause(failing_nodes)

    # Must pick a-node consistently (lowest URN)
    assert root_cause["urn"] == "urn:a"
    assert root_cause["name"] == "a-node"

    # Run again with different order — should be identical
    failing_nodes_reordered = [
        ({"urn": "urn:m", "name": "m-node"}, 2),
        ({"urn": "urn:z", "name": "z-node"}, 2),
        ({"urn": "urn:a", "name": "a-node"}, 2),
    ]

    root_cause_2 = engine._pick_root_cause(failing_nodes_reordered)

    assert root_cause == root_cause_2
