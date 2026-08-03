"""Triage emits the edge-break callout from a two-node estate.

Fixture is the real incident in miniature: a producer that ran an hour ago
and an output that has not moved in nine days. The inverse fixture — both
stale — must fall through to the ordinary root-cause walk, because there the
upstream really is the suspect.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from datahub_rail.triage import TriageEngine

HOUR_MS = 3600 * 1000

DOWNSTREAM = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.daily_digest,PROD)"
UPSTREAM = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.planner_runs,PROD)"


def _two_node_estate(downstream_age_hours: float, upstream_age_hours: float):
    """Client over one edge: planner_runs → daily_digest, with capture times."""
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    ages = {
        DOWNSTREAM: downstream_age_hours,
        UPSTREAM: upstream_age_hours,
    }

    async def walk(urn, hops=1):
        upstream = (
            [{"urn": UPSTREAM, "name": "planner_runs", "platform": "postgres"}]
            if urn == DOWNSTREAM
            else []
        )
        return MagicMock(urn=urn, upstream=upstream, downstream=[])

    async def freshness(urn):
        return MagicMock(
            urn=urn,
            last_modified=now_ms - int(ages[urn] * HOUR_MS),
            is_stale=ages[urn] > 24,
            expected_frequency=0,
        )

    client = MagicMock()
    client.walk_upstream = AsyncMock(side_effect=walk)
    client.get_freshness = AsyncMock(side_effect=freshness)
    return client


async def _report(client, tmp_path):
    """Generate the incident report for the stale downstream."""
    return await TriageEngine().generate_incident_report(
        client=client,
        failing_dataset_urn=DOWNSTREAM,
        failing_dataset_name="daily_digest",
        dataset_owner="ops",
        probe_name="freshness",
        probe_status="fail",
        probe_message="Dataset is stale: last modified 9 days ago (SLA: 24h)",
        outbox_dir=tmp_path,
        sla_hours=24,
    )


@pytest.mark.asyncio
async def test_fresh_upstream_stale_output_gets_the_callout(tmp_path):
    """Producer fresh, output nine days stale: the report says edge, not job."""
    markdown = await _report(_two_node_estate(9 * 24, 1), tmp_path)

    assert "### Producer Healthy, Delivery Broken" in markdown
    assert "`daily_digest` | failing output" in markdown
    assert "`planner_runs` | immediate upstream" in markdown
    assert "not the scheduler" in markdown


@pytest.mark.asyncio
async def test_callout_shows_both_capture_timestamps(tmp_path):
    """Both timestamps are in the block — that is the whole diagnostic."""
    markdown = await _report(_two_node_estate(9 * 24, 1), tmp_path)

    block = markdown.split("### Producer Healthy, Delivery Broken")[1]
    block = block.split("### Root-Cause Candidate")[0]
    assert "216h old" in block
    assert "1h old" in block
    assert "215h more recently" in block


@pytest.mark.asyncio
async def test_both_stale_falls_through_to_the_root_cause_walk(tmp_path):
    """A stale upstream is a genuine upstream suspect: no callout, normal walk."""
    markdown = await _report(_two_node_estate(9 * 24, 8 * 24), tmp_path)

    assert "Producer Healthy" not in markdown
    assert "### Root-Cause Candidate" in markdown
    assert "Dataset: **planner_runs**" in markdown


@pytest.mark.asyncio
async def test_fresh_output_reads_no_upstream_freshness(tmp_path):
    """A non-stale failure spends no graph reads looking for an edge break."""
    client = _two_node_estate(2, 1)

    markdown = await _report(client, tmp_path)

    assert "Producer Healthy" not in markdown
    assert client.get_freshness.await_count == 1, "only the failing dataset was read"
