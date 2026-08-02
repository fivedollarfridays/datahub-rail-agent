## Incident Report

### What Broke
Dataset: **transactions**
URN: `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)`
Owner(s): @data-eng

### Evidence
- **Failing probe**: `schema_contract`
- **Probe**: Schema drift on 'amount': expected decimal(12,2), got int
- **Last modified**: 2026-08-02 20:18 UTC (0 days old)

### Root-Cause Candidate
Dataset: **transactions** — is the failure
Platform: postgres
Distance from failure: 0 hops
Owner: @data-eng

## Next Steps
1. Contact root-cause owner to investigate data pipeline
2. Check for recent pipeline changes or job failures
3. Validate upstream dependencies are operational

### Provenance

| Fact source (tool) | Entity | Read at |
|---|---|---|
| `gms:datasetProperties.lastModified` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)` | 2026-08-02T20:21:02.907539+00:00 |
| `gms:upstreamLineage` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)` | 2026-08-02T20:21:02.916671+00:00 |
| `mcp:get_lineage` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)` | 2026-08-02T20:21:03.137089+00:00 |
| `mcp:list_schema_fields` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)` | 2026-08-02T20:21:03.382709+00:00 |
| `mcp:get_entities` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions,PROD)` | 2026-08-02T20:21:05.226596+00:00 |

---
*All facts in this report sourced from DataHub context graph reads.*
