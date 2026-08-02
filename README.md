# datahub-rail-agent

A data-rail health monitor agent for DataHub's context graph. It runs capture-based liveness probes over dataset freshness and lineage, applies fail-loud classification so silent outages surface as incidents instead of green dashboards, and produces delta-aware alerts that fire on meaningful change rather than raw thresholds. When something breaks, it walks the lineage graph to triage root cause and generates owner-addressed incident reports. It also detects schema and contract drift and emits PR-ready fix artifacts. Integration with DataHub is via the DataHub MCP Server.

## Quick Start: From Zero to Demo

### Prerequisites

- Python 3.11+
- Docker (for running DataHub locally)
- A DataHub instance with the MCP Server running (see below)

### 1. Clone and Install

```bash
git clone https://github.com/<your-org>/datahub-rail-agent.git
cd datahub-rail-agent
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .
```

### 2. Start DataHub Locally

If you don't have a DataHub instance running:

```bash
# Using Docker (quickstart)
docker run -d \
  -p 8080:8080 \
  -p 9090:9090 \
  -p 5432:5432 \
  --name datahub \
  acryldata/datahub-gms:latest
```

Wait for DataHub to be ready (~30 seconds). Check health:
```bash
curl http://localhost:8080/health
```

### 3. Run the MCP Server

In a separate terminal:

```bash
# If using the DataHub MCP Server
# (Instructions assume you have mcp-server-datahub installed)
mcp-server-datahub --datahub-url http://localhost:8080
```

This exposes DataHub's context graph via MCP tools that datahub-rail-agent uses.

### 4. Seed the Demo Estate

With DataHub and MCP running, seed a synthetic broken data estate with 3 deliberate faults:

```bash
DATAHUB_GMS_URL=http://localhost:8080 \
  python scripts/seed_demo_estate.py
```

Output:
```
✓ Seeded dataset: users (healthy control)
✓ Seeded dataset: orders_archive (stale: 45 days old)
✓ Seeded dataset: events (broken lineage: upstream missing)
✓ Seeded dataset: transactions (schema drift: int instead of decimal(12,2))
```

### 5. Run Probes (First Pass)

Execute the first health check run:

```bash
python -m datahub_rail.agent \
  --config config/probes.yaml \
  --datahub-url http://localhost:8080
```

**Expected output:**
```
Dataset: users — PASS (freshness OK, lineage OK, schema OK)
Dataset: orders_archive — FAIL (Freshness: 45 days old, SLA: 24h)
Dataset: events — FAIL (Lineage: upstream dataset missing)
Dataset: transactions — FAIL (Schema: amount type is int, expected decimal(12,2))
```

All three probe failures land in `outbox/` directory.

### 6. Check Incident Reports (Day 1)

```bash
ls -la outbox/
cat outbox/incident_orders_archive_*.md
cat outbox/incident_events_*.md
cat outbox/incident_transactions_*.md
```

Each report includes:
- **What Broke:** Dataset name, owner, probe type
- **Evidence:** Timestamps, SLA details, lineage paths
- **Root-Cause Candidate:** Deepest failing node in the lineage graph
- **Next Steps:** Owner mentions and remediation guidance

**Sample excerpt:**
```markdown
## Incident Report: orders_archive
### What Broke
Dataset: **orders_archive** (data-eng owner)
Probe: FreshnessProbe
Status: FAIL

### Evidence
- Last modified: 2026-06-18 (45 days old)
- SLA: 24h
- Status: CHRONIC (still failing)

### Root-Cause Candidate
Dataset: **orders_archive** (0 hops upstream, is the failure)

### Next Steps
@data-eng: Check data pipeline; last run was 45 days ago.
```

### 7. Run Probes Again (Day 2)

Simulate a second run without fixing anything:

```bash
python -m datahub_rail.agent \
  --config config/probes.yaml \
  --datahub-url http://localhost:8080
```

