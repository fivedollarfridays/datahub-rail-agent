"""Is the monitor itself still running? Answered from capture evidence.

The failure this encodes: a scheduled watcher stopped producing check runs
entirely and nothing said so — the absence of output looked exactly like a
quiet, healthy week. The only trustworthy liveness signal is what the agent
actually wrote into the graph, so this reads the ``rail.last_run`` structured
property PR #3 publishes and refuses to treat "no evidence" as healthy.
"""
from datetime import datetime, timedelta, timezone

from datahub_rail.monitor import (
    RAIL_LAST_RUN_URN,
    evaluate,
    last_run_value,
    newest_run,
)

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=timezone.utc)
DIGEST = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.daily_digest,PROD)"
PLANNER = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.planner_runs,PROD)"


def _entity(urn, stamp):
    """Scroll-shaped entity carrying a rail.last_run structured property."""
    return {
        "urn": urn,
        "structuredProperties": {
            "value": {
                "properties": [
                    {"propertyUrn": "urn:li:structuredProperty:rail.status",
                     "values": [{"string": "PASS"}]},
                    {"propertyUrn": RAIL_LAST_RUN_URN, "values": [{"string": stamp}]},
                ]
            }
        },
    }


def test_last_run_value_reads_the_rail_property():
    """The run stamp comes off the dataset the agent wrote it to."""
    assert last_run_value(_entity(DIGEST, "2026-08-03T11:00:00+00:00")) == (
        "2026-08-03T11:00:00+00:00"
    )


def test_last_run_value_is_none_when_rail_never_wrote():
    """A dataset with no rail property yields nothing, not a default."""
    assert last_run_value({"urn": DIGEST}) is None
    assert last_run_value(
        {"urn": DIGEST, "structuredProperties": {"value": {"properties": []}}}
    ) is None


def test_newest_run_picks_the_latest_stamp_across_the_estate():
    """One live dataset is enough: the newest write wins."""
    stamp, urn = newest_run(
        [
            _entity(DIGEST, "2026-07-25T06:00:00+00:00"),
            _entity(PLANNER, "2026-08-03T11:30:00+00:00"),
        ]
    )

    assert stamp == datetime(2026, 8, 3, 11, 30, tzinfo=timezone.utc)
    assert urn == PLANNER


def test_newest_run_ignores_unparseable_stamps():
    """A malformed stamp is skipped and logged over, never crashes the check."""
    stamp, urn = newest_run(
        [_entity(DIGEST, "not-a-timestamp"), _entity(PLANNER, "2026-08-03T11:30:00+00:00")]
    )

    assert stamp == datetime(2026, 8, 3, 11, 30, tzinfo=timezone.utc)
    assert urn == PLANNER


def test_recent_run_passes():
    """Inside the window: exit 0 and say when it last ran."""
    verdict = evaluate(NOW - timedelta(hours=2), DIGEST, max_age_hours=24, now=NOW)

    assert verdict.ok is True
    assert verdict.exit_code == 0
    assert "2026-08-03T10:00:00+00:00" in verdict.message
    assert "2.0h ago" in verdict.message


def test_stale_run_fails_loudly_with_time_and_rerun_command():
    """Outside the window: exit 1, name the last run, name the fix."""
    verdict = evaluate(NOW - timedelta(hours=216), DIGEST, max_age_hours=24, now=NOW)

    assert verdict.ok is False
    assert verdict.exit_code == 1
    assert "MONITOR IS DEAD" in verdict.message
    assert "2026-07-25T12:00:00+00:00" in verdict.message
    assert "216.0h ago" in verdict.message
    assert "limit 24h" in verdict.message
    assert "python -m datahub_rail.agent --config config/probes.yaml --writeback" in (
        verdict.message
    )


def test_no_markers_at_all_is_a_blind_state_not_a_pass():
    """No write-back evidence anywhere fails loudly rather than assuming health."""
    verdict = evaluate(None, None, max_age_hours=24, now=NOW)

    assert verdict.ok is False
    assert verdict.exit_code == 1
    assert "monitor has never written back (or write-back disabled)" in (
        verdict.message.lower()
    )
    assert "python -m datahub_rail.agent --config config/probes.yaml --writeback" in (
        verdict.message
    )


def test_rerun_command_echoes_the_operator_s_own_flags():
    """The printed fix is the command for *this* estate, not a generic one."""
    verdict = evaluate(
        None, None, max_age_hours=24, now=NOW,
        rerun_command="python -m datahub_rail.agent --config config/ops.yaml --writeback",
    )

    assert "--config config/ops.yaml" in verdict.message
