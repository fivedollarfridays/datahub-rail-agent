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
2. **Lineage Probe** — Walks upstream edges to detect broken dependencies and missing lineage data. Warns loudly on "watch blind" states.
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
- **Unified diff** — Before/after type change, visually clear
- **Commit message** — Structured message linking fault class, detection method, owner

## Tech Stack

- **Language:** Python 3.11+
- **DataHub Integration:** DataHub MCP Server (Model Context Protocol)
- **Data Structures:** Pydantic types for type safety; JSONL for state history
- **Storage:** Local outbox/ directory for incidents and artifacts
- **Testing:** pytest with fixture-based mocks; CI via GitHub Actions

## DataHub Surfaces Used

1. **Context Graph Reads** — `list_datasets`, `get_freshness`, `fetch_schema`, `walk_upstream` / `walk_downstream` via MCP Server
2. **Metadata Ingestion** — Seeder uses DataHub GraphQL API to inject test datasets with deliberate faults
3. **Lineage Navigation** — BFS graph walk to identify root-cause candidates
4. **Owner Information** — Fetched via graph reads for @mentions in incident reports

## Demo

The project includes a reproducible demo estate with 3 deliberate faults:
1. **Stale Freshness** — Dataset `orders_archive`, 45 days old (SLA: 24h)
2. **Broken Lineage** — Dataset `events` with upstream dependency on deleted dataset
3. **Schema Drift** — Dataset `transactions` where `amount` column changed from `decimal(12,2)` to `int`

Plus one healthy control (`users` table) to show passing probes.

**One-command seed:**
```bash
DATAHUB_GMS_URL=http://localhost:8080 python scripts/seed_demo_estate.py
```

All sample outputs (incident reports, patches, diffs) are committed and reproducible.

## Key Innovation

**Delta-aware alerting** is the core originality. Existing tools alert on raw thresholds (freshness > 24h = fire). This agent fires on **state change**:
- Same failure on day 1 and day 2? → "CHRONIC" (deprioritized)
- Recovery from failure? → "RECOVERED" (closes ticket)

This directly addresses the capture-reliability doctrine: *fail loud on outage, suppress noise on chronic states, celebrate recovery*.

## Code Quality

- **100% test coverage** on new modules (86 total tests)
- **Never-raise contract** enforced throughout: no silent passes
- **TDD throughout** — all features written test-first
- **Architecture enforced** — 400-line file ceiling; functions under limits
- **Upstream contribution** — Health-monitoring agent patterns guide contributed to [DataHub MCP Server PR #174](https://github.com/acryldata/mcp-server-datahub/pull/174)

## Future Enhancements

- Custom probe plugins (community-contributed probe types)
- Slack/PagerDuty integration for incident notifications
- Dashboard UI for state history and trend analysis
- Auto-remediation hooks (e.g., auto-retry stale pipelines)

## Inspiration & Doctrine

The architecture applies capture-reliability patterns from battle-tested private ops systems. All code is newly written during the hackathon submission period. See README for full doctrine disclosure.

---

**Repository:** https://github.com/<org>/datahub-rail-agent  
**Demo Video:** [TBD — Kevin will record]  
**Hackathon:** Build with DataHub: The Agent Hackathon
