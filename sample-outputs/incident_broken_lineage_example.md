## Incident Report

### What Broke
Dataset: **broken-lineage-dataset**
URN: `urn:li:dataset:(urn:li:dataPlatform:snowflake,raw.missing_edges,PROD)`
Owner(s): @analytics-team

### Evidence
- **Probe**: Dataset has no upstream dependencies (lineage missing or broken)
- **Last modified**: 1722595200 (unix timestamp)
- **Lineage path**: broken-lineage-dataset

### Root-Cause Candidate
Dataset: **broken-lineage-dataset**
Platform: snowflake
Distance from failure: 0 hops
Owner: @analytics-team

## Next Steps
1. Contact root-cause owner to investigate data pipeline
2. Check for recent pipeline changes or job failures
3. Validate upstream dependencies are operational

---
*All facts in this report sourced from DataHub context graph reads.*
