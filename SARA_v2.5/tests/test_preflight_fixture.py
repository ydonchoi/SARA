import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from claim_identity import ClaimRevision, assess_verification_reuse
from conflict_adjudication import EvidencePosition, adjudicate_evidence_conflict
from evaluator_boundary import EvaluatorSignal, validate_evaluator_signal


FIXTURE = Path(__file__).resolve().parents[1] / "benchmark" / "preflight_cases.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_preflight_seed_set_is_explicitly_draft_not_gold():
    data = load_fixture()
    assert data["status"] == "DRAFT_NOT_INDEPENDENTLY_ADJUDICATED"
    assert all(case["label_status"] == "DRAFT" for case in data["cases"])


def test_preflight_case_ids_are_unique_and_outcomes_are_explicit():
    data = load_fixture()
    cases = data["cases"]
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert all(
        any(key in case for key in (
            "expected_action",
            "expected_review_state",
            "expected_conflict_status",
            "expected_execution_status",
            "expected_review_required",
        ))
        for case in cases
    )


def test_preflight_covers_logical_audit_identity_and_evidence_conflict():
    data = load_fixture()
    suites = {case["suite"] for case in data["cases"]}
    assert suites == {"logical_audit", "claim_identity", "evidence_conflict", "evaluator_boundary"}


def test_claim_identity_cases_bind_verification_contract_revision():
    data = load_fixture()
    cases = [case for case in data["cases"] if case["suite"] == "claim_identity"]
    assert cases
    assert all(case.get("current_contract_revision") for case in cases)
    assert all(
        case.get("prior_binding", {}).get("verification_contract_revision")
        for case in cases
    )
    contract_drift = next(case for case in cases if case["case_id"] == "CV-002")
    assert contract_drift["current_contract_revision"] != (
        contract_drift["prior_binding"]["verification_contract_revision"]
    )
    assert contract_drift["expected_review_state"] == "REQUIRES_REVERIFICATION"
    assert contract_drift["expected_reuse_allowed"] is False


def test_claim_identity_preflight_cases_execute_against_revision_guard():
    data = load_fixture()
    cases = [case for case in data["cases"] if case["suite"] == "claim_identity"]
    for case in cases:
        revision_data = case["current_revision"]
        revision = ClaimRevision(
            claim_id=revision_data["claim_id"],
            revision_id=revision_data["revision_id"],
            text=revision_data["text"],
            scope_json=json.dumps(
                revision_data["scope"], ensure_ascii=False, sort_keys=True,
                separators=(",", ":")
            ),
            content_digest=revision_data["content_digest"],
        )
        result = assess_verification_reuse(
            revision=revision,
            prior_binding=case["prior_binding"],
            current_verifier_revision=case["current_verifier_revision"],
            current_contract_revision=case["current_contract_revision"],
            current_evidence_digest=case["current_evidence_digest"],
        )
        assert result["review_state"] == case["expected_review_state"], case["case_id"]
        assert result["reuse_allowed"] is case["expected_reuse_allowed"], case["case_id"]


def test_evidence_conflict_preflight_cases_execute_against_adjudicator():
    data = load_fixture()
    cases = [case for case in data["cases"] if case["suite"] == "evidence_conflict"]
    for case in cases:
        positions = [
            EvidencePosition(**item) for item in case["evidence_positions"]
        ]
        result = adjudicate_evidence_conflict(
            claim_id=case["claim_id"],
            evidence_positions=positions,
        )
        assert result["conflict_status"] == case["expected_conflict_status"], case["case_id"]
        assert result["claim_verification_status"] == (
            case["expected_claim_verification_status"]
        ), case["case_id"]


def test_supported_preflight_support_cycle_returns_candidate_only():
    data = load_fixture()
    case = next(item for item in data["cases"] if item["case_id"] == "LA-005")
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "SARA_v2.4"))
    from logical_audit import ArgumentEdge, ArgumentNode, validate_argument_graph

    result = validate_argument_graph(
        nodes=[ArgumentNode(**node) for node in case["nodes"]],
        edges=[ArgumentEdge(**edge) for edge in case["edges"]],
    )
    assert case["expected_action"] == "CANDIDATE_ONLY"
    assert result["semantic_audit_status"] == "NOT_PERFORMED"
    assert len(result["candidate_findings"]) == 1
    assert result["candidate_findings"][0]["category"] == "CIRCULAR_REASONING"
    assert result["candidate_findings"][0]["status"] == "CANDIDATE"


def test_evaluator_boundary_preflight_cases_execute_against_result_contract():
    data = load_fixture()
    cases = [case for case in data["cases"] if case["suite"] == "evaluator_boundary"]
    assert cases
    for case in cases:
        evaluator_signal = EvaluatorSignal(**{
            **case["signal"],
            "related_node_ids": tuple(case["signal"].get("related_node_ids", [])),
            "evidence_ids": tuple(case["signal"].get("evidence_ids", [])),
            "provenance_ids": tuple(case["signal"].get("provenance_ids", [])),
        })
        result = validate_evaluator_signal(
            evaluator_signal,
            expected_input_revision_digest=evaluator_signal.input_revision_digest,
        )
        assert result["execution_status"] == case["expected_execution_status"]
        assert result["signal_status"] == case["expected_signal_status"]
        assert result["review_required"] is case["expected_review_required"]
        assert result["is_evidence"] is case["expected_is_evidence"]


def test_conflict_cases_never_promote_claim_truth_status():
    data = load_fixture()
    conflict_cases = [
        case for case in data["cases"] if case["suite"] == "evidence_conflict"
    ]
    assert len(conflict_cases) >= 3
    assert all(
        case["expected_claim_verification_status"] == "UNASSESSED"
        for case in conflict_cases
    )
