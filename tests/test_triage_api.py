"""Public API for incident report generation."""
import pytest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import AsyncMock, MagicMock
from datahub_rail.triage import TriageEngine


@pytest.mark.asyncio
async def test_generate_incident_report_saves_to_outbox():
    """Public API generates report and saves to outbox directory."""
    with TemporaryDirectory() as tmpdir:
        engine = TriageEngine()

        # Mock client
        client = MagicMock()
        client.walk_upstream = AsyncMock(return_value=MagicMock(
            urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
            upstream=[
                {
                    "urn": "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)",
                    "name": "events-raw",
                    "platform": "kafka",
                }
            ],
        ))
        client.get_freshness = AsyncMock(return_value=MagicMock(
            urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
            last_modified=1722595200,
            is_stale=True,
            expected_frequency=3600,
        ))

        # Generate report
        report = await engine.generate_incident_report(
            client,
            failing_dataset_urn="urn:li:dataset:(urn:li:dataPlatform:snowflake,analytics.events,PROD)",
            failing_dataset_name="events",
            dataset_owner="analytics-team",
            probe_name="freshness",
            probe_status="fail",
            probe_message="Dataset is stale: last modified 3 days ago (SLA: 24h)",
            outbox_dir=tmpdir,
        )

        # Verify report content
        assert "## Incident Report" in report
        assert "events" in report
        assert "analytics-team" in report
        assert "stale" in report

        # Verify file was saved
        outbox = Path(tmpdir)
        saved_files = list(outbox.glob("incident_*.md"))
        assert len(saved_files) == 1
        assert saved_files[0].read_text() == report
