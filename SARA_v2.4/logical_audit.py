"""SARA v2.4 logical-audit contract and structural argument checks.

The deterministic checks in this module validate graph integrity and flag
support/dependency cycles for review. They do not prove a fallacy, evaluate the
truth of a premise, or substitute for a semantic evaluator or human reviewer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

NODE_TYPES = {"CLAIM", "PREMISE"}
EDGE_RELATIONS = {"SUPPORTS", "CHALLENGES", "DERIVES_FROM"}
INFERENCE_TYPES = {"DEDUCTIVE", "INDUCTIVE", "ABDUCTIVE", "CAUSAL", "ANALOGICAL", "UNKNOWN"}
FINDING_CATEGORIES = {
    "FORMAL_VALIDITY",
    "INFERENCE_STRENGTH",
    "CAUSAL_INFERENCE",
    "GENERALIZATION",
    "CONCEPT_EQUIVOCATION",
    "CIRCULAR_REASONING",
    "NON_SEQUITUR",
    "EVIDENCE_SCOPE_MISMATCH",
    "ALTERNATIVE_EXPLANATION",
    "OTHER",
}
FINDING_STATUSES = {"CANDIDATE", "SUBSTANTIATED", "REJECTED", "UNASSESSED"}
SEVERITIES = {"CRITICAL", "MATERIAL", "MINOR", "UNASSESSED"}


@dataclass(frozen=True)
class ArgumentNode:
    node_id: str
    node_type: str
    text: str


@dataclass(frozen=True)
class ArgumentEdge:
    edge_id: str
    source_id: str
    target_id: str
    relation: str
    inference_type: str = "UNKNOWN"


@dataclass(frozen=True)
class LogicalAuditFinding:
    finding_id: str
    target_id: str
    category: str
    status: str
    severity: str = "UNASSESSED"
    related_node_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    rationale: str = ""
    counterexample_or_alternative: str = ""
    assessor_id: str = ""


def validate_finding(
    finding: LogicalAuditFinding,
    *,
    node_ids: Iterable[str],
    evidence_ids: Iterable[str] = (),
) -> dict:
    """Validate an audit record; a finding is a decision-support signal, not evidence."""
    known_nodes = set(node_ids)
    known_evidence = set(evidence_ids)
    if not finding.finding_id or not finding.finding_id.strip():
        raise ValueError("FINDING_ID_REQUIRED")
    if finding.target_id not in known_nodes:
        raise ValueError("FINDING_TARGET_UNKNOWN")
    if finding.category not in FINDING_CATEGORIES:
        raise ValueError("INVALID_LOGICAL_FINDING_CATEGORY")
    if finding.status not in FINDING_STATUSES:
        raise ValueError("INVALID_LOGICAL_FINDING_STATUS")
    if finding.severity not in SEVERITIES:
        raise ValueError("INVALID_LOGICAL_FINDING_SEVERITY")
    if any(node_id not in known_nodes for node_id in finding.related_node_ids):
        raise ValueError("FINDING_RELATED_NODE_UNKNOWN")
    if any(evidence_id not in known_evidence for evidence_id in finding.evidence_ids):
        raise ValueError("FINDING_EVIDENCE_UNKNOWN")
    if finding.status == "SUBSTANTIATED":
        if not finding.rationale.strip():
            raise ValueError("SUBSTANTIATED_FINDING_REQUIRES_RATIONALE")
        if not finding.related_node_ids and not finding.evidence_ids:
            raise ValueError("SUBSTANTIATED_FINDING_REQUIRES_BASIS_REFERENCE")
    result = asdict(finding)
    result["source"] = "SARA_LOGICAL_AUDIT"
    result["is_evidence"] = False
    return result


def validate_argument_graph(
    nodes: Iterable[ArgumentNode],
    edges: Iterable[ArgumentEdge],
) -> dict:
    """Check references and return candidate findings for directed support cycles.

    A cycle is a structural warning only: an evaluator must inspect the actual
    propositions before calling it circular reasoning.
    """
    node_list = tuple(nodes)
    edge_list = tuple(edges)
    node_map = {}
    for node in node_list:
        if not node.node_id or not node.node_id.strip():
            raise ValueError("ARGUMENT_NODE_ID_REQUIRED")
        if not node.text or not node.text.strip():
            raise ValueError("ARGUMENT_NODE_TEXT_REQUIRED")
        if node.node_type not in NODE_TYPES:
            raise ValueError("INVALID_ARGUMENT_NODE_TYPE")
        if node.node_id in node_map:
            raise ValueError("DUPLICATE_ARGUMENT_NODE_ID")
        node_map[node.node_id] = node

    edge_ids = set()
    adjacency = {node_id: set() for node_id in node_map}
    for edge in edge_list:
        if not edge.edge_id or not edge.edge_id.strip():
            raise ValueError("ARGUMENT_EDGE_ID_REQUIRED")
        if edge.edge_id in edge_ids:
            raise ValueError("DUPLICATE_ARGUMENT_EDGE_ID")
        edge_ids.add(edge.edge_id)
        if edge.source_id not in node_map or edge.target_id not in node_map:
            raise ValueError("ARGUMENT_EDGE_REFERENCES_UNKNOWN_NODE")
        if edge.relation not in EDGE_RELATIONS:
            raise ValueError("INVALID_ARGUMENT_EDGE_RELATION")
        if edge.inference_type not in INFERENCE_TYPES:
            raise ValueError("INVALID_INFERENCE_TYPE")
        if edge.relation in {"SUPPORTS", "DERIVES_FROM"}:
            adjacency[edge.source_id].add(edge.target_id)

    cycles = _find_cycles(adjacency)
    candidate_findings = []
    for index, cycle in enumerate(cycles, start=1):
        target_id = cycle[-1]
        finding = LogicalAuditFinding(
            finding_id=f"STRUCTURAL-CYCLE-{index}",
            target_id=target_id,
            category="CIRCULAR_REASONING",
            status="CANDIDATE",
            severity="MATERIAL",
            related_node_ids=tuple(cycle[:-1]),
            rationale=(
                "A directed support/dependency cycle exists in the graph. "
                "This is a review candidate, not proof of a semantic fallacy."
            ),
        )
        candidate_findings.append(
            validate_finding(finding, node_ids=node_map.keys())
        )

    return {
        "graph_status": "STRUCTURALLY_VALID",
        "node_ids": sorted(node_map),
        "edge_ids": sorted(edge_ids),
        "candidate_findings": candidate_findings,
        "semantic_audit_status": "NOT_PERFORMED",
        "source": "SARA_LOGICAL_AUDIT",
        "is_evidence": False,
    }


def _find_cycles(adjacency: dict[str, set[str]]) -> list[tuple[str, ...]]:
    """Return deterministic cycle node paths, deduplicated by member set."""
    visited = set()
    stack: list[str] = []
    active_positions: dict[str, int] = {}
    cycles: dict[tuple[str, ...], tuple[str, ...]] = {}

    def visit(node_id: str) -> None:
        if node_id in active_positions:
            cycle = tuple(stack[active_positions[node_id]:] + [node_id])
            key = tuple(sorted(set(cycle)))
            cycles.setdefault(key, cycle)
            return
        if node_id in visited:
            return
        visited.add(node_id)
        active_positions[node_id] = len(stack)
        stack.append(node_id)
        for target_id in sorted(adjacency[node_id]):
            visit(target_id)
        stack.pop()
        active_positions.pop(node_id, None)

    for node_id in sorted(adjacency):
        visit(node_id)
    return [cycles[key] for key in sorted(cycles)]
