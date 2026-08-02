"""State history digest: render NEW / chronic / recovered transitions."""
import json
import pytest
from datetime import datetime, timezone, timedelta
from datahub_rail.state_history import StateHistory, StateDigest


@pytest.fixture
def tmp_history_file(tmp_path):
    """Temp history file for testing."""
    return tmp_path / "history.jsonl"


def test_digest_empty_history_renders_gracefully(tmp_history_file):
    """Digest from empty history (first run) renders gracefully."""
    digest = StateDigest(path=tmp_history_file)

    # Empty history should not crash; returns empty digest
    summary = digest.render()
    assert summary == ""


def test_digest_first_failure_marked_as_new(tmp_history_file):
    """First probe failure is marked as NEW."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # First failure
    history.append(
        dataset_urn="dataset1",
        probe_name="freshness",
        status="fail",
        message="stale data"
    )

    digest = StateDigest(path=tmp_history_file)
    summary = digest.render()

    assert "NEW" in summary
    assert "freshness" in summary
    assert "dataset1" in summary


def test_digest_chronic_failure_collapsed_to_day_n(tmp_history_file):
    """Multiple consecutive failures collapsed to 'still failing (day N)'."""
    # Simulate 3 consecutive days of same failure
    base_time = datetime.now(timezone.utc)
    for day in range(3):
        ts = base_time - timedelta(days=2 - day)
        entry = {
            "dataset_urn": "dataset1",
            "probe_name": "freshness",
            "status": "fail",
            "message": "stale data",
            "timestamp": ts.isoformat(),
        }
        with open(tmp_history_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    digest = StateDigest(path=tmp_history_file)
    summary = digest.render()

    # Should show chronic (day N), not NEW
    assert "day" in summary.lower() or "still" in summary.lower()
    assert "freshness" in summary


def test_digest_recovered_shows_flip_to_pass(tmp_history_file):
    """Flip from fail to pass shows as 'recovered'."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # Fail then pass
    history.append("dataset1", "freshness", "fail", "stale")
    history.append("dataset1", "freshness", "pass", "fresh")

    digest = StateDigest(path=tmp_history_file)
    summary = digest.render()

    assert "recovered" in summary.lower() or "pass" in summary.lower()


def test_digest_multiple_probes_separate_entries(tmp_history_file):
    """Multiple probes on same dataset render separately."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # Multiple probes on same dataset
    history.append("dataset1", "freshness", "fail", "stale")
    history.append("dataset1", "lineage", "pass", "ok")

    digest = StateDigest(path=tmp_history_file)
    summary = digest.render()

    assert "freshness" in summary
    assert "lineage" in summary
