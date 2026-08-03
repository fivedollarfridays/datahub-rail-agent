"""Run-level write-back: incident pointers, idempotency, and fail-soft.

Doctrine: a write-back fault is loud but never breaks the probe run. The
probe run is the product; publishing findings is an enhancement on top.
"""
import json

import pytest

from datahub_rail.writeback import find_incident_report, publish_run

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)"
RUN_AT = "2026-08-03T12:00:00+00:00"


def _history(tmp_path, statuses):
    path = tmp_path / "state_history.jsonl"
    with open(path, "w") as handle:
        for status in statuses:
            handle.write(
                json.dumps(
                    {
                        "dataset_urn": URN,
                        "probe_name": "freshness",
                        "status": status,
                        "message": "m",
                        "timestamp": RUN_AT,
                    }
                )
                + "\n"
            )
    return path


def _report():
    return {"datasets": [{"urn": URN, "name": "users", "status": "fail"}]}


class RecordingWriter:
    """Stands in for the HTTP writer, remembering every apply payload."""

    def __init__(self, fail=False):
        self.applied = []
        self.schema_calls = 0
        self._fail = fail

    async def connect(self):
        return None

    async def disconnect(self):
        return None

    async def ensure_schema(self):
        self.schema_calls += 1

    async def apply(self, dataset_urn, verdict, run_timestamp, incident_file=None):
        if self._fail:
            raise RuntimeError("GMS unreachable")
        payload = {
            "urn": dataset_urn,
            "label": verdict.label,
            "status_class": verdict.status_class,
            "run": run_timestamp,
            "incident": incident_file,
        }
        self.applied.append(payload)
        return payload


def test_find_incident_report_picks_the_newest_report_for_the_dataset(tmp_path):
    """The pointer names this dataset's latest report, not another dataset's."""
    (tmp_path / "incident_users_20260801T000000.md").write_text("old")
    (tmp_path / "incident_users_20260803T120000.md").write_text("new")
    (tmp_path / "incident_events_20260803T120000.md").write_text("other")

    assert find_incident_report(tmp_path, "users") == "incident_users_20260803T120000.md"


def test_find_incident_report_is_none_when_the_dataset_is_healthy(tmp_path):
    """No report means no pointer — nothing stale gets written."""
    assert find_incident_report(tmp_path, "users") is None


@pytest.mark.asyncio
async def test_publish_run_writes_verdict_with_incident_pointer(tmp_path):
    """A failing dataset publishes its verdict plus the report filename."""
    history = _history(tmp_path, ["fail"])
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    (outbox / "incident_users_20260803T120000.md").write_text("report")
    writer = RecordingWriter()

    result = await publish_run(
        _report(), history_path=history, outbox=outbox, writer=writer, run_timestamp=RUN_AT
    )

    assert result["written"] == 1
    assert writer.applied[0]["label"] == "NEW-FAIL"
    assert writer.applied[0]["incident"] == "incident_users_20260803T120000.md"


@pytest.mark.asyncio
async def test_recovered_dataset_writes_no_incident_pointer(tmp_path):
    """RECOVERED clears the failure marker instead of carrying a stale report."""
    history = _history(tmp_path, ["fail", "pass"])
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    writer = RecordingWriter()

    await publish_run(
        {"datasets": [{"urn": URN, "name": "users", "status": "pass"}]},
        history_path=history,
        outbox=outbox,
        writer=writer,
        run_timestamp=RUN_AT,
    )

    assert writer.applied[0]["status_class"] == "RECOVERED"
    assert writer.applied[0]["incident"] is None


@pytest.mark.asyncio
async def test_repeat_publish_is_idempotent(tmp_path):
    """Publishing the same run twice writes byte-identical payloads."""
    history = _history(tmp_path, ["fail"])
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    writer = RecordingWriter()

    await publish_run(_report(), history_path=history, outbox=outbox, writer=writer,
                      run_timestamp=RUN_AT)
    await publish_run(_report(), history_path=history, outbox=outbox, writer=writer,
                      run_timestamp=RUN_AT)

    assert writer.applied[0] == writer.applied[1]


@pytest.mark.asyncio
async def test_write_back_failure_never_breaks_the_run(tmp_path, caplog):
    """A GMS outage during write-back is logged loud and the run still completes."""
    history = _history(tmp_path, ["fail"])
    writer = RecordingWriter(fail=True)

    result = await publish_run(
        _report(), history_path=history, outbox=tmp_path, writer=writer, run_timestamp=RUN_AT
    )

    assert result["failed"] == 1
    assert result["written"] == 0
    assert any(rec.levelname == "ERROR" for rec in caplog.records)


@pytest.mark.asyncio
async def test_publish_run_skips_datasets_with_no_history(tmp_path):
    """Nothing is written to a dataset this run never probed."""
    history = _history(tmp_path, ["pass"])
    writer = RecordingWriter()

    result = await publish_run(
        {"datasets": [{"urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,ghost,PROD)",
                       "name": "ghost", "status": "pass"}]},
        history_path=history,
        outbox=tmp_path,
        writer=writer,
        run_timestamp=RUN_AT,
    )

    assert result["skipped"] == 1
    assert writer.applied == []
