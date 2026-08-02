"""Root-cause selection: pick deepest failing node, deterministic tie-breaking."""
import pytest
from datahub_rail.triage import TriageEngine


@pytest.mark.asyncio
async def test_pick_deepest_failing_node():
    """Root cause is the deepest (furthest) failing node."""
    engine = TriageEngine()

    # Three failing nodes at different depths
    failing_nodes = [
        ({"urn": "urn1", "name": "level-1"}, 1),
        ({"urn": "urn2", "name": "level-2"}, 2),
        ({"urn": "urn3", "name": "level-3"}, 3),
    ]

    root_cause = engine._pick_root_cause(failing_nodes)

    assert root_cause["name"] == "level-3"
    assert root_cause["distance"] == 3


@pytest.mark.asyncio
async def test_tie_break_deterministically():
    """When multiple nodes at same depth fail, pick by sorted URN."""
    engine = TriageEngine()

    # Two nodes at same depth
    failing_nodes = [
        ({"urn": "urn:z", "name": "z-node"}, 2),
        ({"urn": "urn:a", "name": "a-node"}, 2),
    ]

    root_cause = engine._pick_root_cause(failing_nodes)

    # Should pick a-node (urn:a < urn:z alphabetically)
    assert root_cause["name"] == "a-node"
    assert root_cause["urn"] == "urn:a"
