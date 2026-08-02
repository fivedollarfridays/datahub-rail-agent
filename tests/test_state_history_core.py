"""State history persistence: JSONL appending with bounded rotation."""
import json
import pytest
from pathlib import Path
from datetime import datetime, timezone
from datahub_rail.state_history import StateHistory


@pytest.fixture
def tmp_history_file(tmp_path):
    """Temp history file for testing."""
    return tmp_path / "history.jsonl"


def test_state_history_init_creates_file(tmp_history_file):
    """StateHistory init creates file path (doesn't create file yet)."""
    history = StateHistory(path=tmp_history_file, max_entries=100)
    assert history.path == tmp_history_file
    assert history.max_entries == 100


def test_append_first_entry_creates_file(tmp_history_file):
    """First append creates JSONL file with single entry."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    # Append first entry
    history.append(
        dataset_urn="urn:li:dataset:(urn:li:dataPlatform:postgres,orders,PROD)",
        probe_name="freshness",
        status="fail",
        message="Dataset is stale: last modified 2 days ago"
    )

    # File should exist
    assert tmp_history_file.exists()

    # Parse and verify entry
    with open(tmp_history_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    assert len(entries) == 1
    entry = entries[0]
    assert entry["dataset_urn"] == "urn:li:dataset:(urn:li:dataPlatform:postgres,orders,PROD)"
    assert entry["probe_name"] == "freshness"
    assert entry["status"] == "fail"
    assert entry["message"] == "Dataset is stale: last modified 2 days ago"
    assert "timestamp" in entry


def test_append_multiple_entries_preserves_all(tmp_history_file):
    """Multiple appends preserve all entries in JSONL."""
    history = StateHistory(path=tmp_history_file, max_entries=100)

    history.append("dataset1", "freshness", "fail", "stale")
    history.append("dataset2", "lineage", "pass", "ok")
    history.append("dataset1", "freshness", "pass", "fresh")

    with open(tmp_history_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    assert len(entries) == 3
    assert entries[0]["dataset_urn"] == "dataset1"
    assert entries[1]["dataset_urn"] == "dataset2"
    assert entries[2]["dataset_urn"] == "dataset1"


def test_rotation_removes_oldest_when_exceeding_max(tmp_history_file):
    """When entries exceed max_entries, oldest entries are removed."""
    history = StateHistory(path=tmp_history_file, max_entries=3)

    # Append 5 entries (exceeds max of 3)
    for i in range(5):
        history.append(f"dataset{i}", "freshness", "pass", f"entry{i}")

    with open(tmp_history_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    # Should have exactly 3 entries (newest)
    assert len(entries) == 3
    # Should have entries 2, 3, 4 (oldest 0, 1 removed)
    assert entries[0]["dataset_urn"] == "dataset2"
    assert entries[1]["dataset_urn"] == "dataset3"
    assert entries[2]["dataset_urn"] == "dataset4"


def test_rotation_maintains_order(tmp_history_file):
    """Rotation maintains chronological order of remaining entries."""
    history = StateHistory(path=tmp_history_file, max_entries=2)

    history.append("a", "freshness", "pass", "msg_a")
    history.append("b", "lineage", "fail", "msg_b")
    history.append("c", "schema", "pass", "msg_c")

    with open(tmp_history_file) as f:
        entries = [json.loads(line) for line in f if line.strip()]

    assert len(entries) == 2
    assert entries[0]["dataset_urn"] == "b"
    assert entries[1]["dataset_urn"] == "c"
