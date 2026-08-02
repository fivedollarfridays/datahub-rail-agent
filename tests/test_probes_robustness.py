"""Probe robustness: exception handling and blind states."""
import pytest


# Cycle 6: Never-raise contract (exceptions become fail with message)
@pytest.mark.asyncio
async def test_freshness_probe_never_raises_on_client_error():
    """FreshnessProbe catches client errors and returns fail status."""
    from datahub_rail.probes import FreshnessProbe

    class BrokenClient:
        async def get_freshness(self, urn: str):
            raise RuntimeError("MCP server is down")

    probe = FreshnessProbe(sla_hours=24)
    result = await probe.check(BrokenClient(), "urn:test")

    # Must return fail status, never raise
    assert result.status == "fail"
    assert "MCP" in result.message or "down" in result.message or "error" in result.message.lower()


@pytest.mark.asyncio
async def test_lineage_probe_never_raises_on_client_error():
    """LineageProbe catches client errors and returns fail status."""
    from datahub_rail.probes import LineageProbe

    class BrokenClient:
        async def walk_upstream(self, urn: str, hops: int = 1):
            raise ConnectionError("Cannot reach MCP server")

    probe = LineageProbe()
    result = await probe.check(BrokenClient(), "urn:test")

    assert result.status == "fail"
    # Message should name the cause of the failure
    assert "mcp" in result.message.lower() or "reach" in result.message.lower()


@pytest.mark.asyncio
async def test_schema_probe_never_raises_on_client_error():
    """SchemaProbe catches client errors and returns fail status."""
    from datahub_rail.probes import SchemaProbe

    class BrokenClient:
        async def fetch_schema(self, urn: str):
            raise ValueError("Invalid URN format")

    probe = SchemaProbe()
    result = await probe.check(BrokenClient(), "urn:test")

    assert result.status == "fail"
    assert "error" in result.message.lower() or "invalid" in result.message.lower()


# Cycle 7: Blind states (MCP down, no data) → loud warns
@pytest.mark.asyncio
async def test_lineage_probe_warns_on_missing_upstream():
    """LineageProbe warns loudly when no upstream data available."""
    from datahub_rail.probes import LineageProbe
    from datahub_rail.types import LineageResult

    class NoDataClient:
        async def walk_upstream(self, urn: str, hops: int = 1) -> LineageResult:
            # Simulates "watch blind" state: no upstream, no lineage metadata
            return LineageResult(
                urn=urn,
                upstream=[],
                downstream=[],
            )

    probe = LineageProbe()
    result = await probe.check(NoDataClient(), "urn:test")

    # Must warn loudly about the blind state, name the cause
    assert result.status == "fail"
    assert "missing" in result.message.lower() or "broken" in result.message.lower()
    # Message should be explicit about not having lineage
    assert "lineage" in result.message.lower()


@pytest.mark.asyncio
async def test_lineage_probe_detects_watch_blind_state():
    """LineageProbe detects watch-blind state (no lineage data at all)."""
    from datahub_rail.probes import LineageProbe
    from datahub_rail.types import LineageResult

    class WatchBlindClient:
        async def walk_upstream(self, urn: str, hops: int = 1) -> LineageResult:
            # No metadata available from MCP
            return LineageResult(
                urn=urn,
                upstream=[],  # Empty: blind state
                downstream=[],
            )

    probe = LineageProbe()
    result = await probe.check(WatchBlindClient(), "urn:test")

    # Loud warn: must name the blind state
    assert result.status == "fail"
    assert "missing" in result.message.lower() or "no upstream" in result.message.lower()


# Cycle 8: End-to-end with registry and multiple probes
@pytest.mark.asyncio
async def test_registry_checks_all_probes():
    """ProbeRegistry runs all probes and returns results for each."""
    from datahub_rail.probes import ProbeRegistry
    from datahub_rail.types import Freshness, LineageResult, SchemaMetadata
    from datetime import datetime, timezone

    class MockClient:
        async def get_freshness(self, urn: str) -> Freshness:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            return Freshness(
                urn=urn,
                last_modified=now_ms,
                is_stale=False,
                expected_frequency=86400,
            )

        async def walk_upstream(self, urn: str, hops: int = 1) -> LineageResult:
            return LineageResult(
                urn=urn,
                upstream=[{"urn": "urn:up", "name": "source", "platform": "postgres"}],
                downstream=[],
            )

        async def fetch_schema(self, urn: str) -> SchemaMetadata:
            return SchemaMetadata(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint", "description": "ID"},
                ],
                description="Test schema",
            )

    config = {
        "probes": [
            {"name": "freshness", "type": "freshness", "params": {"sla_hours": 24}},
            {"name": "lineage", "type": "lineage", "params": {}},
            {"name": "schema", "type": "schema", "params": {}},
        ]
    }

    registry = ProbeRegistry(config)
    results = await registry.check_dataset(MockClient(), "urn:test")

    assert len(results) == 3
    assert results["freshness"].status == "pass"
    assert results["lineage"].status == "pass"
    assert results["schema"].status == "pass"


@pytest.mark.asyncio
async def test_registry_handles_probe_failures():
    """ProbeRegistry gracefully handles probes that fail."""
    from datahub_rail.probes import ProbeRegistry
    from datahub_rail.types import Freshness
    from datetime import datetime, timezone, timedelta

    old_timestamp = int((datetime.now(timezone.utc) - timedelta(days=45)).timestamp() * 1000)

    class PartiallyBrokenClient:
        async def get_freshness(self, urn: str) -> Freshness:
            # Stale dataset
            return Freshness(
                urn=urn,
                last_modified=old_timestamp,
                is_stale=True,
                expected_frequency=86400,
            )

        async def walk_upstream(self, urn: str, hops: int = 1):
            # Broken connection
            raise RuntimeError("MCP server down")

        async def fetch_schema(self, urn: str):
            raise RuntimeError("Schema unavailable")

    config = {
        "probes": [
            {"name": "freshness", "type": "freshness", "params": {"sla_hours": 24}},
            {"name": "lineage", "type": "lineage", "params": {}},
            {"name": "schema", "type": "schema", "params": {}},
        ]
    }

    registry = ProbeRegistry(config)
    results = await registry.check_dataset(PartiallyBrokenClient(), "urn:test")

    # All probes must return results (never raise)
    assert len(results) == 3
    assert results["freshness"].status == "fail"  # Stale
    assert results["lineage"].status == "fail"  # Exception → fail
    assert results["schema"].status == "fail"  # Exception → fail

    # Messages must be informative
    assert len(results["lineage"].message) > 0
    assert len(results["schema"].message) > 0
