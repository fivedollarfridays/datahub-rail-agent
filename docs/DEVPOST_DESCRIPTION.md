# DataHub Rail Agent — Devpost Submission

## Inspiration

Data pipelines fail silently. A dataset stops loading, a schema drifts, lineage breaks—but dashboards stay green because the monitoring looked at job heartbeats instead of data freshness. When something finally surfaces, blame lands on innocent downstream consumers instead of the root cause.

This agent solves three problems:
1. **Silent outages surface as loud incidents** — Capture-based probes measure data freshness from its own `lastModified` timestamp, not job logs.
2. **Alerts fire on meaningful change, not noise** — State history tracks NEW / CHRONIC / RECOVERED classifications, so alert fatigue doesn't kill signal.
3. **Root-cause is walkable, not guessed** — Lineage triage finds the deepest failing node and generates owner-addressed incident reports with @mentions.

## What It Does

**DataHub Rail Agent** runs three classes of health-monitoring probes over a data estate, classifies failures with delta-aware state history, and generates incident reports with PR-ready fix artifacts.

### Probes

1. **Freshness Probe** — Measures dataset age via `lastModified` timestamp; compares against SLA (default: 24h). Captures stale data in-flight, before cascading failures.
2. **Lineage Probe** — Compares declared upstream edges against the edges the graph can still resolve. A dataset that declares no upstream is a source table and passes; one whose declared upstream no longer resolves fails loudly and names the missing dataset.
3. **Schema Probe** — Detects contract drift when upstream column types change (e.g., `decimal(12,2)` → `int`).

All probes have **never-raise contracts**: exceptions become actionable messages instead of silent passes.

### Delta-Aware State History

Traditional alerting fires on every violation, drowning teams in noise. This agent persists state history and renders **meaningful alerts**:
- **NEW** — First failure; triggers urgency
- **CHRONIC** — Still failing on day N; deprioritized but tracked
- **RECOVERED** — Flip from fail→pass; closes incident

First run with no history degrades gracefully.

### Lineage-Walk Triage

When a probe fails, the agent walks the graph upstream to find the root-cause candidate—the deepest failing node. It then gathers evidence (timestamps, owners, lineage path) and generates markdown incident reports with @mentions for owners.

**Provenance guarantee:** Every fact (timestamps, owners, lineage edges, probe results) is sourced from DataHub graph reads. LLM only phrases the narrative; facts are never hallucinated.

### Schema-Drift Fix Artifacts

For schema-contract violations, the agent emits PR-ready artifacts:
- **YAML patch** — Downstream config correction for consumers to adopt upstream schema
- **Unified diff** — Computed with difflib against the committed downstream contract (`contracts/transactions_warehouse.schema.yaml`), so `git apply` accepts it; the test suite applies it for real on every run
- **Commit message** — Structured message linking fault class, detection method, owner

## Tech Stack

- **Language:** Python 3.11+
- **DataHub Integration:** DataHub MCP Server (Model Context Protocol)
- **Data Structures:** Python dataclasses for typed graph entities; JSONL for state history
- **Storage:** Local outbox/ directory for incidents and artifacts
- **Testing:** pytest (131 tests, 85% line coverage) with recorded-response fixtures; ruff 0.16.1 and the full suite run in GitHub Actions

## DataHub Surfaces Used

1. **Context Graph Reads via MCP Server** — `search` (dataset discovery), `get_entities` (owner, name, platform), `list_schema_fields` (field types), `get_lineage` (resolved upstream edges)
2. **Aspect Reads via OpenAPI v3** — `datasetProperties.lastModified` for capture-based freshness and the `upstreamLineage` aspect for declared edges. The MCP tool surface exposes neither: entity properties come back without `lastModified`, and `get_lineage` only returns upstreams that still resolve, so a soft-deleted upstream — the exact broken-lineage fault — simply disappears
3. **Metadata Ingestion** — Seeder writes datasets, schemas, ownership and lineage through the OpenAPI v3 entity endpoint, failing loud on any non-2xx or error body
4. **Lineage Navigation** — BFS graph walk to identify root-cause candidates
5. **Owner Information** — Read from the ownership aspect for @mentions in incident reports

## Demo

The project includes a reproducible demo estate with 3 deliberate faults:
1. **Stale Freshness** — Dataset `orders_archive`, 45 days old (SLA: 24h)
2. **Broken Lineage** — Dataset `events` with upstream dependency on deleted dataset
3. **Schema Drift** — Dataset `transactions` where `amount` column changed from `decimal(12,2)` to `int`

Plus healthy controls (`users`, `transactions_warehouse`) to show passing probes.

**One-command seed:**
```bash
DATAHUB_GMS_URL=http://localhost:8080 python scripts/seed_demo_estate.py
```

Re-running the seeder is idempotent. All sample outputs (incident reports, patches, diffs, state digest) are committed, and they are regenerated from a real two-run pass by `scripts/refresh_sample_outputs.py` rather than written by hand.

## Key Innovation

**Delta-aware alerting** is the core originality. Existing tools alert on raw thresholds (freshness > 24h = fire). This agent fires on **state change**:
- Same failure on day 1 and day 2? → "CHRONIC" (deprioritized)
- Recovery from failure? → "RECOVERED" (closes ticket)

This directly addresses the capture-reliability doctrine: *fail loud on outage, suppress noise on chronic states, celebrate recovery*.

## Code Quality

- **131 tests, 85% line coverage**, including tests that apply the generated patch with `git apply`
- **Never-raise contract** enforced throughout: no silent passes on reads, and loud failures on writes
- **TDD throughout** — all features written test-first
- **Architecture enforced** — file and function size limits checked in CI
- **Upstream contribution** — Health-monitoring agent patterns guide contributed to [DataHub MCP Server PR #174](https://github.com/acryldata/mcp-server-datahub/pull/174)

## Future Enhancements

- Custom probe plugins (community-contributed probe types)
- Slack/PagerDuty integration for incident notifications
- Dashboard UI for state history and trend analysis
- Auto-remediation hooks (e.g., auto-retry stale pipelines)

## Inspiration & Doctrine

The architecture applies capture-reliability patterns from battle-tested private ops systems. All code is newly written during the hackathon submission period. See README for full doctrine disclosure.

---

**Repository:** https://github.com/fivedollarfridays/datahub-rail-agent  
**Demo Video:** [TBD — Kevin will record]  
**Hackathon:** Build with DataHub: The Agent Hackathon
