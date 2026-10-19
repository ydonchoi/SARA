from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logical_audit import (
    ArgumentEdge,
    ArgumentNode,
    LogicalAuditFinding,
    validate_argument_graph,
    validate_finding,
)


def test_acyclic_graph_is_structurally_valid_without_claiming_semantic_validity():
    result = validate_argument_graph(
        nodes=[
            ArgumentNode("P1", "PREMISE", "All mammals are warm-blooded."),
            ArgumentNode("C1", "CLAIM", "Whales are warm-blooded."),
        ],
        edges=[ArgumentEdge("A1", "P1", "C1", "SUPPORTS", "DEDUCTIVE")],
    )
    assert result["graph_status"] == "STRUCTURALLY_VALID"
    assert result["candidate_findings"] == []
    assert result["semantic_audit_status"] == "NOT_PERFORMED"
    assert result["is_evidence"] is False


def test_support_cycle_is_candidate_not_confirmed_fallacy():
    result = validate_argument_graph(
        nodes=[
            ArgumentNode("C1", "CLAIM", "Claim one."),
            ArgumentNode("C2", "CLAIM", "Claim two."),
        ],
        edges=[
            ArgumentEdge("A1", "C1", "C2", "SUPPORTS"),
            ArgumentEdge("A2", "C2", "C1", "SUPPORTS"),
        ],
    )
    assert len(result["candidate_findings"]) == 1
    finding = result["candidate_findings"][0]
    assert finding["category"] == "CIRCULAR_REASONING"
    assert finding["status"] == "CANDIDATE"
    assert finding["is_evidence"] is False


def test_unknown_edge_reference_is_rejected():
    with pytest.raises(ValueError, match="ARGUMENT_EDGE_REFERENCES_UNKNOWN_NODE"):
        validate_argument_graph(
            nodes=[ArgumentNode("C1", "CLAIM", "Claim.")],
            edges=[ArgumentEdge("A1", "P1", "C1", "SUPPORTS")],
        )


def test_duplicate_node_id_is_rejected():
    with pytest.raises(ValueError, match="DUPLICATE_ARGUMENT_NODE_ID"):
        validate_argument_graph(
            nodes=[
                ArgumentNode("C1", "CLAIM", "First."),
                ArgumentNode("C1", "PREMISE", "Duplicate."),
            ],
            edges=[],
        )


def test_substantiated_finding_requires_rationale_and_basis():
    finding = LogicalAuditFinding(
        finding_id="F1",
        target_id="C1",
        category="NON_SEQUITUR",
        status="SUBSTANTIATED",
    )
    with pytest.raises(ValueError, match="SUBSTANTIATED_FINDING_REQUIRES_RATIONALE"):
        validate_finding(finding, node_ids={"C1"})


def test_finding_must_reference_known_evidence_and_nodes():
    finding = LogicalAuditFinding(
        finding_id="F1",
        target_id="C1",
        category="EVIDENCE_SCOPE_MISMATCH",
        status="CANDIDATE",
        related_node_ids=("P1",),
        evidence_ids=("E404",),
        rationale="The evidence may have a narrower scope.",
    )
    with pytest.raises(ValueError, match="FINDING_EVIDENCE_UNKNOWN"):
        validate_finding(finding, node_ids={"C1", "P1"}, evidence_ids={"E1"})
