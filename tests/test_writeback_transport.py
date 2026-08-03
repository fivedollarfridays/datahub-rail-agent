"""Transport-level write-back tests against a faked OpenAPI v3 surface.

Mirrors the seeder's transport contract: writes go to
``/openapi/v3/entity/dataset?async=false``. Read-then-merge is asserted
here so a live server's existing tags cannot be clobbered.
"""
import json

import pytest

from datahub_rail.verdicts import Verdict
from datahub_rail.writeback import DataHubWriteBack

URN = "urn:li:dataset:(urn:li:dataPlatform:postgres,demo.public.users,PROD)"


class _FakeResponse:
    def __init__(self, status=200, payload=None):
        self.status = status
        self._payload = payload if payload is not None else [{"urn": URN}]

    async def json(self):
        return self._payload

    async def text(self):
        return json.dumps(self._payload)


class _FakeCtx:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return False


class FakeSession:
    """Records posts; serves canned aspect reads keyed by aspect name."""

    def __init__(self, aspects=None, post_status=200):
        self.posts = []
        self.gets = []
        self._aspects = aspects or {}
        self._post_status = post_status

    def post(self, url, json=None, headers=None):
        self.posts.append({"url": url, "payload": json})
        return _FakeCtx(_FakeResponse(status=self._post_status))

    def get(self, url, headers=None):
        self.gets.append(url)
        aspect = url.rsplit("/", 1)[-1]
        if aspect not in self._aspects:
            return _FakeCtx(_FakeResponse(status=404, payload={}))
        return _FakeCtx(_FakeResponse(status=200, payload={"value": self._aspects[aspect]}))

    async def close(self):
        return None


def _writer(session):
    writer = DataHubWriteBack(gms_url="http://localhost:8080")
    writer.session = session
    return writer


def _dataset_posts(session):
    return [p for p in session.posts if "/entity/dataset" in p["url"]]


@pytest.mark.asyncio
async def test_apply_writes_both_aspects_to_openapi_v3():
    """One write per dataset carrying the tag and the structured properties."""
    session = FakeSession()
    verdict = Verdict("CHRONIC", "CHRONIC-day-3", ["freshness"])
    await _writer(session).apply(URN, verdict, "2026-08-03T12:00:00+00:00")

    posts = _dataset_posts(session)
    assert posts, "expected a dataset write"
    assert posts[0]["url"].endswith("/openapi/v3/entity/dataset?async=false")
    body = posts[0]["payload"][0]
    assert body["urn"] == URN
    assert body["globalTags"]["value"]["tags"] == [{"tag": "urn:li:tag:rail.status.CHRONIC"}]


@pytest.mark.asyncio
async def test_apply_writes_full_verdict_probe_and_timestamp():
    """The structured properties carry day-N, the probe name and the run time."""
    session = FakeSession()
    verdict = Verdict("CHRONIC", "CHRONIC-day-3", ["freshness"])
    await _writer(session).apply(URN, verdict, "2026-08-03T12:00:00+00:00", "incident_users_1.md")

    props = _dataset_posts(session)[0]["payload"][0]["structuredProperties"]["value"]["properties"]
    flat = {p["propertyUrn"].split("rail.")[-1]: p["values"][0]["string"] for p in props}
    assert flat["status"] == "CHRONIC-day-3"
    assert flat["probe"] == "freshness"
    assert flat["last_run"] == "2026-08-03T12:00:00+00:00"
    assert flat["incident"] == "incident_users_1.md"


@pytest.mark.asyncio
async def test_apply_reads_existing_aspects_and_preserves_foreign_tags():
    """A tag rail does not own must survive the merge."""
    session = FakeSession(aspects={"globalTags": {"tags": [{"tag": "urn:li:tag:Legacy"}]}})
    await _writer(session).apply(URN, Verdict("PASS", "PASS", ["freshness"]), "2026-08-03T12:00:00+00:00")

    tags = _dataset_posts(session)[0]["payload"][0]["globalTags"]["value"]["tags"]
    assert {"tag": "urn:li:tag:Legacy"} in tags
    assert {"tag": "urn:li:tag:rail.status.PASS"} in tags


@pytest.mark.asyncio
async def test_ensure_schema_creates_tag_entities_and_property_definitions():
    """Tags and structured properties must exist as entities to render in the UI."""
    session = FakeSession()
    await _writer(session).ensure_schema()

    tag_posts = [p for p in session.posts if "/entity/tag" in p["url"]]
    prop_posts = [p for p in session.posts if "/entity/structuredProperty" in p["url"]]
    created_tags = {item["urn"] for p in tag_posts for item in p["payload"]}
    created_props = {item["urn"] for p in prop_posts for item in p["payload"]}

    assert "urn:li:tag:rail.status.CHRONIC" in created_tags
    assert "urn:li:tag:rail.status.RECOVERED" in created_tags
    assert "urn:li:structuredProperty:rail.status" in created_props
    assert "urn:li:structuredProperty:rail.incident" in created_props
