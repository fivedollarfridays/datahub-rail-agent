"""A full agent run over a two-node estate surfaces the edge break.

Same shape as the incident that started this: the producer table is fresh,
the deliverable it feeds has not moved in nine days, and every green run of
the producing job says nothing is wrong.
"""
import time

import pytest

from datahub_rail.agent import execute, freshness_sla_hours
from datahub_rail.types import Dataset, Freshness, LineageResult, SchemaMetadata

BASE = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.{},PROD)"
DIGEST = BASE.format("daily_digest")
PLANNER = BASE.format("planner_runs")
HOUR_MS = 3600 * 1000

CONFIG = {
    "probes": [
        {"name": "freshness", "type": "freshness", "params": {"sla_hours": 24}},
    ]
}


class _TwoNodeEstate:
    """planner_runs (fresh, ran an hour ago) → daily_digest (nine days stale)."""

    def __init__(self, digest_age_hours=9 * 24, planner_age_hours=1):
        self.ages = {DIGEST: digest_age_hours, PLANNER: planner_age_hours}

    async def connect(self):
        return None

    async def disconnect(self):
        return None

    def provenance_for(self, urn):
        return []

    async def list_datasets(self, query="*", num_results=50):
        return [
            Dataset(urn=DIGEST, name="daily_digest", platform="postgres",
                    owner="ops", last_modified=0),
            Dataset(urn=PLANNER, name="planner_runs", platform="postgres",
                    owner="ops", last_modified=0),
        ]

    async def get_entity(self, urn):
        return {"urn": urn, "owner": "ops"}

    async def get_freshness(self, urn):
        now_ms = int(time.time() * 1000)
        return Freshness(
            urn=urn,
            last_modified=now_ms - int(self.ages[urn] * HOUR_MS),
            is_stale=False,
            expected_frequency=0,
        )

    async def get_declared_upstreams(self, urn):
        return [PLANNER] if urn == DIGEST else []

    async def walk_upstream(self, urn, hops=1):
        upstream = (
            [{"urn": PLANNER, "name": "planner_runs", "platform": "postgres"}]
            if urn == DIGEST
            else []
        )
        return LineageResult(urn=urn, upstream=upstream, downstream=[])

    async def fetch_schema(self, urn):
        return SchemaMetadata(urn=urn, fields=[], description="")


def _incident(outbox, name):
    """Read the incident report written for one dataset."""
    return next(iter(outbox.glob(f"incident_{name}_*.md"))).read_text()


@pytest.mark.asyncio
async def test_run_flags_the_edge_and_leaves_the_producer_passing(tmp_path):
    """The producer passes its own probes; only the deliverable fails."""
    outbox = tmp_path / "outbox"
    report = await execute(
        graph=_TwoNodeEstate(), config=CONFIG, outbox=outbox,
        history_path=tmp_path / "h.jsonl",
    )

    status = {r["name"]: r["status"] for r in report["datasets"]}
    assert status == {"daily_digest": "fail", "planner_runs": "pass"}
    assert "### Producer Healthy, Delivery Broken" in _incident(outbox, "daily_digest")


@pytest.mark.asyncio
async def test_stalled_producer_estate_gets_no_callout(tmp_path):
    """Both stale: the upstream is a real suspect, so the walk stands alone."""
    outbox = tmp_path / "outbox"
    await execute(
        graph=_TwoNodeEstate(digest_age_hours=9 * 24, planner_age_hours=8 * 24),
        config=CONFIG, outbox=outbox, history_path=tmp_path / "h.jsonl",
    )

    assert "Producer Healthy" not in _incident(outbox, "daily_digest")


def test_sla_comes_from_the_configured_freshness_probe():
    """The callout uses the estate's own SLA, not a hardcoded 24 hours."""
    assert freshness_sla_hours(CONFIG) == 24
    assert freshness_sla_hours(
        {"probes": [{"name": "freshness", "type": "freshness", "params": {"sla_hours": 72}}]}
    ) == 72
    assert freshness_sla_hours({"probes": []}) == 24
