"""Markdown rendering for incident reports.

Kept separate from the triage engine so the narrative layout can change
without touching graph-walk logic. Every value rendered here arrives from a
DataHub graph read performed by the engine.
"""
from datetime import datetime, timezone


def format_timestamp(epoch_ms: int) -> str:
    """Render an epoch-millisecond timestamp as a date plus age in days."""
    try:
        moment = datetime.fromtimestamp(int(epoch_ms) / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return str(epoch_ms)
    age_days = (datetime.now(timezone.utc) - moment).days
    return f"{moment.strftime('%Y-%m-%d %H:%M UTC')} ({age_days} days old)"


def render_what_broke(failing: dict) -> list[str]:
    """Render the What Broke section with owner @mentions."""
    lines = [
        "### What Broke",
        f"Dataset: **{failing.get('name', 'unknown')}**",
        f"URN: `{failing.get('urn', 'unknown')}`",
    ]
    if failing.get("owner"):
        mentions = ", ".join(f"@{o.strip()}" for o in failing["owner"].split(","))
        lines.append(f"Owner(s): {mentions}")
    lines.append("")
    return lines


def render_evidence(report_data: dict) -> list[str]:
    """Render the Evidence section from graph-read facts."""
    lines = ["### Evidence"]
    if report_data.get("probe_name"):
        lines.append(f"- **Failing probe**: `{report_data['probe_name']}`")
    lines.append(f"- **Probe**: {report_data.get('probe_message', 'Unknown issue')}")
    if report_data.get("last_modified"):
        lines.append(f"- **Last modified**: {format_timestamp(report_data['last_modified'])}")
    lineage_path = report_data.get("lineage_path", [])
    if lineage_path:
        path_str = " → ".join(n.get("name", "?") for n in lineage_path)
        lines.append(f"- **Lineage path**: {path_str}")
    lines.append("")
    return lines


def render_root_cause(root_cause: dict) -> list[str]:
    """Render the Root-Cause Candidate section."""
    suffix = " — is the failure" if root_cause.get("is_self") else ""
    lines = [
        "### Root-Cause Candidate",
        f"Dataset: **{root_cause.get('name', 'unknown')}**{suffix}",
        f"Platform: {root_cause.get('platform', 'unknown')}",
        f"Distance from failure: {root_cause.get('distance', '?')} hops",
    ]
    if root_cause.get("owner"):
        lines.append(f"Owner: @{root_cause['owner']}")
    lines.append("")
    return lines


def render_provenance(provenance: list) -> list[str]:
    """Render the provenance table: every claim traces to a graph read."""
    if not provenance:
        return []
    lines = [
        "### Provenance",
        "",
        "| Fact source (tool) | Entity | Read at |",
        "|---|---|---|",
    ]
    lines += [f"| `{e.tool}` | `{e.dataset_urn}` | {e.timestamp} |" for e in provenance]
    lines.append("")
    return lines


def render_report(report_data: dict) -> str:
    """Render a full incident report to markdown."""
    lines = ["## Incident Report", ""]
    lines += render_what_broke(report_data.get("failing_dataset", {}))
    lines += render_evidence(report_data)
    lines += render_root_cause(report_data.get("root_cause", {}))
    lines += [
        "## Next Steps",
        "1. Contact root-cause owner to investigate data pipeline",
        "2. Check for recent pipeline changes or job failures",
        "3. Validate upstream dependencies are operational",
        "",
    ]
    lines += render_provenance(report_data.get("provenance") or [])
    lines += [
        "---",
        "*All facts in this report sourced from DataHub context graph reads.*",
    ]
    return "\n".join(lines) + "\n"
