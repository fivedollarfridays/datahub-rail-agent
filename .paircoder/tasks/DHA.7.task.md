---
id: DHA.7
title: README, demo script, description, video assets
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 3
status: done
sprint: DHA
depends_on:
- DHA.5
- DHA.6
model: claude-haiku-4-5
runtime:
  pre_task_sha:
    worktree: d9aa3a560f6977958d9e6901b7bef4d2efe5d862
  started_at: '2026-08-02T17:36:06.187887+00:00'
  completed_at: '2026-08-02T17:40:28.435301+00:00'
completed_at: '2026-08-02T12:39:32.443679'
ac_verified: true
---

# README, demo script, description, video assets

Submission-quality pass (an equally-weighted judging criterion): full README (setup from zero → seeded faults → agent run → outbox artifacts, with screenshots), the Devpost text description, and a tight <3-minute demo video SCRIPT walking: seed the broken estate → probes catch all 3 faults → delta digest (day-2 run shows "still failing") → incident report + fix artifact tour. Kevin records the video (operator task noted, not automated); script includes shot list + timings.

# Acceptance Criteria

- [x] README: zero-to-demo path verified on a clean clone
  - ✓ Quick Start section added with 8 detailed steps (clone → install → start DataHub → start MCP → seed → run probes → check reports → verify artifacts)
  - ✓ All referenced paths verified to exist (config/probes.yaml, scripts/seed_demo_estate.py, sample-outputs/, pyproject.toml)
  - ✓ Prerequisites listed clearly (Python 3.11+, Docker, MCP Server)
  - ✓ Expected output shown for each step
  - ✓ Verification section with UI checks and output verification

- [x] Devpost description drafted (features, stack, DataHub surfaces used)
  - ✓ File: docs/DEVPOST_DESCRIPTION.md (108 lines)
  - ✓ Sections: Inspiration, What It Does, Tech Stack, DataHub Surfaces, Demo, Key Innovation, Code Quality
  - ✓ Features described: 3 probe classes (freshness, lineage, schema), delta-aware state history, lineage triage, fix artifacts
  - ✓ Stack documented: Python 3.11+, DataHub MCP Server, Pydantic, pytest, GitHub Actions
  - ✓ DataHub surfaces: Context graph reads (list_datasets, get_freshness, fetch_schema, walk_upstream), metadata ingestion, lineage navigation, owner info

- [x] Video script <3 min with shot list; sample-outputs/ complete
  - ✓ File: docs/DEMO_VIDEO_SCRIPT.md (363 lines)
  - ✓ Timing: 170 seconds total (20+20+35+40+35+20 = 170s, under 3-min target of 180s)
  - ✓ 6 scenes with detailed shot lists: Problem (20s) → Setup (20s) → Day 1 (35s) → Day 2 (40s) → Artifacts (35s) → Closing (20s)
  - ✓ Scene 3: Day 1 run demonstrates all 3 probes catching seeded faults
  - ✓ Scene 4: Day 2 run shows delta-aware state history with CHRONIC classification
  - ✓ Scene 5: Fix artifacts tour (patch, diff, commit message)
  - ✓ Production notes included (screen res, font, pacing, captions)
  - ✓ sample-outputs/: 6 files present (3 incident reports, 2 schema artifacts, 1 commit message)

- [x] Disclosure section: doctrine inspiration + all code new during submission period
  - ✓ Section added to README: "Doctrine & Inspiration"
  - ✓ 5 architectural patterns documented:
    1. Capture-based liveness (measure via lastModified, not heartbeats)
    2. Fail-loud on outage (never-raise contracts)
    3. Delta-aware alerting (NEW/CHRONIC/RECOVERED)
    4. Lineage-walk root-cause triage (deepest failing node)
    5. Provenance guarantee (graph reads only)
  - ✓ Clear statement: "All code in this repository is newly written during the Build with DataHub: The Agent Hackathon submission period"