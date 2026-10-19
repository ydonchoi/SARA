from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from internal_judgment_model import (
    InternalJudgmentError,
    SARAInternalJudgmentModel,
    compute_judgment_input_digest,
)


REQUEST = {
    "request_id": "REQ-1",
    "conversation_id": "CONV-1",
    "turn_id": "TURN-7",
    "content": "The outcome fell after the policy, so the policy caused the decline.",
    "context": {"speaker": "assistant"},
    "reference_catalog": {
        "premise_refs": ["P1"],
        "claim_refs": ["C1"],
        "evidence_ids": ["E1"],
        "provenance_ids": ["SRC-1"],
    },
}


def output_for(request, **overrides):
    result = {
        "request_id": request["request_id"],
        "input_revision_digest": compute_judgment_input_digest(request),
        "judgment_status": "INFERENCE_PRESENT",
        "verification_need": "REQUIRED",
        "external_check_need": "NOT_REQUIRED",
        "inference_types": ["CAUSAL"],
        "basis_spans": ["so the policy caused the decline"],
        "rationale": "Temporal order alone does not establish causation.",
        "uncertainty_reason": "",
        "confidence": "HIGH",
        "premise_refs": ["P1"],
        "claim_refs": ["C1"],
        "evidence_ids": ["E1"],
        "provenance_ids": ["SRC-1"],
    }
    result.update(overrides)
    return result


def model(generate):
    return SARAInternalJudgmentModel(
        generate,
        model_id="sara-runtime",
        model_revision="runtime-test-double",
        rubric_revision="rubric-0.1",
    )


def test_internal_judgment_uses_sara_runtime_and_binds_result_to_input():
    captured = {}

    def generate(system_instruction, payload, timeout_seconds):
        captured["system_instruction"] = system_instruction
        captured["payload"] = payload
        captured["timeout"] = timeout_seconds
        return output_for(payload)

    result = model(generate).judge(REQUEST, timeout_seconds=2)
    assert captured["payload"]["input_revision_digest"] == result["input_revision_digest"]
    assert "SARA's internal inference-judgment component" in captured["system_instruction"]
    assert captured["timeout"] == 2
    assert result["judgment_status"] == "INFERENCE_PRESENT"
    assert result["source"] == "SARA_INTERNAL_JEV_STYLE_JUDGMENT"
    assert result["is_evidence"] is False
    assert result["claim_truth_assessed"] is False
    assert "evaluator provider" not in result


def test_no_inference_judgment_is_not_a_truth_verdict():
    def generate(_system, payload, _timeout):
        return output_for(
            payload,
            judgment_status="NO_INFERENCE_DETECTED",
            verification_need="NOT_REQUIRED",
            external_check_need="NOT_REQUIRED",
            inference_types=[],
            basis_spans=[],
            rationale="The turn only restates an attributed sentence.",
            premise_refs=[],
            claim_refs=[],
            evidence_ids=[],
            provenance_ids=[],
            confidence="HIGH",
        )

    result = model(generate).judge(REQUEST, timeout_seconds=1)
    assert result["judgment_status"] == "NO_INFERENCE_DETECTED"
    assert result["review_required"] is False
    assert result["is_evidence"] is False
    assert result["claim_truth_assessed"] is False


def test_ambiguous_judgment_requires_uncertainty_and_cannot_claim_high_confidence():
    def generate(_system, payload, _timeout):
        return output_for(
            payload,
            judgment_status="AMBIGUOUS",
            inference_types=[],
            basis_spans=[],
            uncertainty_reason="The referenced antecedent is missing.",
            confidence="MEDIUM",
        )

    result = model(generate).judge(REQUEST, timeout_seconds=1)
    assert result["judgment_status"] == "AMBIGUOUS"
    assert result["review_required"] is True


def test_stale_request_digest_is_rejected_before_model_invocation():
    called = False

    def generate(*_args):
        nonlocal called
        called = True
        return {}

    try:
        model(generate).judge(
            {**REQUEST, "input_revision_digest": "stale"},
            timeout_seconds=1,
        )
    except InternalJudgmentError as exc:
        assert str(exc) == "JUDGMENT_INPUT_REVISION_MISMATCH"
    else:
        raise AssertionError("stale digest must be rejected")
    assert called is False


def test_timeout_is_not_misreported_as_no_inference():
    def generate(*_args):
        raise TimeoutError()

    result = model(generate).judge(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "TIMEOUT"
    assert result["judgment_status"] == "NOT_ASSESSED"
    assert result["review_required"] is True
    assert result["is_evidence"] is False


def test_malformed_semantic_output_fails_closed():
    def generate(_system, payload, _timeout):
        return output_for(payload, judgment_status="CERTAINLY_TRUE")

    result = model(generate).judge(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "INVALID_OUTPUT"
    assert result["judgment_status"] == "NOT_ASSESSED"
    assert result["review_required"] is True


def test_unknown_reference_is_rejected_as_invalid_output():
    def generate(_system, payload, _timeout):
        return output_for(payload, evidence_ids=["FABRICATED-EVIDENCE"])

    result = model(generate).judge(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "INVALID_OUTPUT"
    assert result["judgment_status"] == "NOT_ASSESSED"
    assert result["review_required"] is True


def test_basis_span_must_be_verbatim_from_input():
    def generate(_system, payload, _timeout):
        return output_for(payload, basis_spans=["invented words not in the input"])

    result = model(generate).judge(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "INVALID_OUTPUT"
    assert result["judgment_status"] == "NOT_ASSESSED"
