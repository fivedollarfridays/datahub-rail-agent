## Incident Report

### What Broke
Dataset: **stale-dataset**
URN: `urn:li:dataset:(urn:li:dataPlatform:snowflake,raw.events,PROD)`
Owner(s): @data-eng

### Evidence
- **Probe**: Dataset is stale: last modified 5 days ago (SLA: 24h)
- **Last modified**: 1722508800 (unix timestamp)
- **Lineage path**: source-events → stale-dataset

### Root-Cause Candidate
Dataset: **source-events**
Platform: kafka
Distance from failure: 1 hops
Owner: @kafka-ops

## Next Steps
1. Contact root-cause owner to investigate data pipeline
2. Check for recent pipeline changes or job failures
3. Validate upstream dependencies are operational

---
*All facts in this report sourced from DataHub context graph reads.*
