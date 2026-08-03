"""Detecting a producer-healthy / delivery-broken edge.

The failure this encodes: a daily deliverable stopped arriving for nine days
while the pipeline that produces it ran green every night. Watching the
producer said "healthy" the whole time, so the break was misdiagnosed as a
scheduler problem for a week. The graph already holds both timestamps — a
stale output whose immediate upstreams are all *fresh* is not a dead
scheduler, it is a broken edge.
"""
from datahub_rail.edge_break import detect_edge_break, is_past_sla

HOUR_MS = 3600 * 1000
NOW_MS = 1_800_000_000_000


def _node(name, age_hours):
    """A graph node with a capture timestamp `age_hours` old."""
    return {"name": name, "last_modified": NOW_MS - int(age_hours * HOUR_MS)}


def test_stale_output_with_fresh_upstream_is_an_edge_break():
    """Producer ran an hour ago, output has not moved in nine days."""
    finding = detect_edge_break(
        failing=_node("daily_digest", 9 * 24),
        upstreams=[_node("planner_runs", 1)],
        sla_hours=24,
        now_ms=NOW_MS,
    )

    assert finding is not None
    assert finding["failing"]["name"] == "daily_digest"
    assert finding["upstreams"][0]["name"] == "planner_runs"
    assert finding["failing"]["age_hours"] == 9 * 24
    assert finding["upstreams"][0]["age_hours"] == 1
    assert finding["sla_hours"] == 24


def test_both_stale_is_a_normal_root_cause_walk():
    """When the upstream is stale too, the ordinary lineage walk owns it."""
    finding = detect_edge_break(
        failing=_node("daily_digest", 9 * 24),
        upstreams=[_node("planner_runs", 8 * 24)],
        sla_hours=24,
        now_ms=NOW_MS,
    )

    assert finding is None


def test_one_stale_upstream_suppresses_the_callout():
    """Any stale immediate upstream means the break may be genuinely upstream."""
    finding = detect_edge_break(
        failing=_node("daily_digest", 9 * 24),
        upstreams=[_node("planner_runs", 1), _node("contacts", 5 * 24)],
        sla_hours=24,
        now_ms=NOW_MS,
    )

    assert finding is None


def test_fresh_output_is_never_an_edge_break():
    """A failing-but-fresh dataset failed some other probe; no callout."""
    finding = detect_edge_break(
        failing=_node("events", 2),
        upstreams=[_node("planner_runs", 1)],
        sla_hours=24,
        now_ms=NOW_MS,
    )

    assert finding is None


def test_no_upstreams_means_no_edge_to_break():
    """A source dataset has no delivery edge — the stale table is the fault."""
    finding = detect_edge_break(
        failing=_node("orders_archive", 45 * 24),
        upstreams=[],
        sla_hours=24,
        now_ms=NOW_MS,
    )

    assert finding is None


def test_unreadable_timestamps_never_fabricate_a_finding():
    """Missing capture evidence is not evidence of an edge break."""
    assert (
        detect_edge_break(
            failing={"name": "daily_digest", "last_modified": None},
            upstreams=[_node("planner_runs", 1)],
            sla_hours=24,
            now_ms=NOW_MS,
        )
        is None
    )
    assert (
        detect_edge_break(
            failing=_node("daily_digest", 9 * 24),
            upstreams=[{"name": "planner_runs", "last_modified": None}],
            sla_hours=24,
            now_ms=NOW_MS,
        )
        is None
    )


def test_is_past_sla_gates_the_upstream_reads():
    """Callers check this before spending graph reads on upstream freshness."""
    assert is_past_sla(_node("daily_digest", 9 * 24), 24, NOW_MS) is True
    assert is_past_sla(_node("daily_digest", 2), 24, NOW_MS) is False
    assert is_past_sla({"name": "x", "last_modified": None}, 24, NOW_MS) is False


def test_gap_hours_is_how_long_the_producer_outran_its_output():
    """The headline number: producer moved N hours more recently than output."""
    finding = detect_edge_break(
        failing=_node("daily_digest", 9 * 24),
        upstreams=[_node("planner_runs", 2), _node("contacts", 6)],
        sla_hours=24,
        now_ms=NOW_MS,
    )

    assert finding["gap_hours"] == 9 * 24 - 2
