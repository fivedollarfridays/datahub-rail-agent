## Incident Report

### What Broke
Dataset: **orders_archive**
URN: `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)`
Owner(s): @data-eng

### Evidence
- **Failing probe**: `freshness`
- **Probe**: Dataset is stale: last modified 45 days ago (SLA: 24h)
- **Last modified**: 2026-06-18 20:18 UTC (45 days old)

### Root-Cause Candidate
Dataset: **orders_archive** — is the failure
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
| `gms:datasetProperties.lastModified` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)` | 2026-08-02T20:21:02.634620+00:00 |
| `gms:upstreamLineage` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)` | 2026-08-02T20:21:02.646027+00:00 |
| `mcp:get_lineage` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)` | 2026-08-02T20:21:02.892223+00:00 |
| `mcp:get_entities` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)` | 2026-08-02T20:21:04.674104+00:00 |

---
*All facts in this report sourced from DataHub context graph reads.*
