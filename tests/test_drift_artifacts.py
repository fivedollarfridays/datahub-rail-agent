"""Tests for contract-drift fix artifact generation."""
import pytest
from pathlib import Path
from datahub_rail.drift_artifacts import DriftArtifactGenerator


@pytest.fixture
def temp_outbox(tmp_path):
    """Temporary outbox directory."""
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    return outbox


@pytest.mark.asyncio
async def test_generate_schema_patch_artifact(temp_outbox):
    """Schema drift → concrete patch artifact."""
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

    patch_file = await generator.generate_patch_artifact(drift_info, temp_outbox)

    # Verify patch file created
    assert patch_file.exists()
    content = patch_file.read_text()

    # Verify patch contains expected changes
    assert "amount" in content
    assert "decimal(12,2)" in content or "decimal" in content


@pytest.mark.asyncio
async def test_generate_diff_file(temp_outbox):
    """Schema drift → diff-formatted change file."""
    generator = DriftArtifactGenerator()

    drift_info = {
        "field_name": "amount",
        "expected_type": "decimal(12,2)",
        "actual_type": "int",
        "downstream_dataset": "transactions_warehouse",
        "downstream_urn": "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.transactions_warehouse,PROD)",
    }

    diff_file = await generator.generate_diff_file(drift_info, temp_outbox)

    # Verify diff file created
    assert diff_file.exists()
    content = diff_file.read_text()

    # Verify diff format (--- +++ or similar)
    assert "-" in content or "+" in content


@pytest.mark.asyncio
async def test_generate_commit_message(temp_outbox):
    """Schema drift → commit-message-ready summary."""
    generator = DriftArtifactGenerator()

    drift_info = {
        "field_name": "amount",
        "expected_type": "decimal(12,2)",
        "actual_type": "int",
        "downstream_dataset": "transactions_warehouse",
        "upstream_dataset": "transactions",
        "upstream_owner": "@data-eng",
    }

    msg_file = await generator.generate_commit_message(drift_info, temp_outbox)

    # Verify commit message file created
    assert msg_file.exists()
    content = msg_file.read_text()

    # Verify it's a valid commit message (has title + body)
    lines = content.strip().split("\n")
    assert len(lines) >= 1
    # First line should be title (short)
    assert len(lines[0]) <= 72


@pytest.mark.asyncio
async def test_patch_applies_to_seeded_config():
    """Artifact applies cleanly to the seeded downstream config."""
    generator = DriftArtifactGenerator()

    # Seeded downstream config (from seed_demo_estate)
    seeded_config = {
        "name": "transactions_warehouse",
        "platform": "postgres",
        "owner": "analytics",
        "fields": [
            {"field_path": "id", "type": "bigint"},
            {"field_path": "amount", "type": "decimal(12,2)"},
        ]
    }

    # Upstream schema (actual state)
    upstream_schema = {
        "fields": [
            {"field_path": "id", "type": "bigint"},
            {"field_path": "amount", "type": "int"},
        ]
    }

    # Apply patch
    result = await generator.apply_patch(seeded_config, upstream_schema)

    # After applying fix, should align with upstream
    assert result["fields"][1]["type"] == "int"


@pytest.mark.asyncio
async def test_full_artifact_pipeline(temp_outbox):
    """Full pipeline: detect drift → generate all artifacts."""
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

    # Generate all artifacts at once
    artifacts = await generator.generate_all_artifacts(drift_info, temp_outbox)

    # Verify all 3 artifacts generated
    assert "patch" in artifacts
    assert "diff" in artifacts
    assert "message" in artifacts

    # All should be Path objects and exist
    for artifact_type, artifact_path in artifacts.items():
        assert isinstance(artifact_path, Path)
        assert artifact_path.exists()
