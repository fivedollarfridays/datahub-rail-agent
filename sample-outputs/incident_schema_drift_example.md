## Incident Report

### What Broke
Dataset: **schema-drift-dataset**
URN: `urn:li:dataset:(urn:li:dataPlatform:snowflake,raw.contract_broken,PROD)`
Owner(s): @data-platform

### Evidence
- **Probe**: Schema drift on 'user_id': expected BIGINT, got STRING
- **Last modified**: 1722595200 (unix timestamp)
- **Lineage path**: upstream-user-table → schema-drift-dataset

### Root-Cause Candidate
Dataset: **upstream-user-table**
Platform: postgres
Distance from failure: 1 hops
Owner: @user-service-team

## Next Steps
1. Contact root-cause owner to investigate data pipeline
2. Check for recent pipeline changes or job failures
3. Validate upstream dependencies are operational

---
*All facts in this report sourced from DataHub context graph reads.*
