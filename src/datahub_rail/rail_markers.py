"""Shape of the markers rail writes onto a dataset, and how they merge.

Kept apart from transport so the merge rules — replace rail's own markers,
never touch anyone else's — can be read and tested without a server.
"""
from typing import Optional

RAIL_TAG_PREFIX = "urn:li:tag:rail.status."
RAIL_PROPERTY_PREFIX = "urn:li:structuredProperty:rail."

STATUS_CLASSES = ("PASS", "NEW-FAIL", "CHRONIC", "RECOVERED")

# Ordered so the dataset Properties tab reads top-to-bottom as a sentence.
PROPERTY_KEYS = ("status", "probe", "last_run", "incident")

PROPERTY_LABELS = {
    "status": ("Rail Status", "Latest delta-aware verdict from the DataHub Rail Agent"),
    "probe": ("Rail Probe", "Probe that produced the current rail verdict"),
    "last_run": ("Rail Last Run", "Timestamp of the last rail agent probe run"),
    "incident": ("Rail Incident Report", "Incident report filename in the agent outbox"),
}

TAG_DESCRIPTIONS = {
    "PASS": "Rail agent: all probes passing",
    "NEW-FAIL": "Rail agent: newly failing this run",
    "CHRONIC": "Rail agent: failing for multiple consecutive runs",
    "RECOVERED": "Rail agent: recovered since the previous run",
}


def tag_urn(status_class: str) -> str:
    """URN of the bounded status tag for a verdict class."""
    return f"{RAIL_TAG_PREFIX}{status_class}"


def merge_tags(existing: list[dict], status_class: str) -> list[dict]:
    """Replace the rail status tag, preserving every tag rail does not own."""
    foreign = [t for t in existing if not str(t.get("tag", "")).startswith(RAIL_TAG_PREFIX)]
    return foreign + [{"tag": tag_urn(status_class)}]


def merge_properties(existing: list[dict], values: dict) -> list[dict]:
    """Replace rail structured properties; drop rail keys with no value."""
    foreign = [
        p
        for p in existing
        if not str(p.get("propertyUrn", "")).startswith(RAIL_PROPERTY_PREFIX)
    ]
    mine = [
        {"propertyUrn": f"{RAIL_PROPERTY_PREFIX}{key}", "values": [{"string": str(values[key])}]}
        for key in PROPERTY_KEYS
        if values.get(key) is not None
    ]
    return foreign + mine


def property_values(
    verdict,
    run_timestamp: str,
    incident_file: Optional[str] = None,
) -> dict:
    """Build the rail property payload for one dataset's verdict."""
    return {
        "status": verdict.label,
        "probe": ", ".join(verdict.probes),
        "last_run": run_timestamp,
        "incident": incident_file,
    }


def tag_entity(status_class: str) -> dict:
    """Entity payload creating the tag so the UI renders a named chip."""
    return {
        "urn": tag_urn(status_class),
        "tagProperties": {
            "value": {
                "name": f"rail.status.{status_class}",
                "description": TAG_DESCRIPTIONS[status_class],
            }
        },
    }


def property_definition(key: str) -> dict:
    """Entity payload defining one rail structured property."""
    display, description = PROPERTY_LABELS[key]
    return {
        "urn": f"{RAIL_PROPERTY_PREFIX}{key}",
        "propertyDefinition": {
            "value": {
                "qualifiedName": f"rail.{key}",
                "displayName": display,
                "description": description,
                "valueType": "urn:li:dataType:datahub.string",
                "cardinality": "SINGLE",
                "entityTypes": ["urn:li:entityType:datahub.dataset"],
            }
        },
    }