**Expected state digest:**
```
Dataset: users — PASS (no change)
Dataset: orders_archive — FAIL (status: CHRONIC — still failing, deprioritized)
Dataset: events — FAIL (status: CHRONIC)
Dataset: transactions — FAIL (status: CHRONIC)
```

Notice: Probes fire on **change**, not raw thresholds. Chronic failures show up as "still failing" in state history rather than new alerts—this is the delta-aware digest.

### 8. Check Fix Artifacts for Schema Drift

For the `transactions` schema drift fault, review the generated fix artifacts:

```bash
ls -la outbox/
cat outbox/schema_patch_transactions_warehouse.yaml
cat outbox/schema_drift_transactions_warehouse.diff
cat outbox/commit_message_transactions_warehouse.txt
```

These artifacts are PR-ready:
- **Patch:** Downstream config correction (YAML) for consumers to adopt upstream schema
- **Diff:** Before/after unified diff showing the type change
- **Commit message:** Structured message linking fault class, detection method, owner

### Verification: Screenshots & Outputs

After each step, you can verify results:

1. **UI Verification:** Open http://localhost:8080 → Search "orders_archive" → Check `lastModified` metadata shows 45-day-old timestamp.
2. **Outbox Artifacts:** All incident reports, patches, and diffs land in `outbox/` directory—fully reproducible.
3. **State History:** Run twice to see delta-aware state history; second run shows "CHRONIC" classifications.

All sample outputs are committed to `sample-outputs/` for judge verification.

## Probes Engine

The health monitor runs three probe classes against each dataset:

1. **FreshnessProbe** — Capture-based: measures dataset age via `lastModified` metadata timestamp, compares against configurable SLA (default: 24h). Never queries job heartbeats; detects staleness from data's own recency signals.

2. **LineageProbe** — Walks upstream edges (1 hop by default) to detect broken/missing dependencies. Loud warns on "watch blind" states (no lineage data available).

3. **SchemaProbe** — Compares actual schema fields against expected downstream contract (e.g., `amount: decimal(12,2)`). Detects type drift when upstream column type changes.

**Never-raise contract:** All probes catch exceptions and return `ProbeResult` with `status: fail` and an actionable message. No silent passes on unreachable states.

**Config-driven registry:** Probes are loaded from `config/probes.yaml`, so you can point the agent at your own estate by editing the config. Example:

```yaml
probes:
  - name: freshness
    type: freshness
    params:
      sla_hours: 24
  - name: lineage_integrity
    type: lineage
    params: {}
  - name: schema_contract
    type: schema
    params:
      expected_fields:
        amount: decimal(12,2)
```

## Delta-Aware State History

**The Alarm-Fatigue Killer.** Traditional threshold-based alerting fires on every violation, drowning teams in alert noise when systems degrade gracefully or when a single upstream SLA miss cascades across a hundred datasets. Datahub-rail solves this by persisting per-probe status history (JSONL) and rendering **delta-aware digests** — meaningful alerts that fire on *change*, not raw thresholds.

On each run, the digest classifies failures as: **NEW** (first occurrence; triggers urgency), **CHRONIC** (still failing on day N; deprioritized but tracked), or **RECOVERED** (flip from fail→pass; closes the incident). First run with no history degrades gracefully; empty state renders as no-op. This originality criterion distinguishes datahub-rail from every existing threshold-alert tool in the category and directly addresses the capture-reliability doctrine: *fail loud on outage, suppress noise on chronic states, celebrate recovery*.

## Lineage-Walk Triage

When a probe fails, the agent walks the lineage graph upstream from the failing dataset to identify the **root-cause candidate**—the deepest failing node in the dependency chain. It then:

1. **Collects upstream nodes** — BFS walk collecting all ancestors up to configurable depth
2. **Filters failing candidates** — Identifies which upstream nodes have probe failures
3. **Picks root cause** — Selects the deepest failing node (furthest from failure); deterministic tie-breaking by URN
4. **Gathers evidence** — Freshness timestamps, lineage path, probe messages (all from graph reads)
5. **Generates owner-addressed markdown report** — Structured incident narrative with @mentions

**Provenance guarantee:** Every fact in the report (timestamps, owners, lineage edges, probe results) is sourced directly from DataHub graph reads. LLM only phrases the narrative; facts are never hallucinated. Reports land in `outbox/` directory.

Example report structure:
```markdown
## Incident Report
### What Broke
Dataset: **events** (analytics team owner)
### Evidence
- Freshness: stale (5 days old, SLA: 24h)
- Lineage path: raw-events → events
### Root-Cause Candidate
Dataset: **raw-events** (kafka-ops owner, 1 hop upstream)
### Next Steps
Contact root-cause owner...
---
*All facts in this report sourced from DataHub context graph reads.*
```

## Demo Data Estate

The project includes a deterministic seed script (`scripts/seed_demo_estate.py`) that plants a synthetic data estate with deliberately injected faults for demonstration and testing. This enables reproducible video footage and judge-verifiable outputs.

### Fault Classes (3)

1. **Stale Freshness** — A dataset (`orders_archive`) with `lastModified` timestamp 45 days old, beyond a typical SLA. Visible in DataHub UI via freshness metadata.

2. **Broken Lineage Edge** — A downstream dataset (`events`) with an upstream dependency on a deleted dataset (`raw_events_old`). The lineage edge points to a non-existent entity.

3. **Schema-Contract Drift** — An upstream dataset (`transactions`) where the `amount` column type changed from `decimal(12,2)` to `int`, while a downstream consumer (`transactions_warehouse`) still expects `decimal(12,2)`. Type mismatch detectable via schema metadata.

### Healthy Controls

- **users** table: current freshness, full schema, no lineage issues.

### Running the Seeder

**One-command seed (idempotent re-runs):**
```bash
DATAHUB_GMS_URL=http://localhost:8080 \
  python scripts/seed_demo_estate.py
```

Re-running the script is idempotent: it upserts datasets and edges, so multiple runs do not create duplicates.

## Upstream Contribution

**Bonus criterion achieved:** Health-monitoring agent patterns guide contributed to the DataHub MCP Server project.

See [PR #174](https://github.com/acryldata/mcp-server-datahub/pull/174) on the upstream mcp-server-datahub repository: `docs/agent-patterns-health-monitoring.md`. This guide documents the architectural patterns used in datahub-rail-agent and is designed to help future hackathon participants and DataHub users build their own health-monitoring agents:

- Capture-based freshness probes
- Never-raise error contract
- Delta-aware alerting with state history
- Lineage-walk root-cause triage
- Provenance guarantees (graph reads only)

## Hackathon entry

Built for **Build with DataHub: The Agent Hackathon** (Devpost).

## Prior inspiration disclosure

The design applies a capture-reliability doctrine battle-tested in a private ops system (capture-based liveness, fail-loud on outage, freshness verified before reporting state). All code in this repository is newly written during the submission period.

## Doctrine & Inspiration

This project applies architectural patterns from capture-reliability doctrine, battle-tested in private ops systems:

1. **Capture-based liveness** — Measure freshness from data's own timestamps (`lastModified`), not job heartbeats. Jobs can succeed silently while data stales.
2. **Fail-loud on outage** — All probes have never-raise contracts; exceptions become actionable messages. Silent passes on unreachable states are replaced with loud failures.
3. **Delta-aware alerting** — Fire on meaningful state *change* (NEW / CHRONIC / RECOVERED), not raw thresholds. Eliminates alert fatigue while preserving urgency signals.
4. **Lineage-walk root-cause triage** — Walk the DAG to find the deepest failing node; surface owner @mentions in reports so blame doesn't land on innocent consumers.
5. **Provenance guarantee** — Every fact in incident reports is sourced from DataHub graph reads. LLM only phrases narrative; facts are never hallucinated.

All code in this repository is newly written during the Build with DataHub: The Agent Hackathon submission period.

## License

Apache-2.0
