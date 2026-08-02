---
id: DHA.4
title: Delta-aware state history (NEW / day-N / recovered)
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 4
status: pending
sprint: null
tags: [history, delta, originality]
depends_on: [DHA.3]
model: claude-sonnet-5
---

# Objective

The alarm-fatigue killer: persist per-probe status history (JSONL) and render
deltas — NEW failures first, chronic ones collapsed to "still failing (day N)",
one-line "recovered" on the flip to green. First run with no history degrades
gracefully. This distinguishes the entry from every threshold-alert tool in the
category (originality criterion) — the README gets a short "why delta-aware"
section citing the alarm-fatigue problem.

# Files to Update

- `src/datahub_rail_agent/history/store.py` — JSONL append + bounded rotation
- `src/datahub_rail_agent/history/delta.py` — NEW / still-failing-day-N / recovered classification
- `src/datahub_rail_agent/digest.py` — digest renderer (NEW first, chronic collapsed, recovered one-liners)
- `tests/test_history.py`, `tests/test_delta.py`, `tests/test_digest.py`
- `README.md` — "why delta-aware" section (2 paragraphs, cites the doctrine)

# Implementation Plan

1. TDD: delta classification tests first — new, chronic (day-N counting),
   recovered, and empty-history paths.
2. JSONL store: one record per probe per run; bounded rotation (config cap on
   retained runs).
3. Delta engine: compare current run against history; compute day-N from first
   consecutive failure.
4. Digest renderer: NEW failures first, chronic collapsed, recovered one-line;
   graceful on empty history (all findings rendered as first-seen).
5. README rationale section.

# Acceptance Criteria

- [ ] History appended per run; bounded rotation
- [ ] Digest renders NEW vs still-failing-day-N vs recovered; empty-history graceful
- [ ] Tests cover new/chronic/recovered/empty paths
- [ ] README section: the alarm-fatigue rationale (2 paragraphs, cites the doctrine)
- [ ] Wiring: history store invoked by the probe run pipeline after every run
      (call site: the runner that executes the DHA.3 registry); history path +
      rotation bound configured in `config/probes.yaml` with documented defaults
      (e.g. `state/history.jsonl`, keep 90 runs); corrupt/unreadable history line
      → loud warn naming the file+line, run continues (never blocks a probe run)

# Verification

- `uv run pytest tests/ -k "history or delta or digest"` — green
- Live: run twice against seeded estate → second digest shows "still failing (day 2)";
  fix a fault, run again → "recovered" line
- Delete history file, run → graceful first-run digest
- `bpsai-pair arch check src/` — no violations
