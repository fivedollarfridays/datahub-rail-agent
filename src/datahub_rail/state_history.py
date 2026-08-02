"""State history persistence: JSONL appending with bounded rotation."""
import json
from pathlib import Path
from datetime import datetime, timezone


class StateHistory:
    """Persist per-probe status history (JSONL) with bounded rotation."""

    def __init__(self, path: Path | str, max_entries: int = 1000):
        """Initialize history with path and max entry limit."""
        self.path = Path(path)
        self.max_entries = max_entries

    def append(
        self,
        dataset_urn: str,
        probe_name: str,
        status: str,
        message: str,
    ) -> None:
        """Append status entry to JSONL history with bounded rotation."""
        entry = {
            "dataset_urn": dataset_urn,
            "probe_name": probe_name,
            "status": status,
            "message": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Load existing entries
        entries = self.load()
        entries.append(entry)

        # Rotate: keep only newest max_entries
        if len(entries) > self.max_entries:
            entries = entries[-self.max_entries :]

        # Rewrite file with rotated entries
        with open(self.path, "w") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")

    def load(self) -> list[dict]:
        """Load all entries from history file."""
        if not self.path.exists():
            return []

        entries = []
        with open(self.path) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries


class StateDigest:
    """Render delta-aware digests: NEW / still-failing-day-N / recovered."""

    def __init__(self, path: Path | str):
        """Initialize digest reader."""
        self.path = Path(path)

    def render(self) -> str:
        """Render summary of state deltas (NEW / chronic / recovered)."""
        entries = self._load_entries()

        if not entries:
            return ""

        # Group by (dataset_urn, probe_name) and analyze each sequence
        groups = self._group_by_probe()
        lines = []

        for (dataset_urn, probe_name), sequence in sorted(groups.items()):
            summary = self._summarize_sequence(dataset_urn, probe_name, sequence)
            if summary:
                lines.append(summary)

        return "\n".join(lines)

    def _load_entries(self) -> list[dict]:
        """Load all history entries."""
        if not self.path.exists():
            return []

        entries = []
        with open(self.path) as f:
            for line in f:
                if line.strip():
                    entries.append(json.loads(line))
        return entries

    def _group_by_probe(self) -> dict:
        """Group entries by (dataset_urn, probe_name)."""
        entries = self._load_entries()
        groups = {}

        for entry in entries:
            key = (entry["dataset_urn"], entry["probe_name"])
            if key not in groups:
                groups[key] = []
            groups[key].append(entry)

        return groups

    def _summarize_sequence(self, dataset_urn: str, probe_name: str, sequence: list[dict]) -> str:
        """Summarize a sequence of probe results."""
        if not sequence:
            return ""

        latest = sequence[-1]
        status = latest["status"]
        message = latest["message"]

        if len(sequence) == 1:
            # First occurrence
            if status == "fail":
                return f"NEW: {dataset_urn} / {probe_name} — {message}"
            else:
                return f"PASS: {dataset_urn} / {probe_name} — {message}"

        # Check for transitions
        prev_status = sequence[-2]["status"]

        if status == "pass" and prev_status == "fail":
            # Recovered from failure
            return f"RECOVERED: {dataset_urn} / {probe_name} — {message}"

        elif status == "fail":
            # Chronic failure: count consecutive days
            consecutive_days = self._count_consecutive_fails(sequence)
            return f"CHRONIC: {dataset_urn} / {probe_name} (day {consecutive_days}) — {message}"

        else:
            # Passing (not newly passing)
            return ""

    def _count_consecutive_fails(self, sequence: list[dict]) -> int:
        """Count consecutive days of failures from end of sequence."""
        count = 0
        for entry in reversed(sequence):
            if entry["status"] == "fail":
                count += 1
            else:
                break
        return count
