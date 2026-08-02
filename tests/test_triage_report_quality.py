"""Incident report readability: self-rooted failures and human-readable dates."""
import time

import pytest

from datahub_rail.triage import TriageEngine
from datahub_rail.types import Freshness, LineageResult

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"
FORTY_FIVE_DAYS_AGO_MS = int((time.time() - 45 * 24 * 3600) * 1000)


class _NoUpstream:
    async def walk_upstream(self, urn, hops=1):
        return LineageResult(urn=urn, upstream=[], downstream=[])

    async def get_freshness(self, urn):
        return Freshness(urn=urn, last_modified=FORTY_FIVE_DAYS_AGO_MS,
                         is_stale=True, expected_frequency=0)


async def _report(tmp_path, client=None):
    return await TriageEngine().generate_incident_report(
        client=client or _NoUpstream(), failing_dataset_urn=URN,
        failing_dataset_name="orders_archive", dataset_owner="data-eng",
        probe_name="freshness", probe_status="fail",
        probe_message="Dataset is stale: last modified 45 days ago (SLA: 24h)",
        outbox_dir=tmp_path,
    )


@pytest.mark.asyncio
async def test_root_cause_is_the_dataset_itself_when_no_upstream(tmp_path):
    """With no upstream, the failing dataset is its own root cause at 0 hops."""
    markdown = await _report(tmp_path)

    assert "unknown" not in markdown.lower()
    assert "orders_archive" in markdown
    assert "0 hops" in markdown


@pytest.mark.asyncio
async def test_root_cause_states_it_is_the_failure(tmp_path):
    """The report says plainly that the dataset is the failure."""
    markdown = await _report(tmp_path)

    assert "is the failure" in markdown


@pytest.mark.asyncio
async def test_last_modified_renders_as_date_and_age(tmp_path):
    """A judge reads a date, not an epoch-millisecond integer."""
    markdown = await _report(tmp_path)

    assert str(FORTY_FIVE_DAYS_AGO_MS) not in markdown
    assert "45 days old" in markdown
    assert "UTC" in markdown
