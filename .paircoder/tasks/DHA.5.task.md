---
id: DHA.5
title: "Lineage-walk triage \u2192 owner-addressed incident reports"
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 5
status: done
sprint: DHA
depends_on:
- DHA.3
- DHA.4
model: claude-haiku-4-5
runtime:
  pre_task_sha:
    worktree: 3fa1c8e1e49c161ea81cd4c05966304cf8c6f462
  started_at: '2026-08-02T17:19:44.002255+00:00'
  completed_at: '2026-08-02T17:28:08.755242+00:00'
completed_at: '2026-08-02T12:26:52.357084'
ac_verified: true
---

# Lineage-walk triage → owner-addressed incident reports

When a probe fails, the agent does the work a data engineer would: walk the lineage upstream from the failing dataset to the root-cause candidate, pull owners from the context graph, and generate a complete incident report (markdown): what broke, evidence (freshness timestamps, lineage path), root-cause candidate, owner @mentions, suggested next step. LLM-composed narrative over structured facts (facts computed, never hallucinated — every claim in the report traces to a graph read; provenance list at the bottom). Reports land in an outbox/ directory; sample outputs committed for judges.

# Acceptance Criteria

- [x] Root-cause walk picks the deepest failing upstream node; tie-broken deterministically
- [x] Report includes evidence, owner(s) from the graph, provenance of every claim
- [x] Generated live against DHA.2's planted faults; samples committed to sample-outputs/
- [x] Facts computed from graph reads; LLM only phrases — asserted by a provenance test