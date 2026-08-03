"""Aspect payload shaping for write-back.

DataHub's OpenAPI v3 entity write replaces a whole aspect, so write-back has
to merge: rail-owned markers get replaced (never stacked), and anything a
human or another tool put on the dataset survives untouched.
"""

from datahub_rail.writeback import (
    RAIL_PROPERTY_PREFIX,
    merge_properties,
    merge_tags,
    tag_urn,
)


def test_tag_urn_is_bounded_by_status_class():
    """Tag entities stay a small fixed set; the day counter never spawns tags."""
    assert tag_urn("PASS") == "urn:li:tag:rail.status.PASS"
    assert tag_urn("CHRONIC") == "urn:li:tag:rail.status.CHRONIC"


def test_merge_tags_preserves_foreign_tags():
    """A tag a human added must survive a write-back."""
    existing = [{"tag": "urn:li:tag:Legacy"}]
    merged = merge_tags(existing, "PASS")
    assert {"tag": "urn:li:tag:Legacy"} in merged
    assert {"tag": "urn:li:tag:rail.status.PASS"} in merged


def test_merge_tags_replaces_prior_rail_tag_rather_than_stacking():
    """RECOVERED clears the old failure marker instead of accumulating."""
    existing = [{"tag": "urn:li:tag:rail.status.CHRONIC"}, {"tag": "urn:li:tag:Legacy"}]
    merged = merge_tags(existing, "RECOVERED")
    rail = [t for t in merged if t["tag"].startswith("urn:li:tag:rail.status.")]
    assert rail == [{"tag": "urn:li:tag:rail.status.RECOVERED"}]
    assert {"tag": "urn:li:tag:Legacy"} in merged


def test_merge_properties_drops_rail_keys_with_no_value():
    """A recovered dataset loses its stale incident pointer."""
    existing = [
        {"propertyUrn": f"{RAIL_PROPERTY_PREFIX}incident", "values": [{"string": "old.md"}]},
        {"propertyUrn": "urn:li:structuredProperty:someone.else", "values": [{"string": "keep"}]},
    ]
    merged = merge_properties(existing, {"status": "RECOVERED", "incident": None})
    urns = [p["propertyUrn"] for p in merged]
    assert f"{RAIL_PROPERTY_PREFIX}incident" not in urns
    assert "urn:li:structuredProperty:someone.else" in urns
    assert {"propertyUrn": f"{RAIL_PROPERTY_PREFIX}status",
            "values": [{"string": "RECOVERED"}]} in merged
