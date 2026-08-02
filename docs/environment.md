# Local development environment

State note for the DataHub quickstart + MCP server environment this project
develops against. Last verified: 2026-08-02 on macOS (Apple Silicon), Docker
Desktop 29.2.1.

## Components and versions

| Component | Version | Where |
|---|---|---|
| DataHub CLI (`acryl-datahub`) | 1.6.0.17 | `.dhenv` venv in this repo (Python 3.11) |
| DataHub server (quickstart) | v1.5.0.6 | Docker containers |
| mcp-server-datahub | 3.4.5 | via `uvx mcp-server-datahub@latest` |
| `mcp` Python client package | in `.dhenv` | used by `scripts/mcp_smoke.py` |

## Venv setup (version-specific, important)

The system default `python3` is 3.14, which fails to install `acryl-datahub`
(pydantic-core has no 3.14 wheel and the source build fails). Use Homebrew
Python 3.11 (the version the CLI officially tests against; 3.12 works but
prints an "not actively tested" warning):

```bash
python3.11 -m venv ~/Projects/datahub-rail-agent/.dhenv
~/Projects/datahub-rail-agent/.dhenv/bin/pip install acryl-datahub mcp
```

Known benign conflict: installing `mcp` upgrades pydantic to 2.13.x while the
CLI's `mixpanel` dependency pins `<2.12`. pip warns; both the `datahub` CLI
and the smoke client work fine regardless.

## Start / stop the quickstart

```bash
DH=~/Projects/datahub-rail-agent/.dhenv/bin/datahub

$DH docker quickstart          # start (first run pulls images, 15-30+ min)
$DH docker quickstart --stop   # stop containers (data volumes preserved)
$DH docker check               # health check of the running containers
$DH docker nuke                # remove containers, networks, AND volumes (wipes data)
```

Success signal: `http://localhost:9002` returns HTTP 200 and
`datahub docker check` reports healthy.

## Ports

| Port | Service |
|---|---|
| 9002 | DataHub frontend UI (login `datahub` / `datahub`) |
| 8080 | GMS (metadata service): REST, `/api/graphql`, OpenAPI |
| 3306 | MySQL 8.2 |
| 9092 | Kafka broker (Confluent cp-kafka 8.0.0) |
| 9200 | OpenSearch 2.19.3 |

Metadata-service auth is DISABLED in this quickstart: GMS accepts
unauthenticated requests on :8080 (verified via `/api/graphql`). No personal
access token is needed for local work.

## Sample data

```bash
DATAHUB_GMS_URL=http://localhost:8080 $DH docker ingest-sample-data
```

Notes:

- The command needs GMS connection config. Either export `DATAHUB_GMS_URL`
  as above or run `datahub init` once to create `~/.datahubenv`; with
  neither it fails with "No ~/.datahubenv file found".
- It runs two pipelines. The main one writes 103 events (7 datasets incl.
  `SampleHiveDataset`, `SampleKafkaDataset`, `SampleHdfsDataset`,
  `fct_users_created/deleted`, `logging_events`, an s3 backup dataset, plus
  charts/dashboards and lineage). The second pipeline ends with a "No
  metadata was produced by the source" warning and 2 events — expected, not
  a failure.
- Search indexing is async; datasets appear in search/UI a few seconds after
  ingestion.
- Newer alternative the quickstart banner suggests:
  `datahub init` then `datahub datapack load showcase-ecommerce` (richer
  demo pack; not required for this project).

Verify datasets exist:

```bash
curl -s -X POST http://localhost:8080/api/graphql \
  -H 'Content-Type: application/json' \
  -d '{"query":"{ search(input: {type: DATASET, query: \"*\", start: 0, count: 30}) { total searchResults { entity { urn } } } }"}'
```

## MCP server

Official server, stdio transport, run on demand via uvx (uv is installed at
`~/.local/bin/uv`):

```bash
DATAHUB_GMS_URL=http://localhost:8080 DATAHUB_GMS_TOKEN= \
  uvx mcp-server-datahub@latest
```

- `DATAHUB_GMS_URL` — required, point at local GMS.
- `DATAHUB_GMS_TOKEN` — required by the docs for real deployments; for this
  auth-disabled quickstart an empty string works.
- Tools exposed (v3.4.5 against v1.5.0.6): `search`, `get_lineage`,
  `get_dataset_queries`, `get_entities`, `list_schema_fields`,
  `get_lineage_paths_between`. Two document tools (`search_documents`,
  `grep_documents`) are auto-hidden when the catalog has no documents.

Smoke test (initialize + tools/list proof, output in
[mcp-smoke.md](mcp-smoke.md)):

```bash
cd ~/Projects/datahub-rail-agent
DATAHUB_GMS_URL=http://localhost:8080 DATAHUB_GMS_TOKEN= \
  .dhenv/bin/python scripts/mcp_smoke.py
```

## Resource notes

Docker Desktop is allotted 10 CPUs / ~8 GB RAM on this machine; the full
quickstart stack (6 containers) runs comfortably within that.
