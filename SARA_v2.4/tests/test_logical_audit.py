from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from logical_audit import (
    ArgumentEdge,
    ArgumentNode,
    LogicalAuditFinding,
    audit_conditional_inference,
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



def _conditional_inference(second_prop, second_negated, conclusion_prop, conclusion_negated):
    return audit_conditional_inference(
        antecedent="P",
        consequent="Q",
        second_premise_proposition=second_prop,
        second_premise_negated=second_negated,
        conclusion_proposition=conclusion_prop,
        conclusion_negated=conclusion_negated,
        premise_ids=("P1", "P2"),
        conclusion_id="C1",
    )


def test_modus_ponens_is_a_valid_form_without_establishing_truth():
    result = _conditional_inference("P", False, "Q", False)
    assert result["pattern"] == "MODUS_PONENS"
    assert result["formal_form_status"] == "VALID_FORM"
    assert result["premises_truth_status"] == "UNASSESSED"
    assert result["is_evidence"] is False


def test_modus_tollens_is_a_valid_form_without_establishing_truth():
    result = _conditional_inference("Q", True, "P", True)
    assert result["pattern"] == "MODUS_TOLLENS"
    assert result["formal_form_status"] == "VALID_FORM"


def test_affirming_consequent_is_reported_as_invalid_form():
    result = _conditional_inference("Q", False, "P", False)
    assert result["pattern"] == "AFFIRMING_CONSEQUENT"
    assert result["formal_form_status"] == "INVALID_FORM"
    assert result["finding"]["status"] == "SUBSTANTIATED"
    assert result["finding"]["category"] == "FORMAL_VALIDITY"
    assert result["conclusion_truth_status"] == "UNASSESSED"
    assert result["is_evidence"] is False


def test_denying_antecedent_is_reported_as_invalid_form():
    result = _conditional_inference("P", True, "Q", True)
    assert result["pattern"] == "DENYING_ANTECEDENT"
    assert result["formal_form_status"] == "INVALID_FORM"
    assert result["finding"]["status"] == "SUBSTANTIATED"


def test_unknown_conditional_form_is_left_unassessed():
    result = _conditional_inference("P", False, "P", False)
    assert result["pattern"] == "UNRECOGNIZED"
    assert result["formal_form_status"] == "UNASSESSED"
    assert result["review_status"] == "UNASSESSED"


def test_conditional_form_requires_distinct_atoms_and_node_ids():
    with pytest.raises(ValueError, match="CONDITIONAL_ANTECEDENT_AND_CONSEQUENT_MUST_DIFFER"):
        audit_conditional_inference(
            antecedent="P", consequent="P",
            second_premise_proposition="P", second_premise_negated=False,
            conclusion_proposition="P", conclusion_negated=False,
            premise_ids=("P1", "P2"), conclusion_id="C1",
        )



def test_conditional_form_rejects_non_boolean_negation_flags():
    with pytest.raises(ValueError, match="CONDITIONAL_NEGATION_FLAGS_MUST_BE_BOOLEAN"):
        audit_conditional_inference(
            antecedent="P", consequent="Q",
            second_premise_proposition="P", second_premise_negated="false",
            conclusion_proposition="Q", conclusion_negated=False,
            premise_ids=("P1", "P2"), conclusion_id="C1",
        )


def test_conditional_form_rejects_non_string_node_ids():
    with pytest.raises(ValueError, match="CONDITIONAL_PREMISE_IDS_REQUIRED"):
        audit_conditional_inference(
            antecedent="P", consequent="Q",
            second_premise_proposition="P", second_premise_negated=False,
            conclusion_proposition="Q", conclusion_negated=False,
            premise_ids=("P1", 2), conclusion_id="C1",
        )


def test_overlapping_cycles_with_distinct_member_sets_are_both_reported():
    result = validate_argument_graph(
        nodes=[
            ArgumentNode("A", "CLAIM", "Claim A."),
            ArgumentNode("B", "CLAIM", "Claim B."),
            ArgumentNode("C", "CLAIM", "Claim C."),
        ],
        edges=[
            ArgumentEdge("AB", "A", "B", "SUPPORTS"),
            ArgumentEdge("BC", "B", "C", "SUPPORTS"),
            ArgumentEdge("CA", "C", "A", "SUPPORTS"),
            ArgumentEdge("AC", "A", "C", "SUPPORTS"),
        ],
    )
    member_sets = {
        frozenset(finding["related_node_ids"])
        for finding in result["candidate_findings"]
    }
    assert member_sets == {
        frozenset({"A", "B", "C"}),
        frozenset({"A", "C"}),
    }
    assert all(
        finding["status"] == "CANDIDATE" and finding["is_evidence"] is False
        for finding in result["candidate_findings"]
    )
