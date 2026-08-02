"""Evidence gathering for incident reports."""
import pytest
from datahub_rail.triage import TriageEngine


@pytest.mark.asyncio
async def test_gather_evidence_timestamps(mock_client):
    """Evidence includes freshness timestamps from graph."""
    engine = TriageEngine()

    dataset_urn = "urn:li:dataset:(urn:li:dataPlatform:kafka,events-raw,PROD)"

    evidence = await engine._gather_evidence(
        mock_client,
        dataset_urn,
    )

    # Should have fetched freshness
    assert evidence["urn"] == dataset_urn
    assert evidence["last_modified"] == 1722595200
    assert not evidence["is_stale"]


@pytest.mark.asyncio
async def test_gather_evidence_with_probe_status():
    """Evidence includes probe status and message."""
    engine = TriageEngine()

    evidence = engine._add_probe_status(
        {
            "urn": "urn:dataset:test",
            "name": "test_dataset",
        },
        probe_name="freshness",
        status="fail",
        message="Dataset is stale: last modified 3 days ago (SLA: 24h)",
    )

    assert evidence["probe_name"] == "freshness"
    assert evidence["probe_status"] == "fail"
    assert evidence["probe_message"] == "Dataset is stale: last modified 3 days ago (SLA: 24h)"
