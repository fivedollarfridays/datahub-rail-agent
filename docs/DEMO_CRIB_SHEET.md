# Demo Crib Sheet

Copy/paste-ready commands in the order they need to run, for recording the
demo video. Verified end to end on macOS (Apple Silicon) against DataHub
quickstart v1.7.0 with mcp-server-datahub v3.4.6.

The narrative version with timings is in
[DEMO_VIDEO_SCRIPT.md](DEMO_VIDEO_SCRIPT.md).

---

## 0. One-time setup (off camera)

```bash
git clone https://github.com/fivedollarfridays/datahub-rail-agent.git
cd datahub-rail-agent
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]" -c constraints.txt
```

Python 3.11 specifically — `pydantic-core` has no wheel for 3.14 and the
source build fails. On this machine: `/opt/homebrew/opt/python@3.11/bin/python3.11`.

`uv` must be on PATH (the agent shells out to `uvx`):

```bash
export PATH="$HOME/.local/bin:$PATH"
uvx --version
```

## 1. Start DataHub (off camera — slow)

```bash
pip install acryl-datahub
datahub docker quickstart          # first run pulls images, 15-30+ min
```

Health check (this one is worth showing on camera):

```bash
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:8080/health   # 200
```

UI at http://localhost:9002, login `datahub` / `datahub`.
GMS at http://localhost:8080. Auth is disabled locally, so no token.

## 2. Warm the MCP server (off camera)

Avoids dead air while `uvx` downloads on the first take:

```bash
DATAHUB_GMS_URL=http://localhost:8080 DATAHUB_GMS_TOKEN= \
  python scripts/mcp_smoke.py
```

Expect `initialize OK: server=datahub v3.4.6` and `tools/list OK: 6 tools`.

## 3. Reset to a clean day 1 (before every take)

```bash
rm -rf outbox state_history.jsonl
```

The state history is the only thing that makes run 2 differ from run 1, so
this is what rewinds the demo.

## 4. Seed the estate (on camera)

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

Idempotent — safe to re-run between takes. Search indexing is async, so
wait ~5 seconds before step 5 or the estate may come back empty.

## 5. Day 1 run (on camera)

```bash
python -m datahub_rail.agent --config config/probes.yaml \
  --datahub-url http://localhost:8080
```

```
[FAIL] events — lineage_integrity: Broken lineage: declared upstream 'raw_events_old' missing from the graph
[FAIL] orders_archive — freshness: Dataset is stale: last modified 45 days ago (SLA: 24h)
[FAIL] transactions — schema_contract: Schema drift on 'amount': expected decimal(12,2), got int
[PASS] transactions_warehouse — freshness OK, lineage_integrity OK
[PASS] users — freshness OK, lineage_integrity OK
```

Digest lines for the three faults start with `NEW:`. Exit code is 1.

Note: the MCP server logs to stderr. To keep the take clean:

```bash
python -m datahub_rail.agent --config config/probes.yaml \
  --datahub-url http://localhost:8080 2>/dev/null
```

## 6. Show an incident report (on camera)

```bash
ls outbox/
cat outbox/incident_orders_archive_*.md
```

Scroll to the **Provenance** table at the bottom — that is the "every claim
traces to a graph read" beat.

## 7. Day 2 run (on camera)

Identical command, nothing fixed, nothing backdated:

```bash
python -m datahub_rail.agent --config config/probes.yaml \
  --datahub-url http://localhost:8080 2>/dev/null
```

Digest lines now read:

```
CHRONIC: ...demo.public.events,PROD) / lineage_integrity (day 2) — ...
CHRONIC: ...demo.public.orders_archive,PROD) / freshness (day 2) — ...
CHRONIC: ...demo.public.transactions,PROD) / schema_contract (day 2) — ...
```

## 8. Fix artifacts (on camera)

```bash
ls outbox/ | grep transactions_warehouse
cat outbox/schema_drift_transactions_warehouse.diff
git apply --check outbox/schema_drift_transactions_warehouse.diff && echo "applies cleanly"
cat outbox/commit_message_transactions_warehouse.txt
```

`git apply --check` exits 0. Don't run a bare `git apply` on camera unless
you intend to modify `contracts/transactions_warehouse.schema.yaml` — if you
do, undo it with `git checkout -- contracts/`.

## 9. Optional: the RECOVERED beat

```bash
python - <<'PY'
import asyncio, datetime
from datahub_rail.seeder import DatasetSeeder
URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
async def main():
    s = DatasetSeeder("http://localhost:8080"); await s.connect()
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp() * 1000)
    await s.ingest_dataset(urn=URN, name="orders_archive", platform="postgres",
                           owner="data-eng", last_modified=now)
    await s.disconnect()
asyncio.run(main())
PY
sleep 3
python -m datahub_rail.agent --config config/probes.yaml \
  --datahub-url http://localhost:8080 2>/dev/null | grep RECOVERED
```

Restore the fault afterwards with `python scripts/seed_demo_estate.py`.

## 10. Closing shots (on camera)

```bash
ls sample-outputs/
python -m pytest tests/ -q | tail -1     # 220 passed
```

---

## Regenerating committed sample outputs

Not part of the video, but this is how `sample-outputs/` is kept honest —
it runs the agent twice against live DataHub and promotes the real files, so
the committed digest shows the day-2 CHRONIC state:

```bash
DATAHUB_GMS_URL=http://localhost:8080 python scripts/refresh_sample_outputs.py
```

## Gotchas

| Symptom | Cause / fix |
|---|---|
| Estate comes back empty right after seeding | Search indexing is async; wait ~5s |
| `uvx: command not found` | `export PATH="$HOME/.local/bin:$PATH"` |
| Long pause on first agent run | `uvx` is fetching the MCP server; warm it first (step 2) |
| Day 2 still shows `NEW` | `state_history.jsonl` was deleted between runs |
| Day 1 shows `CHRONIC` | Left-over history; `rm state_history.jsonl` |
| Noisy loguru lines in the take | Append `2>/dev/null` |
