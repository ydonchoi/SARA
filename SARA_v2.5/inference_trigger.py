"""SARA activation policy for the internal JEV-style judgment result.

This policy decides whether a dialogue turn needs verification and selects the
does not verify a claim, mark an inference correct, or replace other verification
routes for factual claims that contain no inference.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

TRIGGER_POLICY_REVISION = "sara-verification-need-policy-v0.2"
JUDGMENT_STATUSES = {
    "INFERENCE_PRESENT",
    "NO_INFERENCE_DETECTED",
    "AMBIGUOUS",
}
CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}
VERIFICATION_NEEDS = {"REQUIRED", "NOT_REQUIRED", "AMBIGUOUS"}
EXTERNAL_CHECK_NEEDS = {"REQUIRED", "NOT_REQUIRED", "AMBIGUOUS"}


def decide_sara_activation(
    judgment: Mapping[str, Any],
    *,
    expected_input_revision_digest: str,
    policy_revision: str = TRIGGER_POLICY_REVISION,
) -> dict[str, Any]:
    """Make a fail-closed, revision-bound SARA activation decision."""
    if not isinstance(judgment, Mapping):
        raise ValueError("JUDGMENT_RESULT_MUST_BE_MAPPING")
    if not isinstance(expected_input_revision_digest, str) or not expected_input_revision_digest.strip():
        raise ValueError("EXPECTED_JUDGMENT_INPUT_DIGEST_REQUIRED")
    if not isinstance(policy_revision, str) or not policy_revision.strip():
        raise ValueError("TRIGGER_POLICY_REVISION_REQUIRED")

    digest_matches = judgment.get("input_revision_digest") == expected_input_revision_digest
    status = judgment.get("judgment_status")
    execution = judgment.get("execution_status")
    confidence = judgment.get("confidence")
    verification_need = judgment.get("verification_need")
    external_check_need = judgment.get("external_check_need")
    if not digest_matches:
        action = "SARA_PRECHECK_REVIEW"
        reason = "JUDGMENT_INPUT_REVISION_MISMATCH"
    elif (
        execution != "SUCCEEDED"
        or not isinstance(status, str)
        or status not in JUDGMENT_STATUSES
    ):
        action = "SARA_PRECHECK_REVIEW"
        reason = "JUDGMENT_UNAVAILABLE_OR_INVALID"
    elif (
        not isinstance(verification_need, str)
        or verification_need not in VERIFICATION_NEEDS
        or not isinstance(external_check_need, str)
        or external_check_need not in EXTERNAL_CHECK_NEEDS
    ):
        action = "SARA_PRECHECK_REVIEW"
        reason = "VERIFICATION_NEED_MISSING_OR_INVALID"
    elif status == "AMBIGUOUS" or not isinstance(confidence, str) or confidence not in CONFIDENCE_LEVELS:
        action = "SARA_PRECHECK_REVIEW"
        reason = "INFERENCE_JUDGMENT_AMBIGUOUS"
    elif confidence != "HIGH":
        action = "SARA_PRECHECK_REVIEW"
        reason = "JUDGMENT_CONFIDENCE_NOT_HIGH"
    elif verification_need == "AMBIGUOUS" or external_check_need == "AMBIGUOUS":
        action = "SARA_PRECHECK_REVIEW"
        reason = "VERIFICATION_NEED_AMBIGUOUS"
    elif verification_need == "REQUIRED" or external_check_need == "REQUIRED":
        action = "SARA_SELECTIVE_VERIFICATION"
        reason = (
            "EXTERNAL_CHECK_REQUIRED"
            if external_check_need == "REQUIRED"
            else "VERIFICATION_REQUIRED"
        )
    else:
        action = "NO_INFERENCE_TRIGGER"
        reason = "VERIFICATION_NOT_REQUIRED"

    triggered = action != "NO_INFERENCE_TRIGGER"
    return {
        "decision_id": f"{policy_revision}:{expected_input_revision_digest[:16]}",
        "policy_revision": policy_revision,
        "input_revision_digest": expected_input_revision_digest,
        "judgment_status": status,
        "verification_need": verification_need,
        "external_check_need": external_check_need,
        "activation_action": action,
        "activation_triggered": triggered,
        "review_required": action == "SARA_PRECHECK_REVIEW",
        "reason_code": reason,
        "scope": "DIALOGUE_VERIFICATION_ROUTING",
        "other_verification_routes_untouched": True,
        "claim_truth_assessed": False,
        "is_evidence": False,
        "status": "DECIDED",
    }
