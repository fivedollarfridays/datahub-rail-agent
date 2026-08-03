"""Producer-healthy / delivery-broken detection.

A stale dataset whose immediate upstreams are all *fresh* is a different
fault from a stale dataset behind a stalled pipeline. The producer ran; the
output never arrived. The break sits on the edge between them — a missing
config file, an unmet prerequisite, an expired credential — and no amount of
staring at the producer's green run history will show it.

This module is pure: it takes two capture timestamps already read from the
graph and decides whether the pair is that shape. It fabricates nothing, and
an unreadable timestamp yields no finding rather than a guess.
"""
from typing import Optional

HOUR_MS = 3600 * 1000


def _age_hours(node: dict, now_ms: int) -> Optional[float]:
    """Age of a node's capture timestamp in hours, or None if unreadable."""
    stamp = node.get("last_modified")
    try:
        return (now_ms - int(stamp)) / HOUR_MS
    except (TypeError, ValueError):
        return None


def _aged(node: dict, now_ms: int) -> Optional[dict]:
    """Node annotated with its age, or None when the timestamp is unreadable."""
    age = _age_hours(node, now_ms)
    if age is None:
        return None
    return {
        "name": node.get("name", "unknown"),
        "last_modified": node["last_modified"],
        "age_hours": age,
    }


def is_past_sla(node: dict, sla_hours: int, now_ms: int) -> bool:
    """Whether a node's capture timestamp is older than its SLA.

    Callers gate on this before reading upstream freshness, so a run that has
    no stale output spends no extra graph calls and emits identical reports.
    """
    age = _age_hours(node, now_ms)
    return age is not None and age > sla_hours


def detect_edge_break(
    failing: dict,
    upstreams: list[dict],
    sla_hours: int,
    now_ms: int,
) -> Optional[dict]:
    """Return an edge-break finding when a stale output has only fresh producers.

    ``failing`` and each entry of ``upstreams`` are ``{"name", "last_modified"}``
    dicts sourced from graph reads. Returns ``None`` — meaning "run the ordinary
    root-cause walk" — unless every condition holds: the output is past SLA,
    it has at least one immediate upstream, and every one of those upstreams is
    inside SLA.
    """
    output = _aged(failing, now_ms)
    if output is None or output["age_hours"] <= sla_hours:
        return None

    if not upstreams:
        return None

    producers = [_aged(u, now_ms) for u in upstreams]
    if any(p is None for p in producers):
        return None
    if any(p["age_hours"] > sla_hours for p in producers):
        return None

    newest = min(p["age_hours"] for p in producers)
    return {
        "failing": output,
        "upstreams": sorted(producers, key=lambda p: p["age_hours"]),
        "sla_hours": sla_hours,
        "gap_hours": output["age_hours"] - newest,
    }
