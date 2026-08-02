"""Integration: state history with probe results."""
import pytest
from unittest.mock import AsyncMock
from datahub_rail.state_history import StateHistory, StateDigest
from datahub_rail.probes import ProbeResult, ProbeRegistry


@pytest.fixture
def tmp_history_file(tmp_path):
    """Temp history file for testing."""
    return tmp_path / "history.jsonl"


@pytest.mark.asyncio
async def test_probe_results_recorded_to_history(tmp_history_file):
    """Probe results can be recorded to state history."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # Simulate probe results
    result = ProbeResult(status="fail", message="Dataset is stale")

    history.append(
        dataset_urn="dataset1",
        probe_name="freshness",
        status=result.status,
        message=result.message
    )

    # Verify recorded
    entries = history.load()
    assert len(entries) == 1
    assert entries[0]["status"] == "fail"


@pytest.mark.asyncio
async def test_digest_multiple_runs_workflow(tmp_history_file):
    """Simulate multi-run workflow: first fail, chronic, recovery."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # Run 1: First failure
    history.append("dataset1", "freshness", "fail", "stale")

    digest = StateDigest(path=tmp_history_file)
    summary = digest.render()
    assert "NEW" in summary

    # Run 2: Still failing (chronic)
    history.append("dataset1", "freshness", "fail", "stale")

    summary = digest.render()
    assert "CHRONIC" in summary

    # Run 3: Recovery
    history.append("dataset1", "freshness", "pass", "fresh")

    summary = digest.render()
    assert "RECOVERED" in summary


@pytest.mark.asyncio
async def test_registry_results_to_history_workflow(tmp_history_file):
    """ProbeRegistry results flow to StateHistory."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # Simulate registry config
    config = {
        "probes": [
            {"name": "freshness", "type": "freshness", "params": {"sla_hours": 24}},
        ]
    }

    registry = ProbeRegistry(config=config)

    # Mock client
    client = AsyncMock()
    client.get_freshness.return_value = AsyncMock(last_modified=1000000000000)

    # Run probe (will pass since mock timestamp is fresh)
    result = await registry.probes["freshness"].check(client, "dataset1")

    # Record to history
    history.append("dataset1", "freshness", result.status, result.message)

    # Verify recorded
    entries = history.load()
    assert len(entries) == 1
    assert entries[0]["probe_name"] == "freshness"
