"""Delta-aware verdict derivation for write-back.

The verdict written onto a dataset must match the semantics the digest
already renders (NEW / CHRONIC day N / RECOVERED), derived read-only from
the state history so the existing history writer stays untouched.
"""

from datahub_rail.verdicts import verdict_for_dataset

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)"
OTHER = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)"


def _entry(urn=URN, probe="freshness", status="pass", message="ok", ts="2026-08-03T00:00:00+00:00"):
    return {
        "dataset_urn": urn,
        "probe_name": probe,
        "status": status,
        "message": message,
        "timestamp": ts,
    }


def test_no_history_for_dataset_yields_no_verdict():
    """A dataset the agent never probed gets nothing written to it."""
    assert verdict_for_dataset([_entry(urn=OTHER)], URN) is None


def test_single_passing_run_is_pass():
    """First-ever passing run reports PASS with the probe that produced it."""
    verdict = verdict_for_dataset([_entry(status="pass")], URN)
    assert verdict.label == "PASS"
    assert verdict.status_class == "PASS"
    assert verdict.probes == ["freshness"]


def test_first_failing_run_is_new_fail():
    """A failure with no prior history is NEW-FAIL, not CHRONIC."""
    verdict = verdict_for_dataset([_entry(status="fail", message="stale")], URN)
    assert verdict.label == "NEW-FAIL"
    assert verdict.status_class == "NEW-FAIL"
    assert verdict.probes == ["freshness"]


def test_consecutive_failures_carry_the_day_count():
    """Three failing runs in a row render as CHRONIC-day-3, matching the digest."""
    entries = [_entry(status="fail") for _ in range(3)]
    verdict = verdict_for_dataset(entries, URN)
    assert verdict.status_class == "CHRONIC"
    assert verdict.label == "CHRONIC-day-3"


def test_fail_then_pass_is_recovered():
    """A pass immediately after a failure is RECOVERED, not a plain PASS."""
    entries = [_entry(status="fail"), _entry(status="pass")]
    verdict = verdict_for_dataset(entries, URN)
    assert verdict.status_class == "RECOVERED"
    assert verdict.label == "RECOVERED"


def test_worst_probe_wins_and_only_failing_probes_are_named():
    """With a healthy probe and a chronic one, the chronic verdict is written."""
    entries = [
        _entry(probe="freshness", status="pass"),
        _entry(probe="freshness", status="pass"),
        _entry(probe="schema", status="fail"),
        _entry(probe="schema", status="fail"),
    ]
    verdict = verdict_for_dataset(entries, URN)
    assert verdict.label == "CHRONIC-day-2"
    assert verdict.probes == ["schema"]


def test_all_probes_named_when_everything_passes():
    """A clean dataset lists every probe that vouched for it."""
    entries = [_entry(probe="schema", status="pass"), _entry(probe="freshness", status="pass")]
    verdict = verdict_for_dataset(entries, URN)
    assert verdict.label == "PASS"
    assert verdict.probes == ["freshness", "schema"]
