# DataHub Rail Agent — Demo Video Script

**Target Duration:** <3 minutes (170 seconds max)
**Narrator:** Kevin Masterson
**Audience:** Hackathon judges

Every command in this script has been run against a live DataHub quickstart
(server v1.7.0, mcp-server-datahub v3.4.6) and the output blocks are the
real output. A copy/paste-ready ordering is in
[DEMO_CRIB_SHEET.md](DEMO_CRIB_SHEET.md).

**Before recording:** have DataHub already running and the estate seeded, and
delete `state_history.jsonl` so the first take is a clean day 1.

---

## Scene 1: The Problem (0:00–0:20)

### Shot List
- **0:00–0:10:** Browser on http://localhost:9002 (login `datahub`/`datahub`),
  searching `orders_archive`; point at the last-modified metadata: 45 days old
- **0:10–0:20:** Narrator to camera

### Narrator Script
```
"Data pipelines fail silently. This dataset stopped loading 45 days ago,
but because monitoring watched job heartbeats instead of data freshness,
no alert fired. When the data team finally noticed, blame landed on
innocent downstream consumers instead of the root cause.

DataHub Rail Agent fixes this with three ideas: capture-based health
checks, meaningful alerts, and lineage-walk root-cause triage."
```

### Timing: ~20 sec

---

## Scene 2: Setting Up the Demo (0:20–0:40)

### Shot List
- **0:20–0:30:** Terminal, install (pre-run off camera; show the commands)
  ```bash
  git clone https://github.com/fivedollarfridays/datahub-rail-agent.git
  cd datahub-rail-agent
  python3.11 -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]" -c constraints.txt
  ```

- **0:30–0:35:** DataHub already up
  ```bash
  curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health
  # 200
  ```

- **0:35–0:40:** Seed the demo estate
  ```bash
  DATAHUB_GMS_URL=http://localhost:8080 python scripts/seed_demo_estate.py
  ```
  ```
  ✓ Seeded dataset: users (healthy control)
  ✓ Seeded dataset: orders_archive (stale: 45 days old)
  ✓ Seeded dataset: events (broken lineage: upstream soft-deleted)
  ✓ Seeded dataset: transactions (schema drift: int vs decimal(12,2))
  ✓ Seeded dataset: transactions_warehouse (downstream consumer)

  Seeded 1 healthy control(s) and 3 fault class(es) into http://localhost:8080
  ```

### Narrator Script
```
"I'll run it on my laptop. Clone, install, and seed a demo estate with
three deliberate faults: a stale dataset, a broken lineage edge, and a
schema drift. There's no separate MCP server to babysit — the agent
launches the DataHub MCP server itself."
```

### Timing: ~20 sec

---

## Scene 3: First Run — Probes Catch All 3 Faults (0:40–1:15)

### Shot List
- **0:40–0:45:** Run the agent for the first time
  ```bash
  python -m datahub_rail.agent --config config/probes.yaml \
    --datahub-url http://localhost:8080
  ```
  (First run takes a few seconds while `uvx` starts the MCP server.)

- **0:45–1:00:** Probe results
  ```
  [FAIL] events — lineage_integrity: Broken lineage: declared upstream 'raw_events_old' missing from the graph
  [FAIL] orders_archive — freshness: Dataset is stale: last modified 45 days ago (SLA: 24h)
  [FAIL] transactions — schema_contract: Schema drift on 'amount': expected decimal(12,2), got int
  [PASS] transactions_warehouse — freshness OK, lineage_integrity OK
  [PASS] users — freshness OK, lineage_integrity OK
  ```

- **1:00–1:05:** The digest below it, on first sight of each fault

  **PRODUCTION NOTE:** the real day-1 digest prints a
  `--- Delta-aware state digest ---` header plus 11 lines, with `PASS:` lines
  interleaved between the `NEW:` lines. Only day 2 is naturally clean, because
  only *changed* states print. To make the screen match the three lines below,
  filter the run on camera with `| grep -E '^\[|^NEW'` (that keeps both the
  probe lines above and the NEW lines here). Otherwise reword the beat, because
  narrating "three NEW lines" over eleven lines of output reads badly.

  ```
  NEW: ...demo.public.events,PROD) / lineage_integrity — Broken lineage: declared upstream 'raw_events_old' missing from the graph
  NEW: ...demo.public.orders_archive,PROD) / freshness — Dataset is stale: last modified 45 days ago (SLA: 24h)
  NEW: ...demo.public.transactions,PROD) / schema_contract — Schema drift on 'amount': expected decimal(12,2), got int
  ```

- **1:05–1:15:** Show one incident report, scrolling to the provenance table
  ```bash
  ls outbox/
  cat outbox/incident_orders_archive_*.md
  ```
  ```markdown
  ### What Broke
  Dataset: **orders_archive**
  Owner(s): @data-eng

  ### Evidence
  - **Failing probe**: `freshness`
  - **Probe**: Dataset is stale: last modified 45 days ago (SLA: 24h)
  - **Last modified**: 2026-06-18 20:18 UTC (45 days old)

  ### Root-Cause Candidate
  Dataset: **orders_archive** — is the failure
  Distance from failure: 0 hops

  ### Provenance
  | Fact source (tool) | Entity | Read at |
  |---|---|---|
  | `gms:datasetProperties.lastModified` | `urn:...orders_archive,PROD)` | 2026-08-02T20:21:02+00:00 |
  | `mcp:get_lineage` | `urn:...orders_archive,PROD)` | 2026-08-02T20:21:02+00:00 |
  ```

### Narrator Script
```
"First run: three probes — freshness, lineage, and schema — against every
dataset in the estate. It catches all three faults and passes both healthy
controls.

Every incident report ends with a provenance table: the exact tool, entity
and timestamp behind each claim. Nothing in the evidence is generated
text — if it's in the report, it came out of the graph."
```

