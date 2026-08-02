# DataHub Rail Agent — Demo Video Script

**Target Duration:** <3 minutes (170 seconds max)  
**Narrator:** Kevin Masterson  
**Audience:** Hackathon judges  

---

## Scene 1: The Problem (0:00–0:20)

### Shot List
- **0:00–0:10:** Terminal showing a "healthy" DataHub UI with dataset `orders_archive` displayed in browser
  - Point to `lastModified` timestamp in UI: "45 days ago"
- **0:10–0:15:** Close-up of laptop screen; narrator voiceover: "This dataset stopped loading 45 days ago. But the dashboard still shows green."
- **0:15–0:20:** Terminal showing an actual pipeline log: "Job succeeded" (heartbeat-based alerting is the problem)

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
- **0:20–0:25:** Terminal window showing `git clone && pip install`
  ```bash
  git clone https://github.com/<org>/datahub-rail-agent
  cd datahub-rail-agent && python -m venv .venv && source .venv/bin/activate
  pip install -e .
  ```
  (Commands scroll; ~5 sec)

- **0:25–0:30:** Docker running DataHub
  ```bash
  docker run -d -p 8080:8080 acryldata/datahub-gms:latest
  # Wait for it...
  curl http://localhost:8080/health  # ✓ 200 OK
  ```

- **0:30–0:35:** Start MCP server (show terminal output)
  ```bash
  mcp-server-datahub --datahub-url http://localhost:8080
  # MCP Server listening...
  ```

- **0:35–0:40:** Seed the demo estate (show seeder output)
  ```bash
  DATAHUB_GMS_URL=http://localhost:8080 python scripts/seed_demo_estate.py
  # ✓ Seeded: users (healthy)
  # ✓ Seeded: orders_archive (stale: 45 days)
  # ✓ Seeded: events (broken lineage)
  # ✓ Seeded: transactions (schema drift)
  ```

### Narrator Script
```
"I'll run it on my laptop. Clone, install, start DataHub, start the 
MCP server, and seed a demo estate with three deliberate faults: a 
stale dataset, a broken lineage edge, and a schema drift. All in 20 seconds."
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

- **0:45–1:00:** Show full terminal output (scroll through slowly)
  ```
  [INFO] Probing dataset: users
  [PASS] users — freshness OK, lineage OK, schema OK
  
  [INFO] Probing dataset: orders_archive
  [FAIL] orders_archive — Freshness probe: FAIL (45 days old, SLA: 24h)
  
  [INFO] Probing dataset: events
  [FAIL] events — Lineage probe: FAIL (upstream dataset 'raw_events_old' missing)
  
  [INFO] Probing dataset: transactions
  [FAIL] transactions — Schema probe: FAIL (amount: int, expected decimal(12,2))
  
  [INFO] Generated incident reports: outbox/
  [INFO] Generated fix artifacts: outbox/
  ```

- **1:00–1:05:** List outbox directory
  ```bash
  ls -la outbox/
  # incident_orders_archive_*.md
  # incident_events_*.md
  # incident_transactions_*.md
  # schema_patch_transactions_warehouse.yaml
  # schema_drift_transactions_warehouse.diff
  # commit_message_transactions_warehouse.txt
  ```

- **1:05–1:15:** Show one incident report (scroll)
  ```bash
  cat outbox/incident_orders_archive_*.md
  # ## Incident Report: orders_archive
  # ### What Broke
  # Dataset: orders_archive (data-eng owner)
  # Probe: FreshnessProbe
  # Status: FAIL (NEW)
  # 
  # ### Evidence
  # Last modified: 2026-06-18 (45 days old)
  # SLA: 24h
  # 
  # ### Root-Cause Candidate
  # Dataset: orders_archive (0 hops, is the failure)
  # 
  # ### Next Steps
  # @data-eng: Check data pipeline; last run was 45 days ago.
  ```

### Narrator Script
```
"First run: the agent runs three probes—freshness, lineage, and schema—
against each dataset. It catches all three faults in real time:

[pause for terminal output]

Notice: users passes (healthy control). The other three fail loudly with 
actionable messages. The agent generates incident reports with owner 
@mentions so the right person sees it immediately."
```

### Timing: ~35 sec

---

## Scene 4: Day 2 Run — Delta-Aware State History (1:15–1:55)

### Shot List
- **1:15–1:20:** Narrator sets up: "I'll run the agent again without fixing anything."
  ```bash
  # (same command as before)
  python -m datahub_rail.agent --config config/probes.yaml \
    --datahub-url http://localhost:8080
  ```

- **1:20–1:35:** Show terminal output with state digest (scroll slowly)
  ```
  [INFO] Probing dataset: users
  [PASS] users — freshness OK, lineage OK, schema OK
  
  [INFO] Probing dataset: orders_archive
  [FAIL] orders_archive — Freshness probe: FAIL
         Status: CHRONIC (still failing on day 2, deprioritized)
  
  [INFO] Probing dataset: events
  [FAIL] events — Lineage probe: FAIL
         Status: CHRONIC (still failing on day 2, deprioritized)
  
  [INFO] Probing dataset: transactions
  [FAIL] transactions — Schema probe: FAIL
         Status: CHRONIC (still failing on day 2, deprioritized)
  
  [INFO] State history updated: state_history.jsonl
  ```

- **1:35–1:45:** Show the state history digest
  ```bash
  cat state_history.jsonl | tail -20
  # Shows NEW vs CHRONIC classifications
  # Demonstrates delta-aware alerting: only fires on change
  ```

- **1:45–1:55:** Narrator explains the key innovation
  ```
  "Notice: day 2 still shows failures, but they're marked CHRONIC. 
  The agent fires alerts on meaningful *change*, not raw thresholds. 
  This is the core originality: delta-aware alerting eliminates alert 
  fatigue while preserving urgency signals. If a failure recovers, 
  the agent fires a RECOVERED alert to close the incident."
  ```

### Narrator Script
```
"Day 2 run without fixing anything. Same three datasets fail, but 
notice the status: CHRONIC. The alert doesn't fire again because 
nothing changed. This is the core innovation: fire on meaningful 
*change*, not raw thresholds.

