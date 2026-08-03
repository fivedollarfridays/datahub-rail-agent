"""Liveness of the monitor itself, judged by what it wrote into the graph.

A watcher that dies quietly is indistinguishable from a quiet week: no
alerts, no output, nothing to notice. So this never asks a heartbeat file
whether the agent is alive. It reads the ``rail.last_run`` structured
property the agent publishes onto the datasets it judged (PR #3), takes the
newest stamp in the estate, and fails loudly when that stamp is older than
the operator's tolerance — or when there is no stamp at all, which is a
blind state, not a healthy one.
"""
import argparse
import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .gms import GMSReader
from .rail_markers import RAIL_PROPERTY_PREFIX

logger = logging.getLogger(__name__)

RAIL_LAST_RUN_URN = f"{RAIL_PROPERTY_PREFIX}last_run"

DEFAULT_RERUN_COMMAND = (
    "python -m datahub_rail.agent --config config/probes.yaml --writeback"
)

VERB = "check-monitor"


@dataclass
class MonitorVerdict:
    """Outcome of one liveness check, and the exit code it maps to."""

    ok: bool
    newest: Optional[datetime]
    dataset_urn: Optional[str]
    message: str

    @property
    def exit_code(self) -> int:
        """0 when the monitor is provably live, 1 otherwise."""
        return 0 if self.ok else 1


def _string_value(entry: dict) -> Optional[str]:
    """Pull the string out of one structured-property value entry."""
    for value in entry.get("values") or []:
        if isinstance(value, dict) and value.get("string") is not None:
            return str(value["string"])
        if isinstance(value, str):
            return value
    return None


def last_run_value(entity: dict) -> Optional[str]:
    """The rail.last_run stamp written onto one dataset, or None."""
    aspect = (entity.get("structuredProperties") or {}).get("value") or {}
    for entry in aspect.get("properties") or []:
        if entry.get("propertyUrn") == RAIL_LAST_RUN_URN:
            return _string_value(entry)
    return None


def _parse(stamp: str) -> Optional[datetime]:
    """Parse an ISO8601 run stamp, tolerating a trailing Z."""
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def newest_run(entities: list[dict]) -> tuple[Optional[datetime], Optional[str]]:
    """Newest write-back stamp in the estate and the dataset carrying it."""
    newest: Optional[datetime] = None
    owner: Optional[str] = None
    for entity in entities:
        raw = last_run_value(entity)
        if raw is None:
            continue
        parsed = _parse(raw)
        if parsed is None:
            logger.warning("Unparseable rail.last_run on %s: %r", entity.get("urn"), raw)
            continue
        if newest is None or parsed > newest:
            newest, owner = parsed, entity.get("urn")
    return newest, owner


def evaluate(
    newest: Optional[datetime],
    dataset_urn: Optional[str],
    max_age_hours: float,
    now: Optional[datetime] = None,
    rerun_command: str = DEFAULT_RERUN_COMMAND,
) -> MonitorVerdict:
    """Judge monitor liveness from the newest write-back stamp."""
    now = now or datetime.now(timezone.utc)

    if newest is None:
        return MonitorVerdict(
            ok=False,
            newest=None,
            dataset_urn=None,
            message=(
                "[ALARM] Monitor has never written back (or write-back disabled):"
                " no rail.last_run property on any dataset in DataHub.\n"
                "        No capture evidence is a blind state, not a healthy one.\n"
                f"        Re-run: {rerun_command}"
            ),
        )

    age_hours = (now - newest).total_seconds() / 3600
    stamp = newest.isoformat()
    if age_hours <= max_age_hours:
        return MonitorVerdict(
            ok=True,
            newest=newest,
            dataset_urn=dataset_urn,
            message=(
                f"[OK] Rail monitor is live: newest write-back {stamp}"
                f" ({age_hours:.1f}h ago, limit {max_age_hours:g}h) on {dataset_urn}"
            ),
        )

    return MonitorVerdict(
        ok=False,
        newest=newest,
        dataset_urn=dataset_urn,
        message=(
            f"[ALARM] MONITOR IS DEAD: newest write-back {stamp}"
            f" ({age_hours:.1f}h ago, limit {max_age_hours:g}h) on {dataset_urn}.\n"
            "        Nothing has written a verdict into DataHub since then —"
            " the agent is not running, not that the estate is healthy.\n"
            f"        Re-run: {rerun_command}"
        ),
    )


async def check(
    gms_url: str,
    token: str,
    max_age_hours: float,
    rerun_command: str = DEFAULT_RERUN_COMMAND,
) -> MonitorVerdict:
    """Read every dataset's rail markers and judge the monitor's liveness."""
    reader = GMSReader(gms_url=gms_url, token=token or None)
    await reader.connect()
    try:
        entities = await reader.scroll_datasets(["structuredProperties"])
    finally:
        await reader.disconnect()

    newest, dataset_urn = newest_run(entities)
    return evaluate(newest, dataset_urn, max_age_hours, rerun_command=rerun_command)


def build_parser() -> argparse.ArgumentParser:
    """CLI parser for the check-monitor verb."""
    parser = argparse.ArgumentParser(
        prog=f"python -m datahub_rail.agent {VERB}",
        description=(
            "Fail loudly when nothing has written rail verdicts into DataHub"
            " recently. Liveness is judged from what the agent actually wrote,"
            " never from a heartbeat file."
        ),
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        default=24.0,
        help="how old the newest write-back may be before this fails (default: 24)",
    )
    parser.add_argument("--datahub-url", default="http://localhost:8080", help="GMS base URL")
    parser.add_argument("--token", default="", help="DataHub token (empty for local quickstart)")
    parser.add_argument(
        "--config",
        default="config/probes.yaml",
        help="probe config named in the re-run command this prints",
    )
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Run the liveness check; 0 when provably live, 1 otherwise."""
    args = build_parser().parse_args(argv)
    rerun = f"python -m datahub_rail.agent --config {args.config} --writeback"
    verdict = asyncio.run(
        check(
            gms_url=args.datahub_url,
            token=args.token,
            max_age_hours=args.max_age_hours,
            rerun_command=rerun,
        )
    )
    print(verdict.message, file=sys.stdout if verdict.ok else sys.stderr)
    return verdict.exit_code
