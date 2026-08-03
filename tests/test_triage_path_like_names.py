"""Path-shaped dataset names must not kill the run.

A real estate names datasets after the thing they describe — a file path
(``data/voice/fingerprint.json``), not a flat ``demo.public.x`` table. The
incident filename is built from that name, so an unslugified separator
targets a directory that does not exist and raises ``FileNotFoundError``
*after* every probe has run and *before* anything is printed: the whole
run's work is lost.
"""
import re
from pathlib import Path

import pytest

from datahub_rail.triage import TriageEngine

PATH_LIKE_URN = "urn:li:dataset:(urn:li:dataPlatform:file,data/voice/fingerprint.json,PROD)"
FLAT_URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.orders_archive,PROD)"


async def _report(engine, client, name, urn, outbox):
    """Run one incident report end to end."""
    return await engine.generate_incident_report(
        client=client,
        failing_dataset_urn=urn,
        failing_dataset_name=name,
        dataset_owner="ops",
        probe_name="freshness",
        probe_status="fail",
        probe_message="Dataset is stale: last modified 12 days ago (SLA: 24h)",
        outbox_dir=outbox,
    )


@pytest.mark.asyncio
async def test_path_like_name_completes_and_writes_flat_file(mock_client, tmp_path):
    """A path-shaped name produces one flat report file, no pre-created dirs."""
    outbox = tmp_path / "outbox"
    engine = TriageEngine()

    markdown = await _report(
        engine, mock_client, "data/voice/fingerprint.json", PATH_LIKE_URN, outbox
    )

    assert "## Incident Report" in markdown
    written = [p for p in outbox.rglob("*.md")]
    assert len(written) == 1, f"expected exactly one report, got {written}"

    report = written[0]
    assert report.parent == outbox, "report must be flat in outbox, not nested"
    assert re.fullmatch(
        r"incident_data-voice-fingerprint\.json_\d{8}_\d{6}\.md", report.name
    ), report.name
    assert not [p for p in outbox.iterdir() if p.is_dir()], "no directories created"


@pytest.mark.asyncio
async def test_flat_demo_name_filename_is_byte_identical(mock_client, tmp_path):
    """Flat demo names must keep today's exact filename — samples cannot move."""
    outbox = tmp_path / "outbox"
    engine = TriageEngine()

    await _report(
        engine, mock_client, "demo.public.orders_archive", FLAT_URN, outbox
    )

    report = next(iter(outbox.glob("*.md")))
    assert re.fullmatch(
        r"incident_demo\.public\.orders_archive_\d{8}_\d{6}\.md", report.name
    ), report.name


def test_committed_sample_output_names_are_slug_stable():
    """Every committed sample-outputs/ stem must survive slugify unchanged.

    This is the regression that pins the verified demo: if slugify ever
    rewrites one of these names, the committed artifacts judges compare
    against would no longer match what the code emits.
    """
    from datahub_rail.naming import slugify_dataset_name

    samples = Path(__file__).resolve().parent.parent / "sample-outputs"
    stems = set()
    for artifact in samples.iterdir():
        for prefix in ("incident_", "schema_patch_", "schema_drift_", "commit_message_"):
            if artifact.name.startswith(prefix):
                stems.add(artifact.name[len(prefix):].rsplit(".", 1)[0])

    assert stems, "sample-outputs/ must contain named artifacts to pin"
    for stem in stems:
        assert slugify_dataset_name(stem) == stem, f"slugify would move {stem!r}"
