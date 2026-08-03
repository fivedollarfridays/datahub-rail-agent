"""Delta-aware verdict derivation, read-only over the state history.

The digest already renders NEW / CHRONIC day N / RECOVERED per (dataset,
probe). Write-back needs the same judgement rolled up to one verdict per
dataset, so it recomputes from the same JSONL entries rather than changing
how history is written or rendered.
"""
from dataclasses import dataclass, field


@dataclass
class Verdict:
    """One dataset's rolled-up health verdict for a run."""

    status_class: str
    label: str
    probes: list[str] = field(default_factory=list)


def _probe_state(sequence: list[dict]) -> tuple[str, int]:
    """Classify one probe's history tail. Returns (class, consecutive fails)."""
    latest = sequence[-1]["status"]
    if latest != "fail":
        if len(sequence) > 1 and sequence[-2]["status"] == "fail":
            return "RECOVERED", 0
        return "PASS", 0

    fails = 0
    for entry in reversed(sequence):
        if entry["status"] != "fail":
            break
        fails += 1
    return ("NEW-FAIL", fails) if fails == 1 else ("CHRONIC", fails)


def verdict_for_dataset(entries: list[dict], dataset_urn: str) -> Verdict | None:
    """Roll a dataset's probe histories into a single delta-aware verdict."""
    by_probe: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.get("dataset_urn") == dataset_urn:
            by_probe.setdefault(entry["probe_name"], []).append(entry)

    if not by_probe:
        return None

    states = {probe: _probe_state(seq) for probe, seq in by_probe.items()}
    return _rollup(states)


def _rollup(states: dict[str, tuple[str, int]]) -> Verdict:
    """Pick the most severe probe state; failures name only the failing probes."""
    for status_class in ("CHRONIC", "NEW-FAIL", "RECOVERED"):
        probes = sorted(p for p, (cls, _) in states.items() if cls == status_class)
        if not probes:
            continue
        if status_class == "CHRONIC":
            days = max(n for _, (cls, n) in states.items() if cls == "CHRONIC")
            return Verdict(status_class, f"CHRONIC-day-{days}", probes)
        return Verdict(status_class, status_class, probes)

    return Verdict("PASS", "PASS", sorted(states))
