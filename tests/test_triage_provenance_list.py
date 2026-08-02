"""Incident reports carry an explicit provenance list.

The provenance guarantee is only checkable if the report names the graph
reads behind it. Each entry is (tool, dataset_urn, timestamp).
"""
import pytest

from datahub_rail.triage import Provenance, TriageEngine
from datahub_rail.types import Freshness, LineageResult

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"


class _Client:
    async def walk_upstream(self, urn, hops=1):
        return LineageResult(urn=urn, upstream=[], downstream=[])

    async def get_freshness(self, urn):
        return Freshness(urn=urn, last_modified=1700000000000, is_stale=True, expected_frequency=0)


PROV = [
    Provenance(tool="gms:datasetProperties.lastModified", dataset_urn=URN, timestamp="2026-08-02T15:00:00+00:00"),
    Provenance(tool="mcp:get_lineage", dataset_urn=URN, timestamp="2026-08-02T15:00:01+00:00"),
]


@pytest.mark.asyncio
async def test_report_renders_provenance_section(tmp_path):
    """The report lists every graph read that backs its claims."""
    markdown = await TriageEngine().generate_incident_report(
        client=_Client(), failing_dataset_urn=URN, failing_dataset_name="orders_archive",
        dataset_owner="data-eng", probe_name="freshness", probe_status="fail",
        probe_message="Dataset is stale: last modified 45 days ago (SLA: 24h)",
        outbox_dir=tmp_path, provenance=PROV,
    )

    assert "### Provenance" in markdown
    assert "gms:datasetProperties.lastModified" in markdown
    assert "mcp:get_lineage" in markdown
    assert "2026-08-02T15:00:00+00:00" in markdown


@pytest.mark.asyncio
async def test_report_without_provenance_still_renders(tmp_path):
    """Provenance is optional; omitting it must not break report generation."""
    markdown = await TriageEngine().generate_incident_report(
        client=_Client(), failing_dataset_urn=URN, failing_dataset_name="orders_archive",
        dataset_owner="data-eng", probe_name="freshness", probe_status="fail",
        probe_message="stale", outbox_dir=tmp_path,
    )

    assert "## Incident Report" in markdown
    assert "### Provenance" not in markdown


@pytest.mark.asyncio
async def test_report_names_the_failing_probe(tmp_path):
    """The report states which probe fired, not just its message."""
    markdown = await TriageEngine().generate_incident_report(
        client=_Client(), failing_dataset_urn=URN, failing_dataset_name="orders_archive",
        dataset_owner="data-eng", probe_name="freshness", probe_status="fail",
        probe_message="stale", outbox_dir=tmp_path, provenance=PROV,
    )

    assert "freshness" in markdown
