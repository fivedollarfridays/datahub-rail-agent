"""Drift artifact filenames carry the same path-separator hazard as triage.

``agent._write_drift_artifacts`` derives the downstream name from the failing
dataset (``f"{entry['name']}_warehouse"`` by default), so a path-shaped
dataset name propagates straight into three more outbox writes.
"""
import pytest

from datahub_rail.drift_artifacts import DriftArtifactGenerator
from datahub_rail.naming import slugify_dataset_name


def _drift(downstream):
    return {
        "field_name": "amount",
        "expected_type": "decimal(12,2)",
        "actual_type": "int",
        "upstream_dataset": "data/voice/fingerprint.json",
        "downstream_dataset": downstream,
        "upstream_owner": "ops",
        "contract_path": "contracts/voice.schema.yaml",
        "contract_text": "fields:\n  - field_path: amount\n    type: decimal(12,2)\n",
    }


@pytest.mark.asyncio
async def test_path_like_downstream_writes_flat_artifacts(tmp_path):
    """All three artifacts land flat in the outbox, no nested dirs."""
    outbox = tmp_path / "outbox"

    artifacts = await DriftArtifactGenerator().generate_all_artifacts(
        _drift("data/voice/fingerprint.json_warehouse"), outbox
    )

    assert set(artifacts) == {"patch", "diff", "message"}
    for path in artifacts.values():
        assert path.parent == outbox, f"{path} must be flat in outbox"
        assert path.exists()
    assert not [p for p in outbox.iterdir() if p.is_dir()], "no directories created"

    names = sorted(p.name for p in outbox.iterdir())
    assert names == [
        "commit_message_data-voice-fingerprint.json_warehouse.txt",
        "schema_drift_data-voice-fingerprint.json_warehouse.diff",
        "schema_patch_data-voice-fingerprint.json_warehouse.yaml",
    ]


@pytest.mark.asyncio
async def test_flat_downstream_filenames_are_byte_identical(tmp_path):
    """The committed demo artifact names must not move."""
    outbox = tmp_path / "outbox"

    await DriftArtifactGenerator().generate_all_artifacts(
        _drift("transactions_warehouse"), outbox
    )

    assert sorted(p.name for p in outbox.iterdir()) == [
        "commit_message_transactions_warehouse.txt",
        "schema_drift_transactions_warehouse.diff",
        "schema_patch_transactions_warehouse.yaml",
    ]


@pytest.mark.asyncio
async def test_diff_body_keeps_the_real_contract_path(tmp_path):
    """Slugging is for filenames only — `git apply` needs the true path."""
    outbox = tmp_path / "outbox"

    artifacts = await DriftArtifactGenerator().generate_all_artifacts(
        _drift("data/voice/fingerprint.json_warehouse"), outbox
    )

    body = artifacts["diff"].read_text()
    assert "a/contracts/voice.schema.yaml" in body
    assert "b/contracts/voice.schema.yaml" in body


@pytest.mark.parametrize(
    "name,expected",
    [
        ("demo.public.orders_archive", "demo.public.orders_archive"),
        ("transactions_warehouse", "transactions_warehouse"),
        ("health-history", "health-history"),
        ("a--b", "a--b"),
        ("data/voice/fingerprint.json", "data-voice-fingerprint.json"),
        ("data\\voice\\fp.json", "data-voice-fp.json"),
        ("data//voice", "data-voice"),
        ("has space", "has-space"),
        ("a/../b", "a-..-b"),
        ("", "dataset"),
        ("///", "dataset"),
    ],
)
def test_slugify_cases(name, expected):
    """Safe names pass through untouched; unsafe runs collapse to one dash."""
    assert slugify_dataset_name(name) == expected


def test_slugify_caps_length_without_collision():
    """Overlong names are truncated but stay distinct from each other."""
    long_a = "data/" + "x" * 400 + "/a.json"
    long_b = "data/" + "x" * 400 + "/b.json"

    slug_a = slugify_dataset_name(long_a)
    slug_b = slugify_dataset_name(long_b)

    assert len(slug_a) <= 120
    assert "/" not in slug_a
    assert slug_a != slug_b
