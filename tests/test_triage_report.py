"""Incident report rendering to markdown."""
from datahub_rail.incident_report import render_report


def test_render_incident_report():
    """Report includes what broke, evidence, root-cause, owners, next step."""
    report_data = {
        "failing_dataset": {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
            "name": "events",
            "owner": "analytics-team",
        },
        "root_cause": {
            "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
            "name": "events-raw",
            "platform": "kafka",
            "owner": "kafka-ops",
            "distance": 2,
        },
        "lineage_path": [
            {"name": "events-raw", "platform": "kafka"},
            {"name": "events", "platform": "snowflake"},
        ],
        "probe_message": "Dataset is stale: last modified 3 days ago (SLA: 24h)",
        "last_modified": 1722595200,
    }

    markdown = render_report(report_data)

    # Should include key sections
    assert "## Incident Report" in markdown
    assert "events" in markdown  # What broke
    assert "events-raw" in markdown  # Root cause
    assert "analytics-team" in markdown  # Owners
    assert "stale" in markdown  # Evidence (probe message)
    assert "## Next Steps" in markdown  # Suggested action


def test_render_report_with_multiple_owners():
    """Report mentions multiple owners if applicable."""
    report_data = {
        "failing_dataset": {
            "name": "analytics.events",
            "owner": "analytics-team, data-platform",
        },
        "root_cause": {
            "name": "events-raw",
            "owner": "kafka-ops",
            "distance": 2,
        },
        "lineage_path": [],
        "probe_message": "Connection timeout",
        "last_modified": None,
    }

    markdown = render_report(report_data)

    assert "@analytics-team" in markdown or "analytics-team" in markdown
    assert "@kafka-ops" in markdown or "kafka-ops" in markdown
