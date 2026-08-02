"""The schema-drift diff must apply cleanly to the downstream contract file.

A "PR-ready" artifact that `git apply` rejects is not PR-ready. These tests
generate the diff against a real contract file and apply it for real.
"""
import subprocess
from pathlib import Path

import pytest

from datahub_rail.drift_artifacts import DriftArtifactGenerator

CONTRACT = """fields:
  - field_path: id
    type: bigint
  - field_path: amount
    type: decimal(12,2)
"""

DRIFT = {
    "field_name": "amount",
    "expected_type": "decimal(12,2)",
    "actual_type": "int",
    "upstream_dataset": "transactions",
    "downstream_dataset": "transactions_warehouse",
    "upstream_owner": "data-eng",
}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True)


@pytest.mark.asyncio
async def test_generated_diff_applies_to_the_contract_file(tmp_path):
    """git apply accepts the generated diff against the seeded contract."""
    repo = tmp_path
    _git(repo, "init", "-q")
    contract = repo / "contracts" / "transactions_warehouse.schema.yaml"
    contract.parent.mkdir(parents=True)
    contract.write_text(CONTRACT)

    outbox = repo / "outbox"
    diff_path = await DriftArtifactGenerator().generate_diff_file(
        {**DRIFT, "contract_path": "contracts/transactions_warehouse.schema.yaml",
         "contract_text": CONTRACT},
        outbox,
    )

    check = _git(repo, "apply", "--check", str(diff_path))
    assert check.returncode == 0, check.stderr


@pytest.mark.asyncio
async def test_applying_the_diff_updates_the_declared_type(tmp_path):
    """After applying, the contract expects the upstream's actual type."""
    repo = tmp_path
    _git(repo, "init", "-q")
    contract = repo / "contracts" / "transactions_warehouse.schema.yaml"
    contract.parent.mkdir(parents=True)
    contract.write_text(CONTRACT)

    diff_path = await DriftArtifactGenerator().generate_diff_file(
        {**DRIFT, "contract_path": "contracts/transactions_warehouse.schema.yaml",
         "contract_text": CONTRACT},
        repo / "outbox",
    )
    applied = _git(repo, "apply", str(diff_path))
    assert applied.returncode == 0, applied.stderr

    updated = contract.read_text()
    assert "type: int" in updated
    assert "decimal(12,2)" not in updated
    assert "field_path: id" in updated


@pytest.mark.asyncio
async def test_diff_targets_the_contract_path(tmp_path):
    """Diff headers name the real contract file, not an invented one."""
    diff_path = await DriftArtifactGenerator().generate_diff_file(
        {**DRIFT, "contract_path": "contracts/transactions_warehouse.schema.yaml",
         "contract_text": CONTRACT},
        tmp_path / "outbox",
    )

    text = diff_path.read_text()
    assert "a/contracts/transactions_warehouse.schema.yaml" in text
    assert "b/contracts/transactions_warehouse.schema.yaml" in text


def test_repo_ships_the_downstream_contract_file():
    """The contract the patch targets is committed for judges to apply."""
    contract = Path(__file__).resolve().parent.parent / "contracts" / "transactions_warehouse.schema.yaml"

    assert contract.exists()
    assert "decimal(12,2)" in contract.read_text()
