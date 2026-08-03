"""Write-back is strictly opt-in.

The recorded demo runs the default path, so `python -m datahub_rail.agent`
with no new flag must behave exactly as it did before write-back existed:
no writer built, no extra call, same exit code.
"""
from unittest.mock import AsyncMock, patch

import pytest

from datahub_rail import agent

BASE = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)"


def _args(**overrides):
    parsed = agent.build_parser().parse_args([])
    for key, value in overrides.items():
        setattr(parsed, key, value)
    return parsed


class _StubGraph:
    async def connect(self):
        return None

    async def disconnect(self):
        return None


class _StubWriter:
    """Stands in for DataHubWriteBack so no test ever needs a live GMS."""

    async def connect(self):
        return None

    async def ensure_schema(self):
        return None

    async def disconnect(self):
        return None


def _patched_run(tmp_path, args):
    """Patch the graph and execute() so run() is exercised in isolation."""
    report = {
        "datasets": [
            {"urn": BASE, "name": "users", "status": "pass", "results": {}, "failures": {}}
        ],
        "digest": "PASS",
        "artifacts_written": False,
        "exit_code": 0,
    }
    return (
        patch.object(agent.GraphClient, "create", return_value=_StubGraph()),
        patch.object(agent, "execute", AsyncMock(return_value=report)),
        args,
    )


def test_writeback_flag_defaults_to_off():
    """The default demo invocation must not enable write-back."""
    assert agent.build_parser().parse_args([]).writeback is False


def test_writeback_flag_can_be_enabled():
    """--writeback is the documented opt-in."""
    assert agent.build_parser().parse_args(["--writeback"]).writeback is True


@pytest.mark.asyncio
async def test_default_run_never_publishes(tmp_path):
    """Without the flag, nothing is written back to DataHub."""
    graph_patch, exec_patch, args = _patched_run(
        tmp_path, _args(config="config/probes.yaml", outbox=str(tmp_path),
                        history=str(tmp_path / "h.jsonl"), writeback=False)
    )
    with graph_patch, exec_patch, patch.object(agent, "publish_run", AsyncMock()) as publish:
        with patch.object(agent, "load_config", return_value={"probes": []}):
            code = await agent.run(args)

    publish.assert_not_called()
    assert code == 0


@pytest.mark.asyncio
async def test_opt_in_run_publishes_verdicts(tmp_path):
    """With --writeback, the run publishes its verdicts back into DataHub."""
    graph_patch, exec_patch, args = _patched_run(
        tmp_path, _args(config="config/probes.yaml", outbox=str(tmp_path),
                        history=str(tmp_path / "h.jsonl"), writeback=True)
    )
    counts = {"written": 1, "failed": 0, "skipped": 0}
    with graph_patch, exec_patch, patch.object(
        agent, "publish_run", AsyncMock(return_value=counts)
    ) as publish:
        # Stub the writer too: without this the test passes only on a machine
        # that happens to have GMS running, and fail-soft hides the difference.
        with patch.object(agent, "load_config", return_value={"probes": []}), patch.object(
            agent, "DataHubWriteBack", return_value=_StubWriter()
        ):
            code = await agent.run(args)

    publish.assert_called_once()
    assert code == 0


@pytest.mark.asyncio
async def test_writeback_crash_does_not_change_the_run_outcome(tmp_path):
    """Even a writer that cannot connect leaves the probe run's exit code intact."""
    graph_patch, exec_patch, args = _patched_run(
        tmp_path, _args(config="config/probes.yaml", outbox=str(tmp_path),
                        history=str(tmp_path / "h.jsonl"), writeback=True)
    )
    with graph_patch, exec_patch, patch.object(
        agent.DataHubWriteBack, "connect", AsyncMock(side_effect=OSError("no route to host"))
    ):
        with patch.object(agent, "load_config", return_value={"probes": []}):
            code = await agent.run(args)

    assert code == 0
