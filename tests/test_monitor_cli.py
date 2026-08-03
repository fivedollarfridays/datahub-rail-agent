"""`check-monitor` as a one-command answer to "is the watcher still alive?".

Exit code is the product here: this verb is meant to be the thing a cron or a
CI step runs, so a dead monitor turns into a non-zero exit and a message that
names the last run and the command that restarts it.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from datahub_rail import agent, monitor

DIGEST = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.daily_digest,PROD)"


def _entity(stamp):
    return {
        "urn": DIGEST,
        "structuredProperties": {
            "value": {
                "properties": [
                    {"propertyUrn": monitor.RAIL_LAST_RUN_URN,
                     "values": [{"string": stamp}]}
                ]
            }
        },
    }


class _StubReader:
    """GMSReader stand-in: no socket is opened by any test in this file."""

    entities: list = []

    def __init__(self, *args, **kwargs):
        pass

    async def connect(self):
        return None

    async def disconnect(self):
        return None

    async def scroll_datasets(self, aspects, count=100, max_pages=50):
        return list(self.entities)


def _reader_with(stamps):
    """Stub reader class returning one entity per stamp."""
    return type("_R", (_StubReader,), {"entities": [_entity(s) for s in stamps]})


def _iso(hours_ago):
    return (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()


def test_recent_write_back_exits_zero(capsys):
    """A monitor that wrote an hour ago passes a 24h check."""
    with patch.object(monitor, "GMSReader", _reader_with([_iso(1)])):
        code = agent.main(["check-monitor", "--max-age-hours", "24"])

    assert code == 0
    assert "[OK] Rail monitor is live" in capsys.readouterr().out


def test_stale_write_back_exits_one_and_names_the_rerun(capsys):
    """Nine days since the last write-back: exit 1, loud, actionable."""
    stamp = _iso(9 * 24)
    with patch.object(monitor, "GMSReader", _reader_with([stamp])):
        code = agent.main(["check-monitor", "--max-age-hours", "24"])

    captured = capsys.readouterr()
    assert code == 1
    assert "MONITOR IS DEAD" in captured.err
    assert stamp[:16] in captured.err
    assert "--writeback" in captured.err


def test_no_markers_exits_one(capsys):
    """An estate with no rail markers is blind, and blind fails loudly."""
    with patch.object(monitor, "GMSReader", _reader_with([])):
        code = agent.main(["check-monitor", "--max-age-hours", "24"])

    assert code == 1
    assert "never written back" in capsys.readouterr().err.lower()


def test_max_age_hours_is_the_operator_s_tolerance(capsys):
    """The same estate passes a wide window and fails a narrow one."""
    stamp = _iso(30)
    with patch.object(monitor, "GMSReader", _reader_with([stamp])):
        wide = agent.main(["check-monitor", "--max-age-hours", "48"])
        narrow = agent.main(["check-monitor", "--max-age-hours", "24"])

    assert (wide, narrow) == (0, 1)


def test_rerun_line_echoes_the_config_the_check_was_given(capsys):
    """The printed fix points at this estate's config file."""
    with patch.object(monitor, "GMSReader", _reader_with([])):
        agent.main(["check-monitor", "--max-age-hours", "24", "--config", "config/ops.yaml"])

    assert "--config config/ops.yaml --writeback" in capsys.readouterr().err


def test_check_monitor_verb_does_not_disturb_the_default_run():
    """The demo invocation still parses exactly as it did before this verb."""
    parsed = agent.build_parser().parse_args([])

    assert parsed.config == "config/probes.yaml"
    assert parsed.datahub_url == "http://localhost:8080"
    assert parsed.writeback is False
    assert not hasattr(parsed, "max_age_hours")


@pytest.mark.asyncio
async def test_check_reads_only_the_structured_properties_aspect():
    """Liveness is judged from write-back markers, never a heartbeat file."""
    requested = {}

    class _Recording(_StubReader):
        entities = []

        async def scroll_datasets(self, aspects, count=100, max_pages=50):
            requested["aspects"] = aspects
            return []

    with patch.object(monitor, "GMSReader", _Recording):
        await monitor.check(
            gms_url="http://localhost:8080", token="", max_age_hours=24,
            rerun_command="x",
        )

    assert requested["aspects"] == ["structuredProperties"]
