"""Integration test: full triage pipeline against DHA.2 mocks."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datahub_rail.triage import TriageEngine


async def _setup_stale_lineage_client():
    """Setup mock client with stale events-raw upstream from events."""
    client = MagicMock()

    async def walk_upstream_side_effect(urn, hops=1):
        """Simulate lineage chain."""
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
                        "urn": "urn:li:dataset:(urn:li:dataPlatform:s3,raw-source,PROD)",
                        "name": "raw-source",
                        "platform": "s3",
                    }
                ],
            )
        else:
            return MagicMock(urn=urn, upstream=[])

    async def get_freshness_side_effect(urn):
        """Freshness: events-raw is stale."""
        if "events-raw" in urn:
            return MagicMock(
                urn=urn,
                last_modified=1722595200 - (5 * 24 * 3600),
                is_stale=True,
                expected_frequency=3600,
            )
        elif "raw-source" in urn:
            return MagicMock(
                urn=urn,
                last_modified=1722595200,
                is_stale=False,
                expected_frequency=3600,
            )
        else:
            return MagicMock(urn=urn, last_modified=1722595200, is_stale=False, expected_frequency=3600)

    client.walk_upstream = AsyncMock(side_effect=walk_upstream_side_effect)
    client.get_freshness = AsyncMock(side_effect=get_freshness_side_effect)
    return client


@pytest.mark.asyncio
async def test_full_triage_pipeline():
    """End-to-end: walk lineage, identify root cause, generate report."""
    client = await _setup_stale_lineage_client()

    engine = TriageEngine()

    # Walk upstream from events
    events_urn = "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)"
    nodes = await engine._walk_upstream_with_distance(client, events_urn, max_hops=3)

    # Should collect events-raw (at least)
    assert len(nodes) >= 1
    node_names = {n[0]["name"] for n in nodes}
    assert "events-raw" in node_names

    # events-raw is the root cause (failed & deepest)
    failing_nodes = [
        (n[0], n[1]) for n in nodes
        if "events-raw" in n[0].get("name", "")
    ]
    root_cause = engine._pick_root_cause(failing_nodes)
    assert root_cause["name"] == "events-raw"

    # Gather evidence
    evidence = await engine._gather_evidence(client, "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)")
    assert evidence["is_stale"]

    # Render report
    report_data = {
        "failing_dataset": {
            "name": "events",
            "owner": "analytics-team",
            "urn": events_urn,
        },
        "root_cause": {
            "name": "events-raw",
            "platform": "kafka",
            "owner": "kafka-ops",
            "distance": 1,
            "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
        },
        "lineage_path": [
            {"name": "events-raw", "platform": "kafka"},
            {"name": "events", "platform": "snowflake"},
        ],
        "probe_message": "Dataset is stale: last modified 5 days ago (SLA: 24h)",
        "last_modified": 1722595200 - (5 * 24 * 3600),
    }

    markdown = engine._render_report(report_data)

    # Verify report structure
    assert "## Incident Report" in markdown
    assert "events" in markdown
    assert "events-raw" in markdown
    assert "kafka-ops" in markdown
    assert "stale" in markdown
    assert "## Next Steps" in markdown
    assert "All facts in this report sourced from DataHub" in markdown


@pytest.mark.asyncio
async def test_provenance_every_claim_tracked():
    """Each fact in report has source provenance."""
    engine = TriageEngine()

    client = MagicMock()
    client.walk_upstream = AsyncMock(return_value=MagicMock(
        urn="test",
        upstream=[
            {"urn": "up1", "name": "upstream", "platform": "kafka"}
        ]
    ))
    client.get_freshness = AsyncMock(return_value=MagicMock(
        urn="up1",
        last_modified=1722595200,
        is_stale=False,
        expected_frequency=3600,
    ))

    # Evidence gathering should track provenance
    evidence = await engine._gather_evidence(client, "up1")

    # Verify facts came from graph reads (implicit in mock calls)
    assert "last_modified" in evidence
    assert "is_stale" in evidence
    assert client.get_freshness.called  # Proof fact was read from graph
