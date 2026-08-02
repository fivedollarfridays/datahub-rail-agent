---
id: DHA.3
title: Liveness/drift probes + fail-loud classification
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 5
status: pending
sprint: null
tags: [probes, doctrine]
depends_on: [DHA.1, DHA.2]
model: claude-sonnet-5
---

# Objective

The probe engine, written fresh to the doctrine contracts (docs/capture-reliability-doctrine.md):
every probe never raises, returns pass/warn/fail with a message that names the
next action; freshness probes are capture-based (measure the data's own recency
signals via the context graph, never a job's heartbeat); unknown/unreachable
states are loud warns ("watch blind"), never silent passes. Probes: dataset
freshness vs SLA, lineage integrity (broken/missing upstream edges),
schema-contract drift (downstream expectation vs current schema). Config-driven
probe registry so judges can point it at their own estate.

# Files to Update

- `src/datahub_rail_agent/probes/base.py` — ProbeResult (pass/warn/fail + message + next action), never-raise contract
- `src/datahub_rail_agent/probes/freshness.py` — freshness vs SLA (capture-based)
- `src/datahub_rail_agent/probes/lineage.py` — lineage integrity
- `src/datahub_rail_agent/probes/schema_drift.py` — contract drift vs downstream expectation
- `src/datahub_rail_agent/probes/registry.py` — config-driven registry
- `config/probes.yaml` — probe registry config (targets, SLAs, expectations)
- `tests/test_probes_*.py` — per-probe tests incl. never-raise + blind-state assertions

# Implementation Plan

1. TDD: contract tests first — a probe whose body raises surfaces as `fail` with
   the exception in the message; MCP-down/no-data states surface as loud `warn`
   naming the cause; never a silent pass.
2. Implement `ProbeResult` and the never-raise wrapper in `base.py`.
3. Implement the three probe classes against DHA.1's reader, each returning a
   message that names the next action.
4. Config-driven registry: `config/probes.yaml` declares probe instances
   (dataset URN patterns, SLA thresholds, downstream expectations).
5. Live run against DHA.2's seeded estate — each probe catches its planted fault.

# Acceptance Criteria

- [ ] 3 probe classes implemented against DHA.1's reader; registry config-driven
- [ ] Never-raise contract enforced by tests (probe exceptions surface as fail with message)
- [ ] Blind states (MCP down, no data) → loud warn naming the cause — asserted in tests
- [ ] Each catches its planted fault from DHA.2 in a live run
- [ ] Wiring: registry loaded from `config/probes.yaml` (path overridable via
      `--config` / `RAIL_AGENT_CONFIG` env); probes instantiated only via the
      registry (single call site for the runner in DHA.4/DHA.5); missing or
      malformed config fails loud at load time with the offending key named

# Verification

- `uv run pytest tests/ -k probes` — green, incl. never-raise + blind-state tests
- Live run against seeded quickstart: 3 planted faults → 3 fails, controls pass
- Stop MCP server, run probes → loud warns, exit code still 0 (never-raise)
- `uv run ruff check .` clean; `bpsai-pair arch check src/` — no violations
