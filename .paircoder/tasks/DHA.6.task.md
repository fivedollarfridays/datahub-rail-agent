---
id: DHA.6
title: Contract-drift fix artifacts (PR-ready)
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P1
complexity: 4
status: pending
sprint: null
tags: [remediation, artifacts]
depends_on: [DHA.5]
model: claude-sonnet-5
---

# Objective

For the schema-drift fault class: generate a PR-ready fix artifact — the updated
downstream expectation (e.g. corrected column mapping / dbt-style schema patch)
plus a diff-formatted change file and a commit-message-ready summary, written to
the outbox next to the incident report. Judges' "Sample Outputs" recommendation
is satisfied by committing these artifacts from a live run.

# Files to Update

- `src/datahub_rail_agent/remediation/drift_fix.py` — patch generation (corrected expectation, diff, commit summary)
- `tests/test_drift_fix.py` — artifact correctness incl. clean-apply test
- `sample-outputs/` — committed fix artifacts from a live run

# Implementation Plan

1. TDD: given the seeded downstream expectation and the drifted current schema,
   the generated patch produces exactly the corrected expectation — write the
   clean-apply test first.
2. Generate three artifacts per drift finding: updated expectation file, unified
   diff, commit-message-ready summary.
3. Write to outbox/ alongside the DHA.5 incident report for the same finding.
4. Live run against the seeded drift fault; commit samples.

# Acceptance Criteria

- [ ] Drift fault → concrete patch artifact + diff + summary in outbox/
- [ ] Artifact applies cleanly to the seeded downstream config (verified in test)
- [ ] Samples committed to sample-outputs/
- [ ] Wiring: invoked by the triage pipeline when the failing probe is the
      schema-drift class (call site: DHA.5 report flow); no new config — inherits
      outbox setting; ungeneratable patch (unrecognized drift shape) → incident
      report still produced, artifact skipped with a loud note naming why

# Verification

- `uv run pytest tests/test_drift_fix.py` — green, incl. clean-apply assertion
- Live run → patch + diff + summary in outbox/ next to the incident report
- `bpsai-pair arch check src/` — no violations
