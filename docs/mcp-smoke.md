# MCP smoke test — mcp-server-datahub against local quickstart

Date: 2026-08-02. Proof that the official DataHub MCP server runs against the
local `datahub docker quickstart` instance and answers `initialize` and
`tools/list`.

## Server under test

- `mcp-server-datahub` v3.4.5, launched via `uvx mcp-server-datahub@latest`
  (stdio transport)
- Target: local quickstart GMS at `http://localhost:8080` (DataHub v1.5.0.6)
- No token required: the local quickstart runs with metadata-service auth
  disabled, so `DATAHUB_GMS_TOKEN` is set to an empty string

## Command

Test client is [`scripts/mcp_smoke.py`](../scripts/mcp_smoke.py), a minimal
client using the `mcp` Python package (installed in the repo's `.dhenv` venv).
It spawns the server over stdio, performs `initialize`, then `tools/list`.

```bash
cd ~/Projects/datahub-rail-agent
DATAHUB_GMS_URL=http://localhost:8080 DATAHUB_GMS_TOKEN= \
  .dhenv/bin/python scripts/mcp_smoke.py
```

## Output

```text
initialize OK: server=datahub v3.4.5 protocol=2025-11-25
tools/list OK: 6 tools
  - search: Search across DataHub entities using structured full-text search.
  - get_lineage: Get upstream or downstream lineage for any entity, including datasets, schemaFields, dashboards, cha
  - get_dataset_queries: Get SQL queries associated with a dataset or column to understand usage patterns.
  - get_entities: Get detailed information about one or more entities by their DataHub URNs.
  - list_schema_fields: List schema fields for a dataset, with optional keyword filtering and pagination.
  - get_lineage_paths_between: Get detailed lineage path(s) between two specific entities or columns.
```

## Notes

- Two additional tools (`search_documents`, `grep_documents`) exist but are
  filtered out by the server at startup because the local catalog contains no
  documents (server log: "No documents in catalog, filtering out tools").
- The server verified connectivity to GMS during startup (it queries the
  document count and detects server version 1.5.0.6, is_cloud=False), so a
  passing `tools/list` also proves live connectivity to the quickstart, not
  just a spawned process.
