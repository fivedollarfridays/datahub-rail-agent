---
id: DHA.3
title: Liveness/drift probes + fail-loud classification
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 5
status: done
sprint: DHA
depends_on:
- DHA.1
- DHA.2
model: claude-haiku-4-5
runtime:
  pre_task_sha:
    worktree: aa1b6766f5f09ea382fc14a4414a4578aa6ecffc
  started_at: '2026-08-02T17:10:47.568904+00:00'
  completed_at: '2026-08-02T17:15:34.779868+00:00'
completed_at: '2026-08-02T12:14:47.156817'
ac_verified: true
---

# Liveness/drift probes + fail-loud classification

The probe engine, written fresh to the doctrine contracts: every probe never raises, returns pass/warn/fail with a message that names the next action; freshness probes are capture-based (measure the data's own recency signals via the context graph, never a job's heartbeat); unknown/unreachable states are loud warns ("watch blind"), never silent passes. Probes: dataset freshness vs SLA, lineage integrity (broken/missing upstream edges), schema-contract drift (downstream expectation vs current schema). Config-driven probe registry so judges can point it at their own estate.

# Acceptance Criteria

- [x] 3 probe classes implemented against DHA.1's reader; registry config-driven
  - FreshnessProbe, LineageProbe, SchemaProbe in src/datahub_rail/probes.py
  - ProbeRegistry loads config-driven probes from YAML (config/probes.yaml)
  - Tests: test_probe_registry_loads_config, test_probe_registry_creates_correct_probe_types
  
- [x] Never-raise contract enforced by tests (probe exceptions surface as fail with message)
  - All probes catch exceptions and return ProbeResult(status="fail", message=...)
  - Tests: test_freshness_probe_never_raises_on_client_error, test_lineage_probe_never_raises_on_client_error, test_schema_probe_never_raises_on_client_error
  
- [x] Blind states (MCP down, no data) → loud warn naming the cause — asserted in tests
  - LineageProbe detects empty upstream → fail with "missing lineage" message
  - Tests: test_lineage_probe_warns_on_missing_upstream, test_lineage_probe_detects_watch_blind_state
  
- [x] Each catches its planted fault from DHA.2 in a live run
  - FreshnessProbe catches stale (45 days) → test_probe_catches_stale_freshness_fault
  - LineageProbe catches broken edge (deleted upstream) → test_probe_catches_broken_lineage_fault
  - SchemaProbe catches drift (int vs decimal) → test_probe_catches_schema_drift_fault
  - All 22 probe tests pass + 4 e2e tests detecting DHA.2 faults