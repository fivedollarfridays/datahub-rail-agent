"""Probe engine: liveness/drift detection with fail-loud classification."""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
from abc import ABC, abstractmethod


@dataclass
class ProbeResult:
    """Result of a probe check: pass/warn/fail with message."""

    status: str  # "pass", "warn", or "fail"
    message: str  # Next action or root cause


class Probe(ABC):
    """Abstract base for all probes; never raises, returns pass/warn/fail."""

    @abstractmethod
    async def check(self, client, dataset_urn: str) -> ProbeResult:
        """Check a dataset. Always returns ProbeResult, never raises."""
        pass


class FreshnessProbe(Probe):
    """Freshness probe: capture-based via last_modified, never job heartbeat."""

    def __init__(self, sla_hours: int = 24):
        self.sla_hours = sla_hours

    async def check(self, client, dataset_urn: str) -> ProbeResult:
        """Check if dataset is fresh vs SLA."""
        try:
            freshness = await client.get_freshness(dataset_urn)

            # Calculate age in hours
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            age_ms = now_ms - freshness.last_modified
            age_hours = age_ms / (1000 * 3600)

            if age_hours > self.sla_hours:
                age_days = int(age_hours / 24)
                return ProbeResult(
                    status="fail",
                    message=f"Dataset is stale: last modified {age_days} days ago (SLA: {self.sla_hours}h)",
                )

            return ProbeResult(status="pass", message="Dataset is fresh")
        except Exception as e:
            return ProbeResult(
                status="fail",
                message=f"Failed to check freshness: {str(e)}",
            )


class LineageProbe(Probe):
    """Lineage probe: detects missing/broken upstream edges."""

    async def check(self, client, dataset_urn: str) -> ProbeResult:
        """Check if upstream lineage edges are intact."""
        try:
            lineage = await client.walk_upstream(dataset_urn, hops=1)

            if not lineage.upstream:
                return ProbeResult(
                    status="fail",
                    message="Dataset has no upstream dependencies (lineage missing or broken)",
                )

            return ProbeResult(status="pass", message="Lineage integrity verified")
        except Exception as e:
            return ProbeResult(
                status="fail",
                message=f"Failed to check lineage: {str(e)}",
            )


class SchemaProbe(Probe):
    """Schema probe: detects contract drift between upstream and downstream."""

    def __init__(self, expected_fields: Optional[dict] = None):
        self.expected_fields = expected_fields or {}

    async def check(self, client, dataset_urn: str) -> ProbeResult:
        """Check if schema matches expected types."""
        try:
            schema = await client.fetch_schema(dataset_urn)

            if not self.expected_fields:
                return ProbeResult(status="pass", message="Schema looks good")

            # Check each field for type drift
            for field_name, expected_type in self.expected_fields.items():
                for field in schema.fields:
                    if field["field_path"] == field_name:
                        actual_type = field["type"]
                        if actual_type != expected_type:
                            return ProbeResult(
                                status="fail",
                                message=f"Schema drift on '{field_name}': expected {expected_type}, got {actual_type}",
                            )
                        break
                else:
                    return ProbeResult(
                        status="fail",
                        message=f"Schema drift: expected field '{field_name}' not found",
                    )

            return ProbeResult(status="pass", message="Schema contract verified")
        except Exception as e:
            return ProbeResult(
                status="fail",
                message=f"Failed to check schema: {str(e)}",
            )


class ProbeRegistry:
    """Config-driven registry of probes."""

    def __init__(self, config: dict):
        self.config = config
        self.probes = {}
        self._load_probes()

    def _load_probes(self):
        """Load probes from config."""
        for probe_config in self.config.get("probes", []):
            name = probe_config["name"]
            probe_type = probe_config["type"]
            params = probe_config.get("params", {})

            probe = self._create_probe(probe_type, params)
            self.probes[name] = probe

    def _create_probe(self, probe_type: str, params: dict) -> Probe:
        """Factory method to create probe instances."""
        if probe_type == "freshness":
            return FreshnessProbe(**params)
        elif probe_type == "lineage":
            return LineageProbe(**params)
        elif probe_type == "schema":
            return SchemaProbe(**params)
        else:
            raise ValueError(f"Unknown probe type: {probe_type}")

    async def check_dataset(self, client, dataset_urn: str) -> dict:
        """Run all probes against a dataset."""
        results = {}
        for name, probe in self.probes.items():
            results[name] = await probe.check(client, dataset_urn)
        return results
