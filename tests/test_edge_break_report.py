"""Rendering the edge-break callout, and proving the default report is unmoved.

The callout has to be impossible to skim past: it names both timestamps and
says, in the report itself, that the producer is not the suspect. Equally
important is the negative case — a report with no edge-break finding must
render byte-for-byte what it rendered before this section existed, because
the committed sample-outputs/ are what judges compare against.
"""
from pathlib import Path

from datahub_rail.incident_report import render_report

HOUR_MS = 3600 * 1000
NOW_MS = 1_800_000_000_000

SAMPLES = Path(__file__).resolve().parent.parent / "sample-outputs"

FINDING = {
    "failing": {
        "name": "daily_digest",
        "last_modified": NOW_MS - 9 * 24 * HOUR_MS,
        "age_hours": 9 * 24,
    },
    "upstreams": [
        {
            "name": "planner_runs",
            "last_modified": NOW_MS - 1 * HOUR_MS,
            "age_hours": 1,
        }
    ],
    "sla_hours": 24,
    "gap_hours": 9 * 24 - 1,
}

BASE_DATA = {
    "failing_dataset": {"urn": "urn:x", "name": "daily_digest", "owner": "ops"},
    "root_cause": {"name": "planner_runs", "platform": "postgres", "distance": 1},
    "probe_name": "freshness",
    "probe_message": "Dataset is stale: last modified 9 days ago (SLA: 24h)",
    "lineage_path": [{"name": "planner_runs", "platform": "postgres"}],
}


def test_callout_names_both_timestamps_and_absolves_the_producer():
    """The block shows output and producer capture times and calls the edge."""
    markdown = render_report({**BASE_DATA, "edge_break": FINDING})

    assert "### Producer Healthy, Delivery Broken" in markdown
    assert "daily_digest" in markdown and "planner_runs" in markdown
    assert "216h" in markdown  # output age
    assert "1h" in markdown  # producer age
    assert "not the scheduler" in markdown
    assert "edge" in markdown


def test_callout_precedes_the_root_cause_candidate():
    """It must land before the section it corrects, or it gets skimmed past."""
    markdown = render_report({**BASE_DATA, "edge_break": FINDING})

    assert markdown.index("### Producer Healthy, Delivery Broken") < markdown.index(
        "### Root-Cause Candidate"
    )


def test_report_without_a_finding_is_byte_identical_to_the_shipped_layout():
    """No finding, no new bytes: the committed demo artifacts cannot move."""
    markdown = render_report(BASE_DATA)

    assert markdown == (
        "## Incident Report\n"
        "\n"
        "### What Broke\n"
        "Dataset: **daily_digest**\n"
        "URN: `urn:x`\n"
        "Owner(s): @ops\n"
        "\n"
        "### Evidence\n"
        "- **Failing probe**: `freshness`\n"
        "- **Probe**: Dataset is stale: last modified 9 days ago (SLA: 24h)\n"
        "- **Lineage path**: planner_runs\n"
        "\n"
        "### Root-Cause Candidate\n"
        "Dataset: **planner_runs**\n"
        "Platform: postgres\n"
        "Distance from failure: 1 hops\n"
        "\n"
        "## Next Steps\n"
        "1. Contact root-cause owner to investigate data pipeline\n"
        "2. Check for recent pipeline changes or job failures\n"
        "3. Validate upstream dependencies are operational\n"
        "\n"
        "---\n"
        "*All facts in this report sourced from DataHub context graph reads.*\n"
    )


def test_committed_sample_reports_carry_no_callout():
    """The default demo estate does not trip the callout — samples stay put."""
    reports = sorted(SAMPLES.glob("incident_*.md"))

    assert reports, "sample-outputs/ must contain incident reports to pin"
    for report in reports:
        assert "Producer Healthy" not in report.read_text(), report.name
