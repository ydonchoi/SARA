from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from inference_trigger import decide_sara_activation


DIGEST = "a" * 64


def judgment(status="INFERENCE_PRESENT", confidence="HIGH", execution="SUCCEEDED", digest=DIGEST):
    return {
        "execution_status": execution,
        "judgment_status": status,
        "verification_need": "REQUIRED" if status == "INFERENCE_PRESENT" else "NOT_REQUIRED",
        "external_check_need": "NOT_REQUIRED",
        "confidence": confidence,
        "input_revision_digest": digest,
        "is_evidence": False,
        "claim_truth_assessed": False,
    }


def test_detected_inference_triggers_selective_sara_verification():
    result = decide_sara_activation(judgment(), expected_input_revision_digest=DIGEST)
    assert result["activation_action"] == "SARA_SELECTIVE_VERIFICATION"
    assert result["activation_triggered"] is True
    assert result["scope"] == "DIALOGUE_VERIFICATION_ROUTING"
    assert result["other_verification_routes_untouched"] is True
    assert result["claim_truth_assessed"] is False
    assert result["is_evidence"] is False


def test_clear_no_inference_decision_does_not_trigger_inference_path():
    result = decide_sara_activation(
        judgment("NO_INFERENCE_DETECTED", "HIGH"),
        expected_input_revision_digest=DIGEST,
    )
    assert result["activation_action"] == "NO_INFERENCE_TRIGGER"
    assert result["activation_triggered"] is False
    assert result["other_verification_routes_untouched"] is True


def test_ambiguous_judgment_routes_to_precheck_not_silent_noop():
    result = decide_sara_activation(
        judgment("AMBIGUOUS", "MEDIUM"),
        expected_input_revision_digest=DIGEST,
    )
    assert result["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["review_required"] is True


def test_low_confidence_no_inference_routes_to_precheck():
    result = decide_sara_activation(
        judgment("NO_INFERENCE_DETECTED", "LOW"),
        expected_input_revision_digest=DIGEST,
    )
    assert result["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["activation_triggered"] is True


def test_failed_judgment_routes_to_precheck_not_false_negative():
    result = decide_sara_activation(
        judgment("NOT_ASSESSED", "UNASSESSED", "TIMEOUT"),
        expected_input_revision_digest=DIGEST,
    )
    assert result["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["reason_code"] == "JUDGMENT_UNAVAILABLE_OR_INVALID"


def test_stale_judgment_digest_routes_to_precheck():
    result = decide_sara_activation(
        judgment(digest="b" * 64),
        expected_input_revision_digest=DIGEST,
    )
    assert result["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["reason_code"] == "JUDGMENT_INPUT_REVISION_MISMATCH"


def test_missing_expected_digest_is_rejected():
    try:
        decide_sara_activation(judgment(), expected_input_revision_digest="")
    except ValueError as exc:
        assert str(exc) == "EXPECTED_JUDGMENT_INPUT_DIGEST_REQUIRED"
    else:
        raise AssertionError("missing digest must be rejected")


def test_external_check_triggers_even_without_inference():
    value = judgment("NO_INFERENCE_DETECTED", "HIGH")
    value["external_check_need"] = "REQUIRED"
    result = decide_sara_activation(value, expected_input_revision_digest=DIGEST)
    assert result["activation_action"] == "SARA_SELECTIVE_VERIFICATION"
    assert result["reason_code"] == "EXTERNAL_CHECK_REQUIRED"


def test_ambiguous_verification_need_routes_to_precheck():
    value = judgment("NO_INFERENCE_DETECTED", "HIGH")
    value["verification_need"] = "AMBIGUOUS"
    result = decide_sara_activation(value, expected_input_revision_digest=DIGEST)
    assert result["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["reason_code"] == "VERIFICATION_NEED_AMBIGUOUS"


@pytest.mark.parametrize("confidence", ["LOW", "MEDIUM"])
def test_detected_inference_with_low_or_medium_confidence_routes_to_precheck(confidence):
    result = decide_sara_activation(
        judgment("INFERENCE_PRESENT", confidence),
        expected_input_revision_digest=DIGEST,
    )
    assert result["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["review_required"] is True
