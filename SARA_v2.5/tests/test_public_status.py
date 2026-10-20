from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
V25_ROOT = REPO_ROOT / "SARA_v2.5"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(V25_ROOT))

from public_status import project_public_status


def base_result():
    return {
        "pipeline_status": "ROUTE_EXECUTED",
        "judgment": {
            "judgment_status": "INFERENCE_PRESENT",
            "rationale": "PRIVATE INTERNAL RATIONALE",
            "basis_spans": ["PRIVATE SOURCE SPAN"],
            "claim_refs": ["PRIVATE-CLAIM-ID"],
        },
        "activation_decision": {
            "activation_action": "SARA_SELECTIVE_VERIFICATION",
            "reason_code": "INFERENCE_DETECTED",
        },
        "route_execution": {
            "execution_status": "SUCCEEDED",
            "output": {
                "status": "SUCCEEDED",
                "provider_payload": "PRIVATE PROVIDER DATA",
                "raw_error": "PRIVATE STACK TRACE",
            },
        },
        "verification_provider_invoked": True,
        "conversation_id": "PRIVATE-CONVERSATION-ID",
        "turn_id": "PRIVATE-TURN-ID",
    }


def test_public_projection_is_allowlisted_and_does_not_expose_internal_fields():
    result = project_public_status(base_result())

    assert set(result) == {
        "schema_version",
        "status",
        "verification_started",
        "reason_code",
        "claim_truth_established",
    }
    serialized = repr(result)
    for secret in (
        "PRIVATE INTERNAL RATIONALE",
        "PRIVATE SOURCE SPAN",
        "PRIVATE-CLAIM-ID",
        "PRIVATE PROVIDER DATA",
        "PRIVATE STACK TRACE",
        "PRIVATE-CONVERSATION-ID",
        "PRIVATE-TURN-ID",
    ):
        assert secret not in serialized
    assert result["status"] == "VERIFICATION_COMPLETED"
    assert result["verification_started"] is True
    assert result["claim_truth_established"] is False


def test_ambiguous_precheck_maps_to_review_without_leaking_raw_reason():
    result = base_result()
    result["activation_decision"] = {
        "activation_action": "SARA_PRECHECK_REVIEW",
        "reason_code": "MODEL_GENERATION_FAILED",
        "internal_note": "DO NOT DISCLOSE",
    }
    result["route_execution"]["output"] = {"status": "REVIEW_QUEUED"}

    projected = project_public_status(result)
    assert projected["status"] == "REVIEW_REQUIRED"
    assert projected["reason_code"] == "ASSESSMENT_UNAVAILABLE"
    assert "internal_note" not in projected
    assert "DO NOT DISCLOSE" not in repr(projected)


def test_failed_verifier_maps_to_safe_failure():
    result = base_result()
    result["route_execution"]["execution_status"] = "FAILED"
    result["route_execution"]["output"] = {
        "status": "FAILED",
        "error_code": "SARA_VERIFY_CLAIM_STATUS_NOT_SUCCEEDED",
        "error": "provider exception with sensitive detail",
    }

    projected = project_public_status(result)
    assert projected["status"] == "FAILED"
    assert projected["reason_code"] == "VERIFICATION_FAILED"
    assert "sensitive detail" not in repr(projected)


def test_partially_failed_route_never_maps_to_verification_completed():
    result = base_result()
    result["route_execution"]["output"] = {
        "status": "PARTIALLY_FAILED",
        "verification_results": [
            {"claim_id": "PRIVATE-CLAIM-ID", "execution_status": "SUCCEEDED"},
            {"claim_id": "PRIVATE-CLAIM-ID-2", "execution_status": "FAILED",
             "error_code": "PRIVATE_ERROR"},
        ],
    }

    projected = project_public_status(result)
    assert projected["status"] == "FAILED"
    assert projected["reason_code"] == "VERIFICATION_FAILED"
    assert "PRIVATE-CLAIM-ID" not in repr(projected)
    assert "PRIVATE_ERROR" not in repr(projected)


def test_malformed_verification_result_fails_safe():
    result = base_result()
    result["route_execution"]["output"] = {
        "status": "SUCCEEDED",
        "verification_results": [{"unexpected": "PRIVATE"}],
    }

    projected = project_public_status(result)
    assert projected["status"] == "FAILED"
    assert projected["reason_code"] == "VERIFICATION_FAILED"
    assert "PRIVATE" not in repr(projected)


def test_no_trigger_does_not_claim_verification_was_performed():
    result = base_result()
    result["pipeline_status"] = "NO_ROUTE_REQUIRED"
    result["activation_decision"] = {"activation_action": "NO_TRIGGER"}

    projected = project_public_status(result)
    assert projected["status"] == "NOT_ASSESSED"
    assert projected["verification_started"] is False
    assert projected["claim_truth_established"] is False


def test_malformed_and_unknown_states_fail_safe():
    assert project_public_status(None)["status"] == "FAILED"

    result = base_result()
    result["activation_decision"] = {
        "activation_action": "UNKNOWN_ACTION",
        "reason_code": "UNTRUSTED RAW REASON",
    }
    projected = project_public_status(result)
    assert projected["status"] == "REVIEW_REQUIRED"
    assert projected["reason_code"] == "STATUS_UNAVAILABLE"
    assert "UNTRUSTED RAW REASON" not in repr(projected)
