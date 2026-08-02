---
id: DHA.1
title: MCP client + typed context-graph reader
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 4
status: done
sprint: DHA
depends_on:
- DHA.0
model: claude-haiku-4-5
runtime:
  pre_task_sha:
    worktree: 16716f17a3dc02d81f122b33eca56cb062256203
  started_at: '2026-08-02T16:58:11.464976+00:00'
  completed_at: '2026-08-02T17:03:24.087507+00:00'
completed_at: '2026-08-02T12:03:11.364376'
ac_verified: true
---

# MCP client + typed context-graph reader

Python package scaffold (uv, pytest, ruff) + an MCP client wrapper around the DataHub MCP Server exposing typed reads the rest of the agent consumes: list datasets (with platform/owner), get dataset freshness/last-updated, walk upstream/downstream lineage, fetch schema + description. Fixture-based tests against recorded MCP responses (no live DataHub needed in CI). Include one GitHub Actions workflow (lint + tests) so the public repo shows green checks to judges.

# Acceptance Criteria

- [x] Typed reader API: datasets, freshness, lineage walk (up/down N hops), schema fetch
- [x] Recorded-fixture tests; CI green without a live DataHub
- [x] Live smoke script proving the same calls against the quickstart instance
- [x] ruff clean; files under the 400-line ceiling