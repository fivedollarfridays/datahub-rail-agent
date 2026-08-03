"""Incident triage engine: lineage walk and root-cause analysis."""
from typing import Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

from .edge_break import detect_edge_break, is_past_sla
from .incident_report import render_report
from .naming import slugify_dataset_name
from .urns import platform_from_urn

DEFAULT_SLA_HOURS = 24


@dataclass
class Provenance:
    """Source of a fact: (tool, dataset_urn, timestamp)."""

    tool: str  # "walk_upstream", "get_freshness", "fetch_schema", etc.
    dataset_urn: str
    timestamp: str  # ISO8601


class TriageEngine:
    """Walks lineage, identifies root causes, generates incident reports."""

    async def generate_incident_report(
        self,
        client,
        failing_dataset_urn: str,
        failing_dataset_name: str,
        dataset_owner: str,
        probe_name: str,
        probe_status: str,
        probe_message: str,
        outbox_dir: Optional[Path | str] = None,
        provenance: Optional[list["Provenance"]] = None,
        sla_hours: int = DEFAULT_SLA_HOURS,
    ) -> str:
        """Generate incident report for a failing dataset."""
        outbox_dir = Path(outbox_dir) if outbox_dir else Path("outbox")

        # Walk upstream; every collected ancestor is a root-cause candidate
        nodes = await self._walk_upstream_with_distance(client, failing_dataset_urn, max_hops=5)
        root_cause = self._resolve_root_cause(
            nodes, failing_dataset_urn, failing_dataset_name, dataset_owner
        )
        evidence = await self._gather_evidence(client, failing_dataset_urn)
        edge_break = await self._detect_edge_break(
            client, evidence, failing_dataset_name, nodes, sla_hours
        )

        report_data = {
            "failing_dataset": {
                "urn": failing_dataset_urn,
                "name": failing_dataset_name,
                "owner": dataset_owner,
            },
            "root_cause": root_cause,
            "lineage_path": [
                {
                    "name": n[0].get("name", "unknown"),
                    "platform": n[0].get("platform", "unknown"),
                }
                for n in nodes
            ],
            "probe_name": probe_name,
            "probe_message": probe_message,
            "last_modified": evidence.get("last_modified"),
            "edge_break": edge_break,
            "provenance": provenance or [],
        }

        markdown = render_report(report_data)

        # Save to outbox
        outbox_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        slug = slugify_dataset_name(failing_dataset_name)
        report_file = outbox_dir / f"incident_{slug}_{timestamp}.md"
        report_file.write_text(markdown)

        return markdown

    async def _walk_upstream_with_distance(
        self,
        client,
        dataset_urn: str,
        max_hops: int = 5,
    ) -> list[tuple[dict, int]]:
        """Walk upstream lineage, collecting nodes with distance from root."""
        visited = {}  # urn -> (node_dict, distance)
        queue = [(dataset_urn, 0)]

        while queue:
            current_urn, distance = queue.pop(0)

            if current_urn in visited or distance > max_hops:
                continue

            # Walk next level
            try:
                result = await client.walk_upstream(current_urn, hops=1)
                for upstream_node in result.upstream:
                    upstream_urn = upstream_node["urn"]
                    if upstream_urn not in visited:
                        visited[upstream_urn] = (upstream_node, distance + 1)
                        queue.append((upstream_urn, distance + 1))
            except Exception:
                # Walk failed at this node; continue with others
                continue

        # Return collected upstream nodes sorted by URN for deterministic order
        return sorted(visited.values(), key=lambda x: x[0]["urn"])

    async def _detect_edge_break(
        self,
        client,
        evidence: dict,
        failing_dataset_name: str,
        nodes: list[tuple[dict, int]],
        sla_hours: int,
    ) -> Optional[dict]:
        """Is this a healthy producer with a broken delivery edge?

        Reads immediate-upstream freshness only when the output is already
        past SLA and has resolved upstreams, so runs without the fault make
        exactly the graph calls they made before.
        """
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        failing = {
            "name": failing_dataset_name,
            "last_modified": evidence.get("last_modified"),
        }
        immediate = [node for node, distance in nodes if distance == 1]
        if not immediate or not is_past_sla(failing, sla_hours, now_ms):
            return None

        upstreams = []
        for node in immediate:
            upstream_evidence = await self._gather_evidence(client, node["urn"])
            upstreams.append(
                {
                    "name": node.get("name", "unknown"),
                    "last_modified": upstream_evidence.get("last_modified"),
                }
            )

        return detect_edge_break(failing, upstreams, sla_hours, now_ms)

    def _resolve_root_cause(
        self,
        nodes: list[tuple[dict, int]],
        failing_dataset_urn: str,
        failing_dataset_name: str,
        dataset_owner: str,
    ) -> dict:
        """Deepest failing ancestor, or the dataset itself when it has none."""
        if nodes:
            return self._pick_root_cause(nodes)
        return {
            "name": failing_dataset_name,
            "urn": failing_dataset_urn,
            "platform": platform_from_urn(failing_dataset_urn),
            "owner": dataset_owner,
            "distance": 0,
            "is_self": True,
        }

    def _pick_root_cause(
        self,
        failing_nodes: list[tuple[dict, int]],
    ) -> dict:
        """Pick deepest failing node; tie-break by sorted URN."""
        if not failing_nodes:
            return {}

        # Sort by distance (descending), then by URN (ascending) for tie-breaking
        sorted_nodes = sorted(
            failing_nodes,
            key=lambda x: (-x[1], x[0]["urn"]),
        )

        node, distance = sorted_nodes[0]
        return {**node, "distance": distance}

    async def _gather_evidence(
        self,
        client,
        dataset_urn: str,
    ) -> dict:
        """Gather freshness and lineage evidence for a dataset."""
        try:
            freshness = await client.get_freshness(dataset_urn)
            return {
                "urn": dataset_urn,
                "last_modified": freshness.last_modified,
                "is_stale": freshness.is_stale,
            }
        except Exception:
            return {
                "urn": dataset_urn,
                "last_modified": None,
                "is_stale": None,
            }

    def _add_probe_status(
        self,
        evidence: dict,
        probe_name: str,
        status: str,
        message: str,
    ) -> dict:
        """Add probe status to evidence dict."""
        return {
            **evidence,
            "probe_name": probe_name,
            "probe_status": status,
            "probe_message": message,
        }
