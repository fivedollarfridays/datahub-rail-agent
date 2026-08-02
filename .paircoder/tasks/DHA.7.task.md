---
id: DHA.7
title: README, demo script, description, video assets
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 3
status: pending
sprint: null
tags: [submission, docs]
depends_on: [DHA.5, DHA.6]
model: claude-sonnet-5
---

# Objective

Submission-quality pass (an equally-weighted judging criterion): full README
(setup from zero → seeded faults → agent run → outbox artifacts, with
screenshots), the Devpost text description, and a tight <3-minute demo video
SCRIPT walking: seed the broken estate → probes catch all 3 faults → delta
digest (day-2 run shows "still failing") → incident report + fix artifact tour.
Kevin records the video (operator task noted, not automated); script includes
shot list + timings.

# Files to Update

- `README.md` — full zero-to-demo path, screenshots, disclosure section
- `docs/devpost-description.md` — Devpost text (features, stack, DataHub surfaces used)
- `docs/demo-video-script.md` — <3 min script with shot list + timings
- `sample-outputs/` — verify complete (digest, incident reports, fix artifacts)

# Implementation Plan

1. Verify the zero-to-demo path on a clean clone: quickstart → seed → run agent →
   inspect outbox; fix any README gaps found.
2. Capture/refresh screenshots (DataHub UI faults, digest output, outbox artifacts).
3. Draft the Devpost description mapped to the six judging criteria.
4. Write the video script: shot list, timings, narration beats covering seed →
   3 faults caught → day-2 delta digest → incident report + fix artifact tour.
5. Disclosure section: doctrine inspiration + all code new during the submission
   period (Apache-2.0, hackathon rule compliance).

# Acceptance Criteria

- [ ] README: zero-to-demo path verified on a clean clone
- [ ] Devpost description drafted (features, stack, DataHub surfaces used)
- [ ] Video script <3 min with shot list; sample-outputs/ complete
- [ ] Disclosure section: doctrine inspiration + all code new during submission period

# Verification

- Fresh-clone walkthrough of the README completes without undocumented steps
- sample-outputs/ contains digest + incident reports + fix artifacts from a live run
- Video script timings sum to <3:00

# Operator Notes

- Kevin records the video from the script (not automated). Devpost registration
  (DHA.0 leftover) must be done before submission.
