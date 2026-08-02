---
id: DHA.2
title: Demo dataset seeder (the "broken data estate")
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 3
status: done
sprint: DHA
depends_on:
- DHA.0
model: claude-haiku-4-5
runtime:
  pre_task_sha:
    worktree: 9856f467b79f6e42ad527a305ee08eb99a16fb70
  started_at: '2026-08-02T17:03:32.764734+00:00'
  completed_at: '2026-08-02T17:10:40.493216+00:00'
completed_at: '2026-08-02T12:10:04.753468'
ac_verified: true
---

# Demo dataset seeder (the "broken data estate")

A seed script that ingests a small synthetic data estate into the quickstart instance with deliberately planted faults the agent will catch on camera: one stale dataset (freshness beyond SLA), one broken lineage edge (upstream deleted/renamed), one schema-contract drift (column type change downstream still expects), and healthy controls. Deterministic (fixed names/timestamps) so the demo video and sample outputs are reproducible by judges following the README.

# Acceptance Criteria

- [x] One-command seed against quickstart; idempotent re-runs
  - `scripts/seed_demo_estate.py` one-liner; uses seeder.ingest_dataset() which upserts (idempotent)
  - verified via test_seed_demo_estate_end_to_end
- [x] Plants exactly the 3 fault classes + healthy controls; documented in README
  - Stale: orders_archive (lastModified 45 days ago)
  - Broken lineage: events → deleted raw_events_old upstream
  - Schema drift: transactions amount type int vs decimal(12,2) in warehouse
  - Healthy: users (current freshness)
  - All documented in README.md with class descriptions
- [x] Faults visible in DataHub UI (screenshot-able for the video)
  - Seeder ingests via DataHub GraphQL API; all metadata visible in UI
  - Stale: shows freshness metadata (lastModified timestamp)
  - Broken lineage: lineage graph shows missing upstream node
  - Schema drift: schema tab shows field type mismatch
  - Deterministic names/timestamps enable reproducible demo