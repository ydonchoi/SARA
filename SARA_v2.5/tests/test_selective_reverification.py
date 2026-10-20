from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from selective_reverification import (
    DependencyEdge,
    plan_selective_reverification,
)


NODES = {
    "E1": "EVIDENCE",
    "P1": "PREMISE",
    "C1": "CLAIM",
    "C2": "CLAIM",
    "C3": "CLAIM",
}


def test_upstream_change_schedules_only_transitive_dependent_claims():
    result = plan_selective_reverification(
        nodes=NODES,
        changed_node_ids=["E1"],
        dependency_edges=[
            DependencyEdge("E1", "P1", "SUPPORTS"),
            DependencyEdge("P1", "C1", "SUPPORTS"),
            DependencyEdge("C1", "C2", "DERIVED_FROM"),
        ],
        prior_verification_statuses={
            "C1": "VERIFIED",
            "C2": "PARTIALLY_VERIFIED",
            "C3": "CONTRADICTED",
        },
    )

    assert result["impacted_claim_ids"] == ["C1", "C2"]
    assert result["unaffected_claim_ids"] == ["C3"]
    assert result["plan_status"] == "PLANNED_NOT_EXECUTED"
    assert result["is_evidence"] is False
    by_id = {item["claim_id"]: item for item in result["impacted_claims"]}
    assert by_id["C1"]["prior_verification_status"] == "VERIFIED"
    assert by_id["C2"]["prior_verification_status"] == "PARTIALLY_VERIFIED"
    assert by_id["C1"]["trigger"] == "DEPENDENCY_CHANGED"
    assert by_id["C1"]["triggering_changed_node_ids"] == ["E1"]
    assert all(item["execution_status"] == "PLANNED_NOT_EXECUTED" for item in by_id.values())


def test_directly_changed_claim_and_its_dependents_are_scheduled():
    result = plan_selective_reverification(
        nodes=NODES,
        changed_node_ids=["C1"],
        dependency_edges=[DependencyEdge("C1", "C2", "DERIVED_FROM")],
        prior_verification_statuses={"C1": "VERIFIED", "C2": "VERIFIED"},
    )

    by_id = {item["claim_id"]: item for item in result["impacted_claims"]}
    assert by_id["C1"]["trigger"] == "CLAIM_REVISION_CHANGED"
    assert by_id["C2"]["trigger"] == "DEPENDENCY_CHANGED"
    assert by_id["C1"]["review_state"] == "REQUIRES_REVERIFICATION"


def test_missing_prior_state_is_explicit_not_silently_assumed():
    result = plan_selective_reverification(
        nodes={"P1": "PREMISE", "C1": "CLAIM"},
        changed_node_ids=["P1"],
        dependency_edges=[DependencyEdge("P1", "C1", "SUPPORTS")],
        prior_verification_statuses={},
    )
    item = result["impacted_claims"][0]
    assert item["prior_status_known"] is False
    assert item["prior_verification_status"] is None
    assert item["review_state"] == "REQUIRES_REVERIFICATION"


def test_empty_change_set_produces_empty_plan():
    result = plan_selective_reverification(
        nodes=NODES,
        changed_node_ids=[],
        dependency_edges=[DependencyEdge("P1", "C1", "SUPPORTS")],
        prior_verification_statuses={},
    )
    assert result["impacted_claims"] == []
    assert result["impacted_claim_ids"] == []
    assert result["unaffected_claim_ids"] == ["C1", "C2", "C3"]


def test_dependency_cycles_terminate_and_keep_transitive_impact():
    result = plan_selective_reverification(
        nodes={"P1": "PREMISE", "C1": "CLAIM", "C2": "CLAIM"},
        changed_node_ids=["P1"],
        dependency_edges=[
            DependencyEdge("P1", "C1", "SUPPORTS"),
            DependencyEdge("C1", "C2", "DERIVED_FROM"),
            DependencyEdge("C2", "C1", "CHALLENGES"),
        ],
        prior_verification_statuses={},
    )
    assert result["impacted_claim_ids"] == ["C1", "C2"]


def test_unknown_changed_node_is_rejected():
    with pytest.raises(ValueError, match="CHANGED_NODE_UNKNOWN"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["MISSING"],
            dependency_edges=[],
            prior_verification_statuses={},
        )


def test_unknown_dependency_reference_is_rejected():
    with pytest.raises(ValueError, match="DEPENDENCY_EDGE_REFERENCES_UNKNOWN_NODE"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["E1"],
            dependency_edges=[DependencyEdge("E1", "MISSING", "SUPPORTS")],
            prior_verification_statuses={},
        )


def test_duplicate_dependency_edge_is_rejected():
    edge = DependencyEdge("P1", "C1", "SUPPORTS")
    with pytest.raises(ValueError, match="DUPLICATE_DEPENDENCY_EDGE"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["P1"],
            dependency_edges=[edge, edge],
            prior_verification_statuses={},
        )


def test_prior_status_must_target_claim_and_use_known_status():
    with pytest.raises(ValueError, match="PRIOR_STATUS_TARGET_NOT_CLAIM"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["P1"],
            dependency_edges=[],
            prior_verification_statuses={"P1": "VERIFIED"},
        )
    with pytest.raises(ValueError, match="INVALID_PRIOR_VERIFICATION_STATUS"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["P1"],
            dependency_edges=[],
            prior_verification_statuses={"C1": "CERTAIN"},
        )


def test_malformed_type_values_are_rejected_as_contract_errors():
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_NODE_TYPE"):
        plan_selective_reverification(
            nodes={"C1": []},
            changed_node_ids=[],
            dependency_edges=[],
            prior_verification_statuses={},
        )
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_RELATION"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["P1"],
            dependency_edges=[DependencyEdge("P1", "C1", [])],
            prior_verification_statuses={},
        )
    with pytest.raises(ValueError, match="INVALID_PRIOR_VERIFICATION_STATUS"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["P1"],
            dependency_edges=[],
            prior_verification_statuses={"C1": []},
        )


def test_invalid_dependency_relation_is_rejected():
    with pytest.raises(ValueError, match="INVALID_DEPENDENCY_RELATION"):
        plan_selective_reverification(
            nodes=NODES,
            changed_node_ids=["P1"],
            dependency_edges=[DependencyEdge("P1", "C1", "SUPPORTS_BUT_PROBABLY")],
            prior_verification_statuses={},
        )
