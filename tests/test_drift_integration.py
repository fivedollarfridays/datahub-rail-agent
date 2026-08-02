"""Integration: schema-drift detection → fix artifacts."""
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from datahub_rail.drift_artifacts import DriftArtifactGenerator
from datahub_rail.probes import SchemaProbe, ProbeResult


@pytest.mark.asyncio
async def test_schema_probe_detects_drift():
    """SchemaProbe detects schema-drift fault (seeded config)."""
    client = MagicMock()

    # Seeded schema: downstream expects decimal(12,2) for amount
    async def fetch_schema_side_effect(urn):
        if "transactions_warehouse" in urn:
            # Downstream: expects decimal
            return MagicMock(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint"},
                    {"field_path": "amount", "type": "decimal(12,2)"},
                ]
            )
        else:
            return MagicMock(urn=urn, fields=[])

    client.fetch_schema = AsyncMock(side_effect=fetch_schema_side_effect)

    # Probe configured for downstream's expected types
    probe = SchemaProbe(expected_fields={"amount": "decimal(12,2)", "id": "bigint"})

    # Actual upstream: amount is int (fault injected by seeder)
    # Mock as if fetch_schema returned the actual upstream state
    async def fetch_schema_upstream(urn):
        if "transactions_warehouse" in urn:
            return MagicMock(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint"},
                    {"field_path": "amount", "type": "int"},  # DRIFTED
                ]
            )
        return MagicMock(urn=urn, fields=[])

    client.fetch_schema = AsyncMock(side_effect=fetch_schema_upstream)

    # Run probe: should FAIL with drift message
    result = await probe.check(client, "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)")

    # Verify probe detected drift
    assert result.status == "fail"
    assert "amount" in result.message
    assert "int" in result.message or "drift" in result.message.lower()


@pytest.mark.asyncio
async def test_drift_artifact_generation(tmp_path):
    """Schema drift → generate patch + diff + commit message."""
    generator = DriftArtifactGenerator()

    drift_info = {
        "field_name": "amount",
        "expected_type": "decimal(12,2)",
        "actual_type": "int",
        "downstream_dataset": "transactions_warehouse",
        "downstream_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)",
        "upstream_dataset": "transactions",
        "upstream_owner": "@data-eng",
    }

    outbox = tmp_path / "outbox"
    artifacts = await generator.generate_all_artifacts(drift_info, outbox)

    # Verify all three artifacts generated
    assert len(artifacts) == 3
    assert artifacts["patch"].exists()
    assert artifacts["diff"].exists()
    assert artifacts["message"].exists()

    # Verify artifact content
    patch_content = artifacts["patch"].read_text()
    assert "amount" in patch_content
    assert "int" in patch_content

    diff_content = artifacts["diff"].read_text()
    assert "-" in diff_content
    assert "+" in diff_content

    msg_content = artifacts["message"].read_text()
    assert "Fix schema drift" in msg_content or "schema drift" in msg_content.lower()
    assert "transactions_warehouse" in msg_content


@pytest.mark.asyncio
async def test_patch_applies_cleanly_to_seeded_schema(tmp_path):
    """Artifact applies to seeded downstream config without errors."""
    generator = DriftArtifactGenerator()

    # Seeded downstream config (from seed_demo_estate)
    seeded_downstream = {
        "name": "transactions_warehouse",
        "urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)",
        "platform": "postgres",
        "owner": "analytics",
        "fields": [
            {"field_path": "id", "type": "bigint", "description": "Transaction ID"},
            {"field_path": "amount", "type": "decimal(12,2)", "description": "Amount (expects decimal)"},
        ]
    }

    # Upstream actual schema
    upstream_schema = {
        "fields": [
            {"field_path": "id", "type": "bigint"},
            {"field_path": "amount", "type": "int"},  # DRIFTED
        ]
    }

    # Apply patch
    patched = await generator.apply_patch(seeded_downstream, upstream_schema)

    # Verify patched config now matches upstream types
    amount_field = next(f for f in patched["fields"] if f["field_path"] == "amount")
    assert amount_field["type"] == "int"  # Corrected to upstream type

    # Original metadata preserved
    assert patched["name"] == "transactions_warehouse"
    assert patched["owner"] == "analytics"


@pytest.mark.asyncio
async def test_full_drift_workflow(tmp_path):
    """Full workflow: detect drift → generate artifacts → verify patch applies."""
    client = MagicMock()

    # Client returns the seeded, drifted schemas
    async def fetch_schema_side_effect(urn):
        if "transactions_warehouse" in urn:
            return MagicMock(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint"},
                    {"field_path": "amount", "type": "int"},  # DRIFTED
                ]
            )
        elif "transactions" in urn and "warehouse" not in urn:
            return MagicMock(
                urn=urn,
                fields=[
                    {"field_path": "id", "type": "bigint"},
                    {"field_path": "amount", "type": "int"},
                ]
            )
        return MagicMock(urn=urn, fields=[])

    client.fetch_schema = AsyncMock(side_effect=fetch_schema_side_effect)

    # 1. Probe detects drift
    probe = SchemaProbe(expected_fields={"amount": "decimal(12,2)", "id": "bigint"})
    downstream_urn = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)"
    result = await probe.check(client, downstream_urn)

    assert result.status == "fail"
    assert "amount" in result.message

    # 2. Extract drift info and generate artifacts
    generator = DriftArtifactGenerator()

    drift_info = {
        "field_name": "amount",
        "expected_type": "decimal(12,2)",
        "actual_type": "int",
        "downstream_dataset": "transactions_warehouse",
        "downstream_urn": downstream_urn,
        "upstream_dataset": "transactions",
        "upstream_owner": "@data-eng",
    }

    outbox = tmp_path / "outbox"
    artifacts = await generator.generate_all_artifacts(drift_info, outbox)

    assert artifacts["patch"].exists()
    assert artifacts["diff"].exists()
    assert artifacts["message"].exists()

    # 3. Verify patch applies cleanly
    seeded_config = {
        "name": "transactions_warehouse",
        "fields": [
            {"field_path": "id", "type": "bigint"},
            {"field_path": "amount", "type": "decimal(12,2)"},
        ]
    }

    upstream_schema = {
        "fields": [
            {"field_path": "id", "type": "bigint"},
            {"field_path": "amount", "type": "int"},
        ]
    }

    patched_config = await generator.apply_patch(seeded_config, upstream_schema)
    amount_field = next(f for f in patched_config["fields"] if f["field_path"] == "amount")
    assert amount_field["type"] == "int"