### Timing: ~35 sec

---

## Scene 4: Day 2 Run — Delta-Aware State History (1:15–1:55)

### Shot List
- **1:15–1:20:** "I'll run it again without fixing anything." Same command:
  ```bash
  python -m datahub_rail.agent --config config/probes.yaml \
    --datahub-url http://localhost:8080
  ```

- **1:20–1:40:** Same probe lines, but the digest has changed
  ```
  CHRONIC: ...demo.public.events,PROD) / lineage_integrity (day 2) — Broken lineage: declared upstream 'raw_events_old' missing from the graph
  CHRONIC: ...demo.public.orders_archive,PROD) / freshness (day 2) — Dataset is stale: last modified 45 days ago (SLA: 24h)
  CHRONIC: ...demo.public.transactions,PROD) / schema_contract (day 2) — Schema drift on 'amount': expected decimal(12,2), got int
  ```

- **1:40–1:50:** The history behind it
  ```bash
  grep fail state_history.jsonl | tail -3
  ```
  (NOT a bare `tail -3` — the last three records are `pass` rows for
  `transactions_warehouse` and `users`, not the failures being narrated.)

- **1:50–1:55:** Optional recovery beat — if you want to show `RECOVERED`,
  re-seed `orders_archive` with a current timestamp and run once more.

### Narrator Script
```
"Day 2, nothing fixed. The same three datasets fail — but the digest now
says CHRONIC, day 2, instead of NEW. Nothing was backdated and no clock
was faked; the difference is the state history the first run wrote.

That's the core idea: fire on meaningful change, not raw thresholds.
Traditional monitoring re-fires every time the threshold is crossed, and
by day two everyone has stopped reading the alerts. This agent fires when
something breaks, tells you when it's still broken, and closes it out with
RECOVERED when it heals."
```

### Timing: ~40 sec

---

## Scene 5: Schema-Drift Fix Artifacts (1:55–2:30)

### Shot List
- **1:55–2:00:** What landed in the outbox
  ```bash
  ls outbox/ | grep transactions_warehouse
  # commit_message_transactions_warehouse.txt
  # schema_drift_transactions_warehouse.diff
  # schema_patch_transactions_warehouse.yaml
  ```

- **2:00–2:10:** The diff
  ```bash
  cat outbox/schema_drift_transactions_warehouse.diff
  ```
  ```diff
  --- a/contracts/transactions_warehouse.schema.yaml
  +++ b/contracts/transactions_warehouse.schema.yaml
  @@ -8,4 +8,4 @@
     - field_path: id
       type: bigint
     - field_path: amount
  -    type: decimal(12,2)
  +    type: int
  ```

- **2:10–2:20:** The money shot — it actually applies
  ```bash
  git apply --check outbox/schema_drift_transactions_warehouse.diff && echo "applies cleanly"
  # applies cleanly
  ```

- **2:20–2:30:** The commit message
  ```bash
  cat outbox/commit_message_transactions_warehouse.txt
  ```

### Narrator Script
```
"For schema drift the agent emits PR-ready artifacts: a YAML patch, a
unified diff against the downstream contract that's committed in the repo,
and a commit message linking fault class, detection method and owner.

And 'PR-ready' is checkable — git apply accepts the diff. The test suite
applies it for real on every run, so it can't rot."
```

### Timing: ~35 sec

---

## Scene 6: Closing Remarks (2:30–2:50)

### Shot List
- **2:30–2:40:** The committed sample outputs
  ```bash
  ls sample-outputs/
  ```
- **2:40–2:50:** Tests green
  ```bash
  python -m pytest tests/ -q | tail -1
  # 220 passed
  ```

### Narrator Script
```
"The whole demo is reproducible: sample-outputs holds the artifacts from a
real two-run pass, regenerated by a script rather than written by hand.

Three ideas: capture-based freshness probes that measure data age instead
of reading job logs; delta-aware state history that fires on change; and
lineage-walk triage with owner mentions so blame lands on the real culprit.
220 tests, never-raise contracts, and an upstream patterns guide contributed
back to the DataHub MCP Server repo."
```

### Timing: ~20 sec

---

## Total Timing Breakdown

| Scene | Duration |
|-------|----------|
| Problem | 20 sec |
| Setup | 20 sec |
| Day 1 Run | 35 sec |
| Day 2 Run | 40 sec |
| Fix Artifacts | 35 sec |
| Closing | 20 sec |
| **TOTAL** | **170 sec** |

**Buffer:** 10 seconds (under the 3-minute target).

---

## Production Notes

1. **Screen Resolution:** record at 1920x1080 or higher
2. **Font Size:** terminal at 14pt or larger
3. **Pacing:** scroll terminal output slowly so judges can read
4. **Long URNs:** the digest lines are wide — either widen the terminal or
   accept the wrap; don't shrink the font below readable
5. **First-run latency:** `uvx` fetches the MCP server on first use. Warm it
   before recording so the take isn't dead air
6. **Captions:** timestamps in the lower-left (0:00, 1:00, 2:00)

---

## Reproducibility Verification

```bash
git clone https://github.com/fivedollarfridays/datahub-rail-agent.git
cd datahub-rail-agent
python3.11 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]" -c constraints.txt

datahub docker quickstart

DATAHUB_GMS_URL=http://localhost:8080 python scripts/seed_demo_estate.py
python -m datahub_rail.agent --config config/probes.yaml --datahub-url http://localhost:8080
python -m datahub_rail.agent --config config/probes.yaml --datahub-url http://localhost:8080

ls outbox/ && cat outbox/incident_*.md
git apply --check outbox/schema_drift_transactions_warehouse.diff
```
