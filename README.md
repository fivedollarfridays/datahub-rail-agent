# datahub-rail-agent

A data-rail health monitor agent for DataHub's context graph. It runs capture-based liveness probes over dataset freshness and lineage, applies fail-loud classification so silent outages surface as incidents instead of green dashboards, and produces delta-aware alerts that fire on meaningful change rather than raw thresholds. When something breaks, it walks the lineage graph to triage root cause and generates owner-addressed incident reports. It also detects schema and contract drift and emits PR-ready fix artifacts. Integration with DataHub is via the DataHub MCP Server.

## Hackathon entry

Built for **Build with DataHub: The Agent Hackathon** (Devpost).

## Prior inspiration disclosure

The design applies a capture-reliability doctrine battle-tested in a private ops system (capture-based liveness, fail-loud on outage, freshness verified before reporting state). All code in this repository is newly written during the submission period.

## License

Apache-2.0
