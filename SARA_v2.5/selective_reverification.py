"""SARA v2.5 prototype: dependency-aware selective re-verification planning.

This module computes which claims may be affected by changed upstream inputs.
It plans review only; it does not execute verification or mutate claim status.
DependencyEdge direction is explicit: upstream_id -> dependent_id.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Iterable, Mapping

NODE_TYPES = {"CLAIM", "PREMISE", "EVIDENCE", "METHOD"}
DEPENDENCY_RELATIONS = {"SUPPORTS", "CHALLENGES", "DERIVED_FROM"}
VERIFICATION_STATUSES = {
    "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"
}


@dataclass(frozen=True)
class DependencyEdge:
    upstream_id: str
    dependent_id: str
    relation: str


def plan_selective_reverification(
    *,
    nodes: Mapping[str, str],
    changed_node_ids: Iterable[str],
    dependency_edges: Iterable[DependencyEdge],
    prior_verification_statuses: Mapping[str, str],
) -> dict:
    """Return a deterministic re-verification plan for impacted claim nodes."""
    if not isinstance(nodes, Mapping):
        raise ValueError("NODES_MUST_BE_MAPPING")

    node_types = dict(nodes)
    for node_id, node_type in node_types.items():
        if not isinstance(node_id, str) or not node_id.strip():
            raise ValueError("DEPENDENCY_NODE_ID_REQUIRED")
        if not isinstance(node_type, str) or node_type not in NODE_TYPES:
            raise ValueError("INVALID_DEPENDENCY_NODE_TYPE")

    changed = tuple(changed_node_ids)
    if any(not isinstance(node_id, str) or not node_id.strip() for node_id in changed):
        raise ValueError("CHANGED_NODE_ID_REQUIRED")
    if len(set(changed)) != len(changed):
        raise ValueError("DUPLICATE_CHANGED_NODE_ID")
    unknown_changed = set(changed) - set(node_types)
    if unknown_changed:
        raise ValueError("CHANGED_NODE_UNKNOWN")

    if not isinstance(prior_verification_statuses, Mapping):
        raise ValueError("PRIOR_VERIFICATION_STATUSES_MUST_BE_MAPPING")
    for claim_id, status in prior_verification_statuses.items():
        if claim_id not in node_types or node_types[claim_id] != "CLAIM":
            raise ValueError("PRIOR_STATUS_TARGET_NOT_CLAIM")
        if not isinstance(status, str) or status not in VERIFICATION_STATUSES:
            raise ValueError("INVALID_PRIOR_VERIFICATION_STATUS")

    adjacency = {node_id: set() for node_id in node_types}
    seen_edges = set()
    for edge in dependency_edges:
        if not isinstance(edge.upstream_id, str) or not edge.upstream_id.strip():
            raise ValueError("DEPENDENCY_UPSTREAM_ID_REQUIRED")
        if not isinstance(edge.dependent_id, str) or not edge.dependent_id.strip():
            raise ValueError("DEPENDENCY_DEPENDENT_ID_REQUIRED")
        if edge.upstream_id not in node_types or edge.dependent_id not in node_types:
            raise ValueError("DEPENDENCY_EDGE_REFERENCES_UNKNOWN_NODE")
        if not isinstance(edge.relation, str) or edge.relation not in DEPENDENCY_RELATIONS:
            raise ValueError("INVALID_DEPENDENCY_RELATION")
        edge_key = (edge.upstream_id, edge.dependent_id, edge.relation)
        if edge_key in seen_edges:
            raise ValueError("DUPLICATE_DEPENDENCY_EDGE")
        seen_edges.add(edge_key)
        adjacency[edge.upstream_id].add(edge.dependent_id)

    # Track every changed root that can reach each node. Pairwise visitation
    # terminates even if the incoming dependency graph contains a cycle.
    roots_by_node: dict[str, set[str]] = {node_id: set() for node_id in node_types}
    queue = deque()
    for root in changed:
        roots_by_node[root].add(root)
        queue.append((root, root))
    visited_pairs = set()
    while queue:
        current, root = queue.popleft()
        pair = (current, root)
        if pair in visited_pairs:
            continue
        visited_pairs.add(pair)
        for dependent in sorted(adjacency[current]):
            if root not in roots_by_node[dependent]:
                roots_by_node[dependent].add(root)
                queue.append((dependent, root))

    impacted = []
    for claim_id in sorted(node_id for node_id, kind in node_types.items() if kind == "CLAIM"):
        roots = roots_by_node[claim_id]
        if not roots:
            continue
        direct = claim_id in changed
        impacted.append({
            "claim_id": claim_id,
            "prior_verification_status": prior_verification_statuses.get(claim_id),
            "prior_status_known": claim_id in prior_verification_statuses,
            "review_state": "REQUIRES_REVERIFICATION",
            "trigger": "CLAIM_REVISION_CHANGED" if direct else "DEPENDENCY_CHANGED",
            "triggering_changed_node_ids": sorted(roots),
            "execution_status": "PLANNED_NOT_EXECUTED",
            "is_evidence": False,
        })

    return {
        "plan_status": "PLANNED_NOT_EXECUTED",
        "changed_node_ids": sorted(changed),
        "impacted_claims": impacted,
        "impacted_claim_ids": [item["claim_id"] for item in impacted],
        "unaffected_claim_ids": sorted(
            node_id for node_id, kind in node_types.items()
            if kind == "CLAIM" and not roots_by_node[node_id]
        ),
        "source": "SARA_SELECTIVE_REVERIFICATION_PLANNER",
        "is_evidence": False,
    }
