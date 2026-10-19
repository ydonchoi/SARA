"""SARA activation policy for the internal JEV-style judgment result.

This policy decides whether an inference-triggered SARA review should run. It
does not verify a claim, mark an inference correct, or replace other verification
routes for factual claims that contain no inference.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

TRIGGER_POLICY_REVISION = "sara-inference-trigger-policy-v0.1"
JUDGMENT_STATUSES = {
    "INFERENCE_PRESENT",
    "NO_INFERENCE_DETECTED",
    "AMBIGUOUS",
}
CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}


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
    if not digest_matches:
        action = "SARA_PRECHECK_REVIEW"
        reason = "JUDGMENT_INPUT_REVISION_MISMATCH"
    elif execution != "SUCCEEDED" or status not in JUDGMENT_STATUSES:
        action = "SARA_PRECHECK_REVIEW"
        reason = "JUDGMENT_UNAVAILABLE_OR_INVALID"
    elif status == "INFERENCE_PRESENT":
        action = "SARA_SELECTIVE_VERIFICATION"
        reason = "INFERENCE_DETECTED"
    elif status == "AMBIGUOUS" or confidence not in CONFIDENCE_LEVELS:
        action = "SARA_PRECHECK_REVIEW"
        reason = "INFERENCE_JUDGMENT_AMBIGUOUS"
    elif confidence != "HIGH":
        action = "SARA_PRECHECK_REVIEW"
        reason = "JUDGMENT_CONFIDENCE_NOT_HIGH"
    else:
        action = "NO_INFERENCE_TRIGGER"
        reason = "NO_INFERENCE_DETECTED_WITH_HIGH_CONFIDENCE"

    triggered = action != "NO_INFERENCE_TRIGGER"
    return {
        "decision_id": f"{policy_revision}:{expected_input_revision_digest[:16]}",
        "policy_revision": policy_revision,
        "input_revision_digest": expected_input_revision_digest,
        "judgment_status": status,
        "activation_action": action,
        "activation_triggered": triggered,
        "review_required": action == "SARA_PRECHECK_REVIEW",
        "reason_code": reason,
        "scope": "INFERENCE_TRIGGER_ONLY",
        "other_verification_routes_untouched": True,
        "claim_truth_assessed": False,
        "is_evidence": False,
        "status": "DECIDED",
    }
