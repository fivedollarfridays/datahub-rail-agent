---
id: DHA.2
title: Demo dataset seeder (the broken data estate)
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 3
status: pending
sprint: null
tags: [seeder, demo]
depends_on: [DHA.0]
model: claude-sonnet-5
---

# Objective

A seed script that ingests a small synthetic data estate into the quickstart
instance with deliberately planted faults the agent will catch on camera: one
stale dataset (freshness beyond SLA), one broken lineage edge (upstream
deleted/renamed), one schema-contract drift (column type change downstream still
expects), and healthy controls. Deterministic (fixed names/timestamps) so the
demo video and sample outputs are reproducible by judges following the README.

# Files to Update

- `scripts/seed_estate.py` — one-command seeder entry point
- `src/datahub_rail_agent/seeding/estate.py` — estate definition (datasets, lineage, schemas, faults)
- `tests/test_estate.py` — estate definition invariants (determinism, fault classes present)
- `README.md` — planted-faults section

# Implementation Plan

1. TDD: tests first for the estate definition — exactly 3 fault classes planted,
   fixed names/timestamps (no wall-clock nondeterminism in dataset identity),
   healthy controls present.
2. Define the synthetic estate as data (names, platforms, owners, lineage edges,
   schemas, timestamps) separate from the ingestion I/O.
3. Implement seeding via DataHub ingestion (emitter/REST against quickstart);
   idempotent re-runs (stable URNs, upserts).
4. Verify faults visible in DataHub UI; capture screenshots for DHA.7.
5. Document the estate + faults in README.

# Acceptance Criteria

- [ ] One-command seed against quickstart; idempotent re-runs
- [ ] Plants exactly the 3 fault classes + healthy controls; documented in README
- [ ] Faults visible in DataHub UI (screenshot-able for the video)
- [ ] Wiring: invoked as `uv run python scripts/seed_estate.py`; target instance
      configured via env (`DATAHUB_GMS_URL`, documented default matching
      docs/environment.md); unreachable instance or rejected ingestion exits
      non-zero with a message naming the failing endpoint and next action

# Verification

- `uv run pytest tests/test_estate.py` — green
- Run seeder twice against quickstart; second run is a no-op/upsert (idempotent)
- Confirm stale dataset, broken lineage edge, and schema drift visible in the UI
- `bpsai-pair arch check src/` — no violations
