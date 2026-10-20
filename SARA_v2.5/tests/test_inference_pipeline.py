from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inference_pipeline import SARAInferencePipeline
from internal_judgment_model import (
    SARAInternalJudgmentModel,
    compute_judgment_input_digest,
)


REQUEST = {
    "request_id": "REQ-PIPE-1",
    "conversation_id": "CONV-1",
    "turn_id": "TURN-3",
    "content": "Sales rose after the campaign, therefore the campaign caused the increase.",
    "context": {"role": "assistant"},
}


def generate_for(status="INFERENCE_PRESENT", confidence="HIGH"):
    def generate(_rubric, payload, _timeout):
        inference = status == "INFERENCE_PRESENT"
        return {
            "request_id": payload["request_id"],
            "input_revision_digest": compute_judgment_input_digest(payload),
            "judgment_status": status,
            "verification_need": "REQUIRED" if inference else "NOT_REQUIRED",
            "external_check_need": "NOT_REQUIRED",
            "inference_types": ["CAUSAL"] if inference else [],
            "basis_spans": ["therefore the campaign caused the increase"] if inference else [],
            "rationale": "The conclusion goes beyond temporal sequence.",
            "uncertainty_reason": "Insufficient context." if status == "AMBIGUOUS" else "",
            "confidence": confidence,
            "premise_refs": [],
            "claim_refs": [],
            "evidence_ids": [],
            "provenance_ids": [],
        }
    return generate


def test_pipeline_executes_sara_verification_after_inference_detection():
    called = {"verify": 0, "precheck": 0}

    def verify(request, judgment, decision):
        called["verify"] += 1
        assert judgment["judgment_status"] == "INFERENCE_PRESENT"
        assert decision["activation_action"] == "SARA_SELECTIVE_VERIFICATION"
        return {"workflow": "test-verifier", "status": "PROPOSED"}

    def precheck(*_args):
        called["precheck"] += 1
        return {"status": "NEEDS_REVIEW"}

    model = SARAInternalJudgmentModel(
        generate_for(), model_id="sara-runtime", model_revision="test-double"
    )
    result = SARAInferencePipeline(
        model, run_selective_verification=verify, run_precheck=precheck
    ).process(REQUEST, timeout_seconds=1)

    assert called == {"verify": 1, "precheck": 0}
    assert result["pipeline_status"] == "ROUTE_EXECUTED"
    assert result["route_execution"]["execution_status"] == "SUCCEEDED"
    assert result["route_execution"]["output"]["status"] == "PROPOSED"
    assert result["is_evidence"] is False
    assert result["claim_truth_assessed"] is False


def test_pipeline_routes_ambiguous_judgment_to_precheck():
    called = {"verify": 0, "precheck": 0}

    def verify(*_args):
        called["verify"] += 1
        return {"status": "UNEXPECTED"}

    def precheck(_request, judgment, decision):
        called["precheck"] += 1
        assert judgment["judgment_status"] == "AMBIGUOUS"
        assert decision["activation_action"] == "SARA_PRECHECK_REVIEW"
        return {"status": "REVIEW_QUEUED"}

    model = SARAInternalJudgmentModel(
        generate_for("AMBIGUOUS", "MEDIUM"),
        model_id="sara-runtime", model_revision="test-double"
    )
    result = SARAInferencePipeline(
        model, run_selective_verification=verify, run_precheck=precheck
    ).process(REQUEST, timeout_seconds=1)

    assert called == {"verify": 0, "precheck": 1}
    assert result["route_execution"]["output"]["status"] == "REVIEW_QUEUED"


def test_pipeline_does_not_claim_completed_verification_from_proposal_output():
    model = SARAInternalJudgmentModel(
        generate_for(), model_id="sara-runtime", model_revision="test-double"
    )
    result = SARAInferencePipeline(
        model,
        run_selective_verification=lambda *_: {"status": "PROPOSED"},
        run_precheck=lambda *_: {"status": "REVIEW_QUEUED"},
    ).process(REQUEST, timeout_seconds=1)
    assert result["pipeline_status"] == "ROUTE_EXECUTED"
    assert result["route_execution"]["output"]["status"] == "PROPOSED"
    assert result["verification_result_is_callback_owned"] is True


def test_route_failure_is_not_misreported_as_success_or_negative_finding():
    def fail(*_args):
        raise RuntimeError("private details should not be returned")

    model = SARAInternalJudgmentModel(
        generate_for(), model_id="sara-runtime", model_revision="test-double"
    )
    result = SARAInferencePipeline(
        model, run_selective_verification=fail, run_precheck=lambda *_: {}
    ).process(REQUEST, timeout_seconds=1)

    assert result["pipeline_status"] == "ROUTE_NOT_COMPLETED"
    assert result["route_execution"]["execution_status"] == "FAILED"
    assert result["route_execution"]["error_code"] == "RuntimeError"
    assert "private details" not in str(result)
    assert result["claim_truth_assessed"] is False
