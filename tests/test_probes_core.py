"""Probe engine: core classes and registry."""
import pytest


# Cycle 1: Probe base class
def test_probe_result_pass():
    """Probe result with pass status."""
    from datahub_rail.probes import ProbeResult

    result = ProbeResult(status="pass", message="Dataset is fresh")
    assert result.status == "pass"
    assert result.message == "Dataset is fresh"


def test_probe_result_warn():
    """Probe result with warn status."""
    from datahub_rail.probes import ProbeResult

    result = ProbeResult(status="warn", message="No freshness data available")
    assert result.status == "warn"
    assert result.message == "No freshness data available"


def test_probe_result_fail():
    """Probe result with fail status."""
    from datahub_rail.probes import ProbeResult

    result = ProbeResult(status="fail", message="Dataset is stale (45 days old)")
    assert result.status == "fail"
    assert result.message == "Dataset is stale (45 days old)"


# Cycle 2: FreshnessProbe detects stale datasets
@pytest.mark.asyncio
async def test_freshness_probe_healthy_dataset():
    """FreshnessProbe passes for fresh dataset."""
    from datahub_rail.probes import FreshnessProbe
    from datahub_rail.types import Freshness
    from datetime import datetime, timezone

    # Mock client that returns fresh dataset (current timestamp)
    class MockClient:
        async def get_freshness(self, urn: str) -> Freshness:
            now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            return Freshness(
                urn=urn,
                last_modified=now_ms,
                is_stale=False,
                expected_frequency=86400,  # 1 day in seconds
            )

    probe = FreshnessProbe(sla_hours=24)
    result = await probe.check(MockClient(), "urn:test")

    assert result.status == "pass"
    assert "fresh" in result.message.lower()


@pytest.mark.asyncio
async def test_freshness_probe_stale_dataset():
    """FreshnessProbe fails for stale dataset."""
    from datahub_rail.probes import FreshnessProbe
    from datahub_rail.types import Freshness
    from datetime import datetime, timezone, timedelta

    # Mock client that returns stale dataset (45 days old)
    old_timestamp = int((datetime.now(timezone.utc) - timedelta(days=45)).timestamp() * 1000)

    class MockClient:
        async def get_freshness(self, urn: str) -> Freshness:
            return Freshness(
                urn=urn,
                last_modified=old_timestamp,
                is_stale=True,
                expected_frequency=86400,
            )

    probe = FreshnessProbe(sla_hours=24)
    result = await probe.check(MockClient(), "urn:test")

    assert result.status == "fail"
    assert "stale" in result.message.lower()
    assert "45" in result.message or "days" in result.message.lower()


# Cycle 3: LineageProbe detects broken upstream
@pytest.mark.asyncio
async def test_lineage_probe_healthy():
    """LineageProbe passes when all upstream edges exist."""
    from datahub_rail.probes import LineageProbe
    from datahub_rail.types import LineageResult

    class MockClient:
        async def walk_upstream(self, urn: str, hops: int = 1) -> LineageResult:
            return LineageResult(
                urn=urn,
                upstream=[
                    {"urn": "urn:upstream1", "name": "source_table", "platform": "postgres"}
                ],
                downstream=[],
            )

    probe = LineageProbe()
    result = await probe.check(MockClient(), "urn:test")

    assert result.status == "pass"
    assert "lineage" in result.message.lower()


@pytest.mark.asyncio
async def test_lineage_probe_broken():
    """LineageProbe fails when upstream is missing."""
    from datahub_rail.probes import LineageProbe
    from datahub_rail.types import LineageResult

    class MockClient:
        async def walk_upstream(self, urn: str, hops: int = 1) -> LineageResult:
            # Simulates broken lineage: no upstream nodes
            return LineageResult(
                urn=urn,
                upstream=[],
                downstream=[],
            )

    probe = LineageProbe()
    result = await probe.check(MockClient(), "urn:test")

    assert result.status == "fail"
    assert "missing" in result.message.lower() or "broken" in result.message.lower()


# Cycle 4: SchemaProbe detects type drift
@pytest.mark.asyncio
async def test_schema_probe_healthy():
    """SchemaProbe passes when schema matches expected types."""
    from datahub_rail.probes import SchemaProbe
    from datahub_rail.types import SchemaMetadata

    class MockClient:
        async def fetch_schema(self, urn: str) -> SchemaMetadata:
            return SchemaMetadata(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint", "description": "ID"},
                    {"field_path": "amount", "type": "decimal(12,2)", "description": "Amount"},
                ],
                description="Valid schema",
            )

    probe = SchemaProbe()
    result = await probe.check(MockClient(), "urn:test")

    assert result.status == "pass"


@pytest.mark.asyncio
async def test_schema_probe_drift():
    """SchemaProbe fails when field type changes (int vs decimal)."""
    from datahub_rail.probes import SchemaProbe
    from datahub_rail.types import SchemaMetadata

    class MockClient:
        async def fetch_schema(self, urn: str) -> SchemaMetadata:
            return SchemaMetadata(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint", "description": "ID"},
                    {"field_path": "amount", "type": "int", "description": "Amount (type mismatch)"},
                ],
                description="Schema with drift",
            )

    probe = SchemaProbe(
        expected_fields={
            "amount": "decimal(12,2)",
        }
    )
    result = await probe.check(MockClient(), "urn:test")

    assert result.status == "fail"
    assert "drift" in result.message.lower() or "mismatch" in result.message.lower()
    assert "amount" in result.message.lower()


# Cycle 5: ProbeRegistry config-driven
def test_probe_registry_loads_config():
    """ProbeRegistry loads probes from config."""
    from datahub_rail.probes import ProbeRegistry

    config = {
        "probes": [
            {"name": "freshness", "type": "freshness", "params": {"sla_hours": 24}},
            {"name": "lineage", "type": "lineage", "params": {}},
            {"name": "schema", "type": "schema", "params": {}},
        ]
    }

    registry = ProbeRegistry(config)
    assert len(registry.probes) == 3
    assert "freshness" in registry.probes
    assert "lineage" in registry.probes
    assert "schema" in registry.probes


def test_probe_registry_creates_correct_probe_types():
    """ProbeRegistry creates correct probe instances."""
    from datahub_rail.probes import ProbeRegistry

    config = {
        "probes": [
            {"name": "my_freshness", "type": "freshness", "params": {"sla_hours": 48}},
        ]
    }

    registry = ProbeRegistry(config)
    probe = registry.probes["my_freshness"]

    # Check that FreshnessProbe was created with correct params
    assert hasattr(probe, "sla_hours")
    assert probe.sla_hours == 48
