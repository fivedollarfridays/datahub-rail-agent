---
id: DHA.0
title: Repo + DataHub quickstart + MCP server running (operator)
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 2
status: done
sprint: null
tags: [operator]
depends_on: []
model: claude-sonnet-5
---

# Objective

OPERATOR TASK (Kevin). Create public repo `fivedollarfridays/datahub-rail-agent`
(Apache 2.0 LICENSE, README stub disclosing doctrine inspiration + hackathon entry
note). Get DataHub quickstart running locally and the DataHub MCP Server reachable
from a test client. Register for the hackathon on Devpost.

**STATUS: DONE 2026-08-02** — environment live and verified: repo public with
Apache-2.0, quickstart healthy at :9002/:8080, sample data ingested, MCP smoke
passed (see docs/mcp-smoke.md + docs/environment.md). Devpost registration is the
one remaining operator item and does NOT block any code task.

# Implementation Plan

- Operator-executed; no agent work. Kept for plan completeness and dependency graph.

# Acceptance Criteria

- [x] Public repo exists with Apache-2.0 LICENSE visible + README stub
- [x] DataHub quickstart up locally; UI reachable; sample ingestion works
- [x] MCP Server endpoint responds to a hello/list call from a scratch client
- [ ] Devpost registration done (team of 1) — operator item, non-blocking

# Verification

- docs/mcp-smoke.md and docs/environment.md record the verified environment state.
