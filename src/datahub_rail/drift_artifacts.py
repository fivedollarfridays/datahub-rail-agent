"""Generate PR-ready fix artifacts for schema-drift faults."""
import difflib
from pathlib import Path

from .naming import slugify_dataset_name


def _default_contract(field_name: str, expected_type: str) -> str:
    """Fallback contract text when no committed contract file is supplied."""
    return f"fields:\n  - field_path: {field_name}\n    type: {expected_type}\n"


class DriftArtifactGenerator:
    """Generate patch, diff, and commit message for schema-drift faults."""

    async def generate_patch_artifact(self, drift_info: dict, outbox_dir: Path) -> Path:
        """Generate schema patch file that corrects downstream config."""
        outbox_dir.mkdir(parents=True, exist_ok=True)

        field_name = drift_info["field_name"]
        actual_type = drift_info["actual_type"]
        downstream_dataset = drift_info["downstream_dataset"]

        content = f"""# Schema Patch: {downstream_dataset}

## Issue
Field `{field_name}` in `{downstream_dataset}` expects `{drift_info["expected_type"]}` but upstream provides `{actual_type}`.

## Fix
Update downstream schema to match upstream type:

```yaml
fields:
  - field_path: {field_name}
    type: {actual_type}
```

## Applied By
Run this patch against your downstream dataset configuration.
"""

        patch_file = outbox_dir / f"schema_patch_{slugify_dataset_name(downstream_dataset)}.yaml"
        patch_file.write_text(content)
        return patch_file

    async def generate_diff_file(self, drift_info: dict, outbox_dir: Path) -> Path:
        """Generate a unified diff that `git apply` accepts.

        The diff is computed with difflib against the downstream contract
        text, so hunk headers and context are correct and the patch applies
        cleanly to the committed contract file.
        """
        outbox_dir.mkdir(parents=True, exist_ok=True)

        expected = drift_info["expected_type"]
        actual = drift_info["actual_type"]
        downstream = drift_info["downstream_dataset"]
        contract_path = drift_info.get(
            "contract_path", f"contracts/{downstream}.schema.yaml"
        )

        before = drift_info.get("contract_text")
        if before is None:
            before = _default_contract(drift_info["field_name"], expected)
        after = before.replace(f"type: {expected}", f"type: {actual}")

        diff_content = "".join(
            difflib.unified_diff(
                before.splitlines(keepends=True),
                after.splitlines(keepends=True),
                fromfile=f"a/{contract_path}",
                tofile=f"b/{contract_path}",
            )
        )

        diff_file = outbox_dir / f"schema_drift_{slugify_dataset_name(downstream)}.diff"
        diff_file.write_text(diff_content)
        return diff_file

    async def generate_commit_message(self, drift_info: dict, outbox_dir: Path) -> Path:
        """Generate commit-message-ready summary."""
        outbox_dir.mkdir(parents=True, exist_ok=True)

        field_name = drift_info["field_name"]
        downstream = drift_info["downstream_dataset"]
        upstream = drift_info["upstream_dataset"]
        upstream_owner = drift_info.get("upstream_owner", "upstream-team")
        expected = drift_info["expected_type"]
        actual = drift_info["actual_type"]

        msg_content = f"""Fix schema drift: {downstream} field '{field_name}' type mismatch

The downstream dataset {downstream} expects field '{field_name}' of type
{expected}, but the upstream {upstream} recently changed it to {actual}.

This patch corrects the downstream schema expectation to match the
upstream type, aligning the contract.

Upstream owner: {upstream_owner}
Fault class: schema-contract-drift
Detection method: SchemaProbe (expected vs actual type check)
"""

        msg_file = outbox_dir / f"commit_message_{slugify_dataset_name(downstream)}.txt"
        msg_file.write_text(msg_content)
        return msg_file

    async def apply_patch(self, downstream_config: dict, upstream_schema: dict) -> dict:
        """Apply patch: align downstream schema with upstream schema."""
        result = downstream_config.copy()
        result["fields"] = []

        upstream_fields = {f["field_path"]: f["type"] for f in upstream_schema.get("fields", [])}

        for field in downstream_config.get("fields", []):
            field_path = field["field_path"]
            # Use upstream type if available, else keep original
            actual_type = upstream_fields.get(field_path, field["type"])
            result["fields"].append({
                **field,
                "type": actual_type,
            })

        return result

    async def generate_all_artifacts(self, drift_info: dict, outbox_dir: Path) -> dict:
        """Generate all three artifacts: patch, diff, commit message."""
        outbox_dir = Path(outbox_dir)
        outbox_dir.mkdir(parents=True, exist_ok=True)

        patch = await self.generate_patch_artifact(drift_info, outbox_dir)
        diff = await self.generate_diff_file(drift_info, outbox_dir)
        message = await self.generate_commit_message(drift_info, outbox_dir)

        return {
            "patch": patch,
            "diff": diff,
            "message": message,
        }
