"""Allowlisted public-status projection for SARA v2.5 runtime results.

This module is a response-shaping boundary, not authentication, authorization,
or a substitute for a secure host adapter. It intentionally drops internal
payloads and maps unknown state to a generic safe response.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

PUBLIC_SCHEMA_VERSION = "sara.public-status.v0.1"

_PUBLIC_REASON_CODES = {
    "INFERENCE_HAS_NO_BOUND_CLAIM_CANDIDATE": "CLAIM_BINDING_REQUIRED",
    "INFERENCE_EVIDENCE_INPUT_INVALID": "INPUT_REVIEW_REQUIRED",
    "PRECHECK_REQUIRED": "REVIEW_REQUIRED",
    "AMBIGUOUS_JUDGMENT": "AMBIGUOUS_INPUT",
    "MODEL_GENERATION_FAILED": "ASSESSMENT_UNAVAILABLE",
    "SARA_VERIFY_CLAIM_STATUS_NOT_SUCCEEDED": "VERIFICATION_FAILED",
}


def project_public_status(runtime_result: Any) -> dict[str, Any]:
    """Return a minimal, non-sensitive public status object.

    No free-form model text, claim text, spans, provider payload, identifiers,
    stack traces, or unknown keys are copied from the runtime result.
    """
    safe = {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "status": "NOT_ASSESSED",
        "verification_started": False,
        "reason_code": "STATUS_UNAVAILABLE",
        "claim_truth_established": False,
    }
    if not isinstance(runtime_result, Mapping):
        safe.update(status="FAILED", reason_code="INVALID_RUNTIME_RESULT")
        return safe

    judgment = runtime_result.get("judgment")
    decision = runtime_result.get("activation_decision")
    route = runtime_result.get("route_execution")
    if not isinstance(judgment, Mapping) or not isinstance(decision, Mapping):
        safe.update(status="FAILED", reason_code="INVALID_RUNTIME_STATE")
        return safe
    if not isinstance(route, Mapping):
        route = {}

    judgment_status = judgment.get("judgment_status")
    activation_action = decision.get("activation_action")
    pipeline_status = runtime_result.get("pipeline_status")
    execution_status = route.get("execution_status")
    route_output = route.get("output")
    if not isinstance(route_output, Mapping):
        route_output = {}
    route_status = route_output.get("status")

    raw_reason = decision.get("reason_code")
    public_reason = (
        _PUBLIC_REASON_CODES.get(raw_reason, "STATUS_UNAVAILABLE")
        if isinstance(raw_reason, str) else "STATUS_UNAVAILABLE"
    )

    if judgment_status == "NOT_ASSESSED":
        safe.update(status="NOT_ASSESSED", reason_code="ASSESSMENT_UNAVAILABLE")
        return safe

    verification_results = route_output.get("verification_results")
    results_are_invalid_or_failed = (
        isinstance(verification_results, list)
        and any(
            not isinstance(item, Mapping)
            or item.get("execution_status") != "SUCCEEDED"
            for item in verification_results
        )
    )
    if (
        execution_status == "FAILED"
        or route_status == "FAILED"
        or route_status == "PARTIALLY_FAILED"
        or pipeline_status == "ROUTE_FAILED"
        or results_are_invalid_or_failed
    ):
        safe.update(status="FAILED", reason_code="VERIFICATION_FAILED")
        return safe

    if activation_action == "SARA_PRECHECK_REVIEW" or route_status in {
        "NEEDS_REVIEW", "REVIEW_QUEUED"
    }:
        safe.update(status="REVIEW_REQUIRED", reason_code=public_reason)
        return safe

    if pipeline_status == "NO_ROUTE_REQUIRED" or activation_action == "NO_TRIGGER":
        safe.update(status="NOT_ASSESSED", reason_code="NO_VERIFICATION_TRIGGER")
        return safe

    if activation_action == "SARA_SELECTIVE_VERIFICATION":
        provider_invoked = runtime_result.get("verification_provider_invoked")
        if provider_invoked is True:
            safe.update(
                status="VERIFICATION_COMPLETED",
                verification_started=True,
                reason_code="VERIFICATION_ATTEMPT_COMPLETED",
            )
        else:
            safe.update(status="REVIEW_REQUIRED", reason_code="VERIFICATION_NOT_CONFIRMED")
        return safe

    safe.update(status="REVIEW_REQUIRED", reason_code="STATUS_UNAVAILABLE")
    return safe
