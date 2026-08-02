---
id: DHA.8
title: 'Upstream bonus: DataHub docs/skill contribution'
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P2
complexity: 2
status: pending
sprint: null
tags: [upstream, bonus]
depends_on: [DHA.5]
model: claude-sonnet-5
---

# Objective

The bonus judging criterion: one small, genuinely useful upstream contribution —
a docs PR or example (e.g. an MCP-client usage example or a delta-aware-alerting
pattern writeup) to the DataHub project, linked from the Devpost submission.
Scope strictly small; a merged-or-open PR link is the deliverable.

# Files to Update

- Upstream: one docs/example PR against a DataHub repo (fork + branch)
- `README.md` — link to the upstream PR
- `docs/devpost-description.md` — link to the upstream PR

# Implementation Plan

1. Pick the contribution from what DHA.1–DHA.5 actually surfaced (best candidates:
   MCP-client usage example, or a delta-aware-alerting pattern writeup) — choose
   whichever fills a real gap in DataHub's docs.
2. Check DataHub's CONTRIBUTING.md; keep scope to docs/example only.
3. Open the PR from a fork; confirm CI/lint passes on the upstream repo.
4. Link the PR in README + Devpost description.

# Acceptance Criteria

- [ ] One upstream PR opened against a DataHub repo (docs/example scope)
- [ ] Linked in README + Devpost description

# Verification

- PR URL is live (open or merged) and referenced from both README and Devpost text

# Operator Notes

- Opening the PR from Kevin's GitHub account is an operator confirmation point —
  agent prepares the branch/content; Kevin approves the outward-facing PR.
