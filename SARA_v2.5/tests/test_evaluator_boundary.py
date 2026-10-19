from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evaluator_boundary import EvaluatorSignal, validate_evaluator_signal


def signal(**overrides):
    values = {
        "signal_id": "S1",
        "evaluator_id": "JEV",
        "evaluator_revision": "jev-1.2",
        "rubric_revision": "rubric-3",
        "input_revision_digest": "claim-rev-digest-1",
        "execution_status": "SUCCEEDED",
        "signal_status": "ISSUE_CANDIDATE",
        "rationale": "The inference appears stronger than the supplied premise.",
        "related_node_ids": ("C1", "P1"),
        "evidence_ids": ("E1",),
        "provenance_ids": ("EV-1",),
    }
    values.update(overrides)
    return EvaluatorSignal(**values)


def validate(item, **overrides):
    args = {
        "expected_input_revision_digest": "claim-rev-digest-1",
        "known_node_ids": {"C1", "P1"},
        "known_evidence_ids": {"E1"},
    }
    args.update(overrides)
    return validate_evaluator_signal(item, **args)


def test_issue_candidate_is_decision_support_not_evidence_or_claim_verification():
    result = validate(signal())
    assert result["signal_status"] == "ISSUE_CANDIDATE"
    assert result["execution_status"] == "SUCCEEDED"
    assert result["review_required"] is True
    assert result["is_evidence"] is False
    assert "claim_verification_status" not in result
    assert result["source"] == "SARA_EVALUATOR_SIGNAL"


def test_no_issue_reported_is_not_a_claim_truth_or_validity_verdict():
    result = validate(signal(
        signal_status="NO_ISSUE_REPORTED",
        rationale="No issue was reported by this evaluator under the supplied rubric.",
        related_node_ids=(),
        evidence_ids=(),
    ))
    assert result["review_required"] is False
    assert result["signal_status"] == "NO_ISSUE_REPORTED"
    assert result["is_evidence"] is False
    assert "claim_verification_status" not in result


@pytest.mark.parametrize(
    "execution_status",
    ["FAILED", "TIMEOUT", "INVALID_OUTPUT", "INCOMPLETE"],
)
def test_execution_failure_is_not_promoted_to_a_research_finding(execution_status):
    result = validate(signal(
        execution_status=execution_status,
        signal_status="NOT_AVAILABLE",
        rationale="",
        related_node_ids=(),
        evidence_ids=(),
    ))
    assert result["execution_status"] == execution_status
    assert result["signal_status"] == "NOT_AVAILABLE"
    assert result["review_required"] is True
    assert result["is_evidence"] is False
    assert "claim_verification_status" not in result


def test_failed_execution_cannot_emit_an_issue_candidate():
    with pytest.raises(ValueError, match="FAILED_EVALUATOR_CANNOT_EMIT_RESEARCH_SIGNAL"):
        validate(signal(
            execution_status="TIMEOUT",
            signal_status="ISSUE_CANDIDATE",
        ))


def test_successful_execution_cannot_mark_signal_not_available():
    with pytest.raises(ValueError, match="SUCCEEDED_EVALUATOR_SIGNAL_STATUS_REQUIRED"):
        validate(signal(signal_status="NOT_AVAILABLE"))


def test_stale_evaluator_input_digest_is_rejected():
    with pytest.raises(ValueError, match="EVALUATOR_INPUT_REVISION_MISMATCH"):
        validate(signal(input_revision_digest="old-claim-digest"))


def test_issue_candidate_requires_rationale_and_basis_reference():
    with pytest.raises(ValueError, match="EVALUATOR_CANDIDATE_REQUIRES_RATIONALE"):
        validate(signal(rationale=" "))
    with pytest.raises(ValueError, match="EVALUATOR_CANDIDATE_REQUIRES_BASIS_REFERENCE"):
        validate(signal(related_node_ids=(), evidence_ids=()))


def test_unknown_node_and_evidence_references_are_rejected():
    with pytest.raises(ValueError, match="EVALUATOR_REFERENCES_UNKNOWN_NODE"):
        validate(signal(related_node_ids=("C404",)))
    with pytest.raises(ValueError, match="EVALUATOR_REFERENCES_UNKNOWN_EVIDENCE"):
        validate(signal(evidence_ids=("E404",)))


def test_contract_and_input_identity_fields_are_required():
    with pytest.raises(ValueError, match="EVALUATOR_RUBRIC_REVISION_REQUIRED"):
        validate(signal(rubric_revision=" "))
    with pytest.raises(ValueError, match="EXPECTED_INPUT_DIGEST_REQUIRED"):
        validate(signal(), expected_input_revision_digest="")


def test_non_string_rationale_is_rejected_as_invalid_output_shape():
    with pytest.raises(ValueError, match="INVALID_EVALUATOR_RATIONALE"):
        validate(signal(rationale=None))
