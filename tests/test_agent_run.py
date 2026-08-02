"""Agent entrypoint: config loading and a full probe run over a fake estate."""
import pytest

from datahub_rail.agent import execute, load_config
from datahub_rail.types import Dataset, Freshness, LineageResult, SchemaMetadata

BASE = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.{},PROD)"
USERS = BASE.format("users")
ORDERS = BASE.format("orders_archive")
EVENTS = BASE.format("events")
GONE = BASE.format("raw_events_old")

NOW_MS = 1_800_000_000_000
OLD_MS = NOW_MS - 45 * 24 * 3600 * 1000

CONFIG = {
    "probes": [
        {"name": "freshness", "type": "freshness", "params": {"sla_hours": 24}},
        {"name": "lineage_integrity", "type": "lineage", "params": {}},
    ]
}


class _FakeGraph:
    """In-memory estate: one healthy control, one stale, one broken lineage."""

    def __init__(self):
        self.provenance = []

    async def connect(self):
        return None

    async def disconnect(self):
        return None

    def provenance_for(self, urn):
        return []

    async def list_datasets(self, query="*", num_results=50):
        return [
            Dataset(urn=USERS, name="users", platform="postgres", owner="", last_modified=0),
            Dataset(urn=ORDERS, name="orders_archive", platform="postgres", owner="", last_modified=0),
            Dataset(urn=EVENTS, name="events", platform="postgres", owner="", last_modified=0),
        ]

    async def get_entity(self, urn):
        return {"urn": urn, "name": urn.split(",")[1].split(".")[-1],
                "platform": "postgres", "owner": "data-eng"}

    async def get_freshness(self, urn):
        import time
        now_ms = int(time.time() * 1000)
        stale = now_ms - 45 * 24 * 3600 * 1000
        return Freshness(urn=urn, last_modified=stale if urn == ORDERS else now_ms,
                         is_stale=False, expected_frequency=0)

    async def get_declared_upstreams(self, urn):
        return [GONE] if urn == EVENTS else []

    async def walk_upstream(self, urn, hops=1):
        return LineageResult(urn=urn, upstream=[], downstream=[])

    async def fetch_schema(self, urn):
        return SchemaMetadata(urn=urn, fields=[], description="")


def test_load_config_reads_probe_registry(tmp_path):
    """The shipped config file must parse into a probe registry."""
    cfg = tmp_path / "probes.yaml"
    cfg.write_text("probes:\n  - name: freshness\n    type: freshness\n    params:\n      sla_hours: 24\n")

    loaded = load_config(cfg)

    assert loaded["probes"][0]["type"] == "freshness"


def test_load_config_ships_valid_repo_config():
    """config/probes.yaml in the repo must be loadable as written."""
    from pathlib import Path
    repo_cfg = Path(__file__).resolve().parent.parent / "config" / "probes.yaml"

    loaded = load_config(repo_cfg)

    assert [p["type"] for p in loaded["probes"]] == ["freshness", "lineage", "schema"]


@pytest.mark.asyncio
async def test_execute_flags_exactly_the_planted_faults(tmp_path):
    """Healthy control passes; stale and broken-lineage datasets fail."""
    report = await execute(
        graph=_FakeGraph(), config=CONFIG,
        outbox=tmp_path / "outbox", history_path=tmp_path / "history.jsonl",
    )

    status = {r["name"]: r["status"] for r in report["datasets"]}
    assert status == {"users": "pass", "orders_archive": "fail", "events": "fail"}


@pytest.mark.asyncio
async def test_execute_writes_incident_reports_for_failures_only(tmp_path):
    """One incident report per failing dataset lands in the outbox."""
    outbox = tmp_path / "outbox"
    await execute(graph=_FakeGraph(), config=CONFIG, outbox=outbox,
                  history_path=tmp_path / "history.jsonl")

    names = sorted(p.name.split("_2")[0] for p in outbox.glob("incident_*.md"))
    assert names == ["incident_events", "incident_orders_archive"]


@pytest.mark.asyncio
async def test_execute_appends_history_and_renders_digest(tmp_path):
    """First run marks failures NEW; second run marks them CHRONIC day 2."""
    history = tmp_path / "history.jsonl"
    first = await execute(graph=_FakeGraph(), config=CONFIG,
                          outbox=tmp_path / "outbox", history_path=history)
    assert "NEW" in first["digest"]

    second = await execute(graph=_FakeGraph(), config=CONFIG,
                           outbox=tmp_path / "outbox", history_path=history)
    assert "CHRONIC" in second["digest"]
    assert "day 2" in second["digest"]


@pytest.mark.asyncio
async def test_execute_returns_nonzero_exit_when_faults_found(tmp_path):
    """A run that finds faults reports a failing exit code."""
    report = await execute(graph=_FakeGraph(), config=CONFIG,
                           outbox=tmp_path / "outbox", history_path=tmp_path / "h.jsonl")

    assert report["exit_code"] == 1


@pytest.mark.asyncio
async def test_execute_orders_datasets_deterministically(tmp_path):
    """Output order is stable run-to-run so the demo reads the same every take."""
    report = await execute(graph=_FakeGraph(), config=CONFIG,
                           outbox=tmp_path / "outbox", history_path=tmp_path / "h.jsonl")

    assert [r["name"] for r in report["datasets"]] == ["events", "orders_archive", "users"]
