---
id: DHA.1
title: MCP client + typed context-graph reader
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 4
status: pending
sprint: null
tags: [mcp, client, scaffold]
depends_on: [DHA.0]
model: claude-sonnet-5
---

# Objective

Python package scaffold (uv, pytest, ruff) plus an MCP client wrapper around the
DataHub MCP Server exposing typed reads the rest of the agent consumes: list
datasets (with platform/owner), get dataset freshness/last-updated, walk
upstream/downstream lineage, fetch schema + description. Fixture-based tests
against recorded MCP responses so CI needs no live DataHub. One GitHub Actions
workflow (lint + tests) so the public repo shows green checks to judges.

# Files to Update

- `pyproject.toml` — uv-managed package, pytest + ruff dev deps
- `src/datahub_rail_agent/mcp_client.py` — thin MCP transport wrapper
- `src/datahub_rail_agent/reader.py` — typed context-graph reader API
- `src/datahub_rail_agent/models.py` — dataclasses: Dataset, Freshness, LineageEdge, SchemaField
- `tests/fixtures/` — recorded MCP responses (JSON)
- `tests/test_reader.py` — fixture-based reader tests
- `scripts/live_smoke.py` — same calls against the live quickstart
- `.github/workflows/ci.yml` — lint + tests

# Implementation Plan

1. TDD: write failing tests for each reader method against recorded fixtures first.
2. Scaffold package with uv; wire pytest + ruff.
3. Implement `mcp_client.py` (transport, connection config via env
   `DATAHUB_MCP_URL`, default from docs/environment.md).
4. Implement typed reader over the client: `list_datasets()`, `get_freshness(urn)`,
   `walk_lineage(urn, direction, hops)`, `get_schema(urn)`.
5. Record real MCP responses from the live quickstart into `tests/fixtures/`.
6. Live smoke script proving the same calls against quickstart (not run in CI).
7. Add GitHub Actions workflow; verify green.

# Acceptance Criteria

- [ ] Typed reader API: datasets, freshness, lineage walk (up/down N hops), schema fetch
- [ ] Recorded-fixture tests; CI green without a live DataHub
- [ ] Live smoke script proving the same calls against the quickstart instance
- [ ] ruff clean; files under the 400-line ceiling
- [ ] Wiring: reader is the single package entry point for graph reads (constructed
      in `scripts/live_smoke.py` call site now, agent runner later); MCP endpoint
      configured via `DATAHUB_MCP_URL` env with documented default; unreachable
      server or malformed response raises a typed `McpReadError` from the client
      layer (probe layer in DHA.3 converts to loud warn — client itself fails loud)

# Verification

- `uv run pytest` — green with no live DataHub
- `uv run ruff check .` — clean
- `uv run python scripts/live_smoke.py` — all four read classes succeed against quickstart
- `bpsai-pair arch check src/` — no violations
