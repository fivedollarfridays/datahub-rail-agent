---
id: DHA.5
title: Lineage-walk triage → owner-addressed incident reports
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 5
status: pending
sprint: null
tags: [triage, remediation, llm]
depends_on: [DHA.3, DHA.4]
model: claude-sonnet-5
---

# Objective

When a probe fails, the agent does the work a data engineer would: walk the
lineage upstream from the failing dataset to the root-cause candidate, pull
owners from the context graph, and generate a complete incident report
(markdown): what broke, evidence (freshness timestamps, lineage path), root-cause
candidate, owner @mentions, suggested next step. LLM-composed narrative over
structured facts — facts computed, never hallucinated; every claim in the report
traces to a graph read; provenance list at the bottom. Reports land in an
outbox/ directory; sample outputs committed for judges.

# Files to Update

- `src/datahub_rail_agent/triage/rootcause.py` — upstream walk, deepest-failing-node selection, deterministic tie-break
- `src/datahub_rail_agent/triage/facts.py` — structured fact bundle w/ provenance (every fact carries its graph-read source)
- `src/datahub_rail_agent/triage/report.py` — report assembly; LLM phrases the narrative over the fact bundle only
- `src/datahub_rail_agent/llm.py` — Anthropic client wrapper (narrative composition only)
- `tests/test_rootcause.py`, `tests/test_report_provenance.py`
- `sample-outputs/` — committed reports from a live run against the seeded estate

# Implementation Plan

1. TDD: root-cause walk tests first on fixture lineage graphs — picks the deepest
   failing upstream node; ties broken deterministically (documented rule, e.g.
   lexicographic URN); cycles/missing nodes handled.
2. Fact bundle: every fact (timestamps, path, owners) carries provenance — which
   reader call produced it. No free facts.
3. Report assembly: template renders structured facts; LLM composes narrative
   sections from the fact bundle only; provenance list appended.
4. Provenance test: every claim-bearing line in a generated report traces to a
   fact in the bundle (assert narrative introduces no new URNs/numbers/names).
5. Outbox writer; live run against planted faults; commit samples to sample-outputs/.

# Acceptance Criteria

- [ ] Root-cause walk picks the deepest failing upstream node; tie-broken deterministically
- [ ] Report includes evidence, owner(s) from the graph, provenance of every claim
- [ ] Generated live against DHA.2's planted faults; samples committed to sample-outputs/
- [ ] Facts computed from graph reads; LLM only phrases — asserted by a provenance test
- [ ] Wiring: triage triggered by the run pipeline for each `fail` result
      (call site: the DHA.4 runner); LLM key via `ANTHROPIC_API_KEY` env — absent
      key degrades to template-only report (loud note in output, run still
      succeeds); outbox dir configurable (`outbox/` default); LLM/API errors
      never lose the report — template fallback with the error named

# Verification

- `uv run pytest tests/ -k "rootcause or provenance"` — green
- Live run against seeded estate → incident reports in outbox/ for all planted faults
- Reports show owner @mentions and provenance lists; samples committed
- `bpsai-pair arch check src/` — no violations