Compare this to traditional monitoring that fires every time a 
threshold is crossed. By day 2, you're drowning in alerts and 
everyone stops listening. DataHub Rail only fires when state 
changes—when something breaks, when it stays broken (CHRONIC), 
or when it recovers."
```

### Timing: ~40 sec

---

## Scene 5: Schema-Drift Fix Artifacts (1:55–2:30)

### Shot List
- **1:55–2:00:** Explain what's in outbox
  ```bash
  ls outbox/ | grep transactions
  # schema_patch_transactions_warehouse.yaml
  # schema_drift_transactions_warehouse.diff
  # commit_message_transactions_warehouse.txt
  ```

- **2:00–2:10:** Show the patch artifact
  ```bash
  cat outbox/schema_patch_transactions_warehouse.yaml
  # ---
  # operations:
  #   - op: replace
  #     path: /fields/amount/type
  #     value: int
  ```

- **2:10–2:20:** Show the diff artifact
  ```bash
  cat outbox/schema_drift_transactions_warehouse.diff
  # --- before
  # +++ after
  #  amount: decimal(12,2)
  # +amount: int
  ```

- **2:20–2:30:** Show the commit message
  ```bash
  cat outbox/commit_message_transactions_warehouse.txt
  # chore: Update schema for transactions_warehouse to match upstream
  # 
  # Detected schema-contract drift:
  # - Field: amount
  # - Upstream type: int
  # - Expected type: decimal(12,2)
  # - Fault class: SCHEMA_DRIFT
  # - Detection method: SchemaProbe
  # 
  # Downstream consumer: transactions_warehouse
  # Owner: @data-consumer-team
  ```

### Narrator Script
```
"For schema drift, the agent emits PR-ready fix artifacts: a YAML 
patch for config changes, a unified diff showing the type mismatch, 
and a commit message linking the fault class, detection method, and 
owner. Judges can review these artifacts in the outbox/ directory 
and verify reproducibility."
```

### Timing: ~35 sec

---

## Scene 6: Closing Remarks (2:30–2:50)

### Shot List
- **2:30–2:40:** Show the sample-outputs/ directory
  ```bash
  ls sample-outputs/
  # All incident reports, patches, diffs committed for reproducibility
  ```

- **2:40–2:50:** Show README quick-start
  ```bash
  cat README.md | head -50
  # "Quick Start: From Zero to Demo"
  # Shows reproducibility path
  ```

### Narrator Script
```
"The entire demo is reproducible: all sample outputs are committed 
to the repo. A judge can clone, install, run the seeder, run the 
agent, and see the exact same reports and artifacts in seconds.

DataHub Rail Agent brings three ideas to data monitoring:
1. Capture-based freshness probes measure data age directly, not job logs.
2. Delta-aware state history fires on meaningful change, eliminating alert fatigue.
3. Lineage-walk root-cause triage with owner @mentions so blame lands 
   on the real culprit.

The code is production-ready: 86 tests, never-raise contracts, and 
an upstream contribution to the DataHub MCP Server repository showing 
these patterns can be reused."
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

**Buffer:** 10 seconds (under 3-minute target of 180 sec)

---

## Production Notes

1. **Screen Resolution:** Record at 1920x1080 or higher for text readability
2. **Font Size:** Terminal font should be at least 14pt; IDE themes with high contrast
3. **Pacing:** Scroll terminal output slowly (~2 sec per command) so judges can read
4. **Audio:** Speak clearly; background music optional but can help (no copyright issues)
5. **Callouts:** Use terminal highlighting or cursor circles to emphasize key lines
6. **Captions:** Add timestamps in lower-left corner (0:00, 1:00, 2:00, etc.)

---

## Reproducibility Verification

Judges can verify this entire demo by running:

```bash
git clone https://github.com/<org>/datahub-rail-agent
cd datahub-rail-agent
python -m venv .venv && source .venv/bin/activate
pip install -e .

# Start DataHub
docker run -d -p 8080:8080 acryldata/datahub-gms:latest

# Start MCP server (in separate terminal)
mcp-server-datahub --datahub-url http://localhost:8080

# Seed demo
DATAHUB_GMS_URL=http://localhost:8080 python scripts/seed_demo_estate.py

# Run day 1
python -m datahub_rail.agent --config config/probes.yaml --datahub-url http://localhost:8080

# Review outputs
ls -la outbox/ && cat outbox/incident_*.md
```

Expected output matches the video exactly. All sample outputs in `sample-outputs/` are committed for judge reference.
