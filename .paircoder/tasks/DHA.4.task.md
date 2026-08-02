---
id: DHA.4
title: Delta-aware state history (NEW / day-N / recovered)
plan: plan-2026-08-dha1-datahub-agent
type: feature
priority: P0
complexity: 4
status: done
sprint: DHA
depends_on:
- DHA.3
model: claude-haiku-4-5
runtime:
  pre_task_sha:
    worktree: 43aa025fd97c211585b9b808ff195052acabd8f9
  started_at: '2026-08-02T17:15:41.807907+00:00'
  completed_at: '2026-08-02T17:19:37.050117+00:00'
completed_at: '2026-08-02T12:18:48.047697'
ac_verified: true
---

# Delta-aware state history (NEW / day-N / recovered)

The alarm-fatigue killer: persist per-probe status history (JSONL) and render deltas — NEW failures first, chronic ones collapsed to "still failing (day N)", one-line "recovered" on the flip to green. First run with no history degrades gracefully. This is the feature that distinguishes the entry from every threshold-alert tool in the category (originality criterion) — the README gets a short "why delta-aware" section citing the alarm-fatigue problem.

# Acceptance Criteria

- [x] History appended per run; bounded rotation — StateHistory.append() with load/rewrite rotation, max_entries limit enforced (tests: test_state_history_core.py 5/5)
- [x] Digest renders NEW vs still-failing-day-N vs recovered; empty-history graceful — StateDigest.render() classifies transitions, empty history → "" (tests: test_state_history_digest.py 5/5)
- [x] Tests cover new/chronic/recovered/empty paths — 13 tests: 5 core persistence + 5 digest rendering + 3 integration
- [x] README section: the alarm-fatigue rationale (2 paragraphs, cites the doctrine) — Added "Delta-Aware State History" section citing capture-reliability doctrine