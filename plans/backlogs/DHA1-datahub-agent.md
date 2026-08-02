# Backlog: DHA1 — DataHub Agent Hackathon entry ("Agents That Do Real Work")

Plan type: feature. TARGET REPO: NEW public `fivedollarfridays/datahub-rail-agent`
(Apache 2.0 — license required by rules; hackathon rule: code newly created during the
submission period, doctrine/patterns disclosed as prior inspiration in the README).
Deadline: **Aug 10, 2026 5:00 pm EDT** (Devpost, Build with DataHub: The Agent Hackathon).

The entry: a **data-rail health monitor agent** applying the capture-reliability doctrine we
battle-tested in ops (docs/capture-reliability-doctrine.md + the SMR sprints) to DataHub's
context graph — capture-based liveness over dataset freshness/lineage (never bare
heartbeats), fail-loud classification, **delta-aware alerting** (NEW vs still-failing-day-N
vs recovered — the alarm-fatigue killer), and real remediation: lineage-walk root-cause
triage producing owner-addressed incident reports, and schema/contract-drift detection
producing PR-ready fix artifacts. DataHub integration via the **MCP Server** (judging
criterion #1). Judging is six equal criteria: DataHub use, technical execution, originality,
real-world usefulness, submission quality, upstream-contribution bonus — each has a task or
AC below. TDD; keep files under a 400-line ceiling; every probe follows never-raise +
message-carries-next-action contracts.

## Phase 0: Operator gates (Kevin, do first)

### DHA.0 — Repo + DataHub quickstart + MCP server running | Cx: 2 | P0

**STATUS: DONE 2026-08-02** (environment live and verified: repo public w/ Apache-2.0, quickstart healthy at :9002/:8080, sample data ingested, MCP smoke passed — see docs/mcp-smoke.md + docs/environment.md). Devpost registration is the one remaining operator item and does NOT block any code task.

**Description:** OPERATOR TASK. Create public repo `datahub-rail-agent` (Apache 2.0 LICENSE,
README stub disclosing doctrine inspiration + hackathon entry note). Get DataHub quickstart
running locally (docker compose, per docs.datahub.com quickstart) and the DataHub MCP Server
reachable from a test client. Register for the hackathon on Devpost. Everything downstream
is blocked on this environment existing.

**AC:**
- [x] Public repo exists with Apache-2.0 LICENSE visible + README stub
- [x] DataHub quickstart up locally; UI reachable; sample ingestion works
- [x] MCP Server endpoint responds to a hello/list call from a scratch client
- [ ] Devpost registration done (team of 1)

**Depends on:** none

**Model:** claude-haiku-4-5

## Phase 1: Context-graph client

### DHA.1 — MCP client + typed context-graph reader | Cx: 4 | P0

**Description:** Python package scaffold (uv, pytest, ruff) + an MCP client wrapper around
the DataHub MCP Server exposing typed reads the rest of the agent consumes: list datasets
(with platform/owner), get dataset freshness/last-updated, walk upstream/downstream lineage,
fetch schema + description. Fixture-based tests against recorded MCP responses (no live
DataHub needed in CI). Include one GitHub Actions workflow (lint + tests) so the public repo
shows green checks to judges.

**AC:**
- [ ] Typed reader API: datasets, freshness, lineage walk (up/down N hops), schema fetch
- [ ] Recorded-fixture tests; CI green without a live DataHub
- [ ] Live smoke script proving the same calls against the quickstart instance
- [ ] ruff clean; files under the 400-line ceiling

**Depends on:** DHA.0

**Model:** claude-haiku-4-5

### DHA.2 — Demo dataset seeder (the "broken data estate") | Cx: 3 | P0

**Description:** A seed script that ingests a small synthetic data estate into the quickstart
instance with deliberately planted faults the agent will catch on camera: one stale dataset
(freshness beyond SLA), one broken lineage edge (upstream deleted/renamed), one
schema-contract drift (column type change downstream still expects), and healthy controls.
Deterministic (fixed names/timestamps) so the demo video and sample outputs are reproducible
by judges following the README.

**AC:**
- [ ] One-command seed against quickstart; idempotent re-runs
- [ ] Plants exactly the 3 fault classes + healthy controls; documented in README
- [ ] Faults visible in DataHub UI (screenshot-able for the video)

**Depends on:** DHA.0

**Model:** claude-haiku-4-5

## Phase 2: Probe engine (the doctrine port)

### DHA.3 — Liveness/drift probes + fail-loud classification | Cx: 5 | P0

**Description:** The probe engine, written fresh to the doctrine contracts: every probe
never raises, returns pass/warn/fail with a message that names the next action; freshness
probes are capture-based (measure the data's own recency signals via the context graph,
never a job's heartbeat); unknown/unreachable states are loud warns ("watch blind"), never
silent passes. Probes: dataset freshness vs SLA, lineage integrity (broken/missing upstream
edges), schema-contract drift (downstream expectation vs current schema). Config-driven
probe registry so judges can point it at their own estate.

**AC:**
- [ ] 3 probe classes implemented against DHA.1's reader; registry config-driven
- [ ] Never-raise contract enforced by tests (probe exceptions surface as fail with message)
- [ ] Blind states (MCP down, no data) → loud warn naming the cause — asserted in tests
- [ ] Each catches its planted fault from DHA.2 in a live run

**Depends on:** DHA.1, DHA.2

**Model:** claude-haiku-4-5

### DHA.4 — Delta-aware state history (NEW / day-N / recovered) | Cx: 4 | P0

**Description:** The alarm-fatigue killer: persist per-probe status history (JSONL) and
render deltas — NEW failures first, chronic ones collapsed to "still failing (day N)",
one-line "recovered" on the flip to green. First run with no history degrades gracefully.
This is the feature that distinguishes the entry from every threshold-alert tool in the
category (originality criterion) — the README gets a short "why delta-aware" section citing
the alarm-fatigue problem.

**AC:**
- [ ] History appended per run; bounded rotation
- [ ] Digest renders NEW vs still-failing-day-N vs recovered; empty-history graceful
- [ ] Tests cover new/chronic/recovered/empty paths
- [ ] README section: the alarm-fatigue rationale (2 paragraphs, cites the doctrine)

**Depends on:** DHA.3

**Model:** claude-haiku-4-5

## Phase 3: Real work (remediation)

### DHA.5 — Lineage-walk triage → owner-addressed incident reports | Cx: 5 | P0

**Description:** When a probe fails, the agent does the work a data engineer would: walk the
lineage upstream from the failing dataset to the root-cause candidate, pull owners from the
context graph, and generate a complete incident report (markdown): what broke, evidence
(freshness timestamps, lineage path), root-cause candidate, owner @mentions, suggested next
step. LLM-composed narrative over structured facts (facts computed, never hallucinated —
every claim in the report traces to a graph read; provenance list at the bottom). Reports
land in an outbox/ directory; sample outputs committed for judges.

**AC:**
- [ ] Root-cause walk picks the deepest failing upstream node; tie-broken deterministically
- [ ] Report includes evidence, owner(s) from the graph, provenance of every claim
- [ ] Generated live against DHA.2's planted faults; samples committed to sample-outputs/
- [ ] Facts computed from graph reads; LLM only phrases — asserted by a provenance test

**Depends on:** DHA.3, DHA.4

**Model:** claude-haiku-4-5

### DHA.6 — Contract-drift fix artifacts (PR-ready) | Cx: 4 | P1

**Description:** For the schema-drift fault class: generate a PR-ready fix artifact — the
updated downstream expectation (e.g. corrected column mapping / dbt-style schema patch) plus
a diff-formatted change file and a commit-message-ready summary, written to the outbox next
to the incident report. Judges' "Sample Outputs" recommendation is satisfied by committing
these artifacts from a live run.

**AC:**
- [ ] Drift fault → concrete patch artifact + diff + summary in outbox/
- [ ] Artifact applies cleanly to the seeded downstream config (verified in test)
- [ ] Samples committed to sample-outputs/

**Depends on:** DHA.5

**Model:** claude-haiku-4-5

## Phase 4: Submission assets + bonus

### DHA.7 — README, demo script, description, video assets | Cx: 3 | P0

**Description:** Submission-quality pass (an equally-weighted judging criterion): full
README (setup from zero → seeded faults → agent run → outbox artifacts, with screenshots),
the Devpost text description, and a tight <3-minute demo video SCRIPT walking: seed the
broken estate → probes catch all 3 faults → delta digest (day-2 run shows "still failing")
→ incident report + fix artifact tour. Kevin records the video (operator task noted, not
automated); script includes shot list + timings.

**AC:**
- [ ] README: zero-to-demo path verified on a clean clone
- [ ] Devpost description drafted (features, stack, DataHub surfaces used)
- [ ] Video script <3 min with shot list; sample-outputs/ complete
- [ ] Disclosure section: doctrine inspiration + all code new during submission period

**Depends on:** DHA.5, DHA.6

**Model:** claude-haiku-4-5

### DHA.8 — Upstream bonus: DataHub docs/skill contribution | Cx: 2 | P2

**Description:** The bonus judging criterion: one small, genuinely useful upstream
contribution — a docs PR or example (e.g. an MCP-client usage example or a
delta-aware-alerting pattern writeup) to the DataHub project, linked from the Devpost
submission. Scope strictly small; a merged-or-open PR link is the deliverable.

**AC:**
- [ ] One upstream PR opened against a DataHub repo (docs/example scope)
- [ ] Linked in README + Devpost description

**Depends on:** DHA.5

**Model:** claude-haiku-4-5

## Delivery Summary

| Task | Title | Cx | Priority | Model |
| --- | --- | --- | --- | --- |
| DHA.0 | Repo + quickstart + MCP running (operator) | 2 | P0 | claude-haiku-4-5 |
| DHA.1 | MCP client + typed context-graph reader | 4 | P0 | claude-haiku-4-5 |
| DHA.2 | Demo dataset seeder (broken estate) | 3 | P0 | claude-haiku-4-5 |
| DHA.3 | Probes + fail-loud classification | 5 | P0 | claude-haiku-4-5 |
| DHA.4 | Delta-aware state history | 4 | P0 | claude-haiku-4-5 |
| DHA.5 | Lineage triage → incident reports | 5 | P0 | claude-haiku-4-5 |
| DHA.6 | Contract-drift fix artifacts | 4 | P1 | claude-haiku-4-5 |
| DHA.7 | README + demo script + description | 3 | P0 | claude-haiku-4-5 |
| DHA.8 | Upstream bonus contribution | 2 | P2 | claude-haiku-4-5 |

Total Cx: 32 (agent tasks: 30; operator gate: 2)

## Priority Order

1. DHA.0 — operator gate; everything blocks on the environment (Kevin, ~1 evening)
2. DHA.1 + DHA.2 — parallel once DHA.0 lands (disjoint: client vs seeder)
3. DHA.3 → DHA.4 — the doctrine core, sequential (same engine files)
4. DHA.5 → DHA.6 — the "real work" differentiator
5. DHA.7 — submission polish (P0 — submission quality is a full judging criterion)
6. DHA.8 — bonus, only after the entry itself is solid
