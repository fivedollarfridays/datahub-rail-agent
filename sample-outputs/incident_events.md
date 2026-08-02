## Incident Report

### What Broke
Dataset: **events**
URN: `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)`
Owner(s): @data-eng

### Evidence
- **Failing probe**: `lineage_integrity`
- **Probe**: Broken lineage: declared upstream 'raw_events_old' missing from the graph
- **Last modified**: 2026-08-02 20:18 UTC (0 days old)

### Root-Cause Candidate
Dataset: **events** — is the failure
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
| `gms:datasetProperties.lastModified` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)` | 2026-08-02T20:21:02.352317+00:00 |
| `gms:upstreamLineage` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)` | 2026-08-02T20:21:02.363926+00:00 |
| `mcp:get_lineage` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)` | 2026-08-02T20:21:02.616621+00:00 |
| `mcp:get_entities` | `urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.events,PROD)` | 2026-08-02T20:21:04.113351+00:00 |

---
*All facts in this report sourced from DataHub context graph reads.*
