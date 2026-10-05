"""Transport-neutral callable execution boundary for SARA v2.3."""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

EXECUTION_STATUSES = {"SUCCEEDED", "FAILED", "REJECTED"}
VERIFICATION_STATUSES = {"VERIFIED", "PARTIALLY VERIFIED", "INFERRED", "HYPOTHESIZED", "UNVERIFIED", "CONTRADICTED"}
INFERENCE_LEVELS = {"FACT", "INFERENCE", "HYPOTHESIS", "SPECULATION"}
CITATION_STATUSES = {"VERIFIED", "PARTIALLY VERIFIED", "UNVERIFIED", "CONTRADICTED", "NOT_COMPLETED"}

class SARAExecutionError(ValueError):
    pass

def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SARAExecutionError(f"{name}_INVALID")
    return value

def _validate_request(request: Mapping[str, Any]) -> None:
    if request.get("capability") != "verify_claim":
        raise SARAExecutionError("SARA_EXECUTION_CAPABILITY_INVALID")
    claim = _mapping(request.get("claim"), "SARA_CLAIM")
    for field in ("id", "text", "type", "source"):
        if not claim.get(field):
            raise SARAExecutionError(f"SARA_REQUEST_FIELD_REQUIRED:{field}")
    level = claim.get("inference_level")
    if level is not None:
        if level not in INFERENCE_LEVELS:
            raise SARAExecutionError("SARA_INFERENCE_LEVEL_INVALID")
        if level != "FACT" and not claim.get("inference_basis"):
            raise SARAExecutionError("SARA_INFERENCE_BASIS_REQUIRED")
    evidence = request.get("evidence", [])
    if not isinstance(evidence, list):
        raise SARAExecutionError("SARA_EVIDENCE_INVALID")
    evidence_by_id = {}
    for item in evidence:
        item = _mapping(item, "SARA_EVIDENCE")
        evidence_id = item.get("id")
        if not evidence_id or evidence_id in evidence_by_id:
            raise SARAExecutionError("SARA_EVIDENCE_ID_INVALID")
        evidence_by_id[evidence_id] = item
        supports = item.get("supports_claims")
        if supports is not None:
            if not isinstance(supports, list) or claim["id"] not in supports:
                raise SARAExecutionError("SARA_EVIDENCE_CLAIM_BINDING_INVALID")
    evidence_ids = claim.get("evidence_ids")
    if evidence_ids is not None:
        if not isinstance(evidence_ids, list):
            raise SARAExecutionError("SARA_CLAIM_EVIDENCE_IDS_INVALID")
        if any(eid not in evidence_by_id for eid in evidence_ids):
            raise SARAExecutionError("SARA_CLAIM_EVIDENCE_REFERENCE_DANGLING")
    if not request.get("request_id"):
        raise SARAExecutionError("SARA_REQUEST_ID_REQUIRED")

def _validate_response(request: Mapping[str, Any], response: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(_mapping(response, "SARA_RESPONSE"))
    if result.get("claim_id") != request["claim"]["id"]:
        raise SARAExecutionError("SARA_RESPONSE_CLAIM_ID_MISMATCH")
    status = result.get("status")
    if status not in EXECUTION_STATUSES:
        raise SARAExecutionError("SARA_EXECUTION_STATUS_INVALID")
    result.setdefault("provider_id", "SARA")
    if status != "SUCCEEDED":
        result.pop("verification", None)
        return result
    verification = _mapping(result.get("verification"), "SARA_VERIFICATION")
    if verification.get("verification_status") not in VERIFICATION_STATUSES:
        raise SARAExecutionError("SARA_VERIFICATION_STATUS_INVALID")
    if verification.get("verification_layer") != "research_verification":
        raise SARAExecutionError("SARA_VERIFICATION_LAYER_INVALID")
    citation = result.get("external_citation_verification")
    if verification.get("truthfulness_status", "UNASSESSED") == "ESTABLISHED":
        citation = _mapping(citation, "SARA_CITATION")
        if citation.get("status") != "VERIFIED":
            raise SARAExecutionError("SARA_TRUTHFULNESS_ESTABLISHED_WITHOUT_CITATION")
    if citation is not None:
        citation = _mapping(citation, "SARA_CITATION")
        if citation.get("status") not in CITATION_STATUSES:
            raise SARAExecutionError("SARA_CITATION_STATUS_INVALID")
    if not result.get("external_result_provenance_ids"):
        raise SARAExecutionError("SARA_RESULT_PROVENANCE_REQUIRED")
    return result

class CallableSARA:
    """Callable execution boundary; verifier is an injected implementation."""

    def __init__(self, verifier: Callable[[Mapping[str, Any]], Mapping[str, Any]]):
        self._verifier = verifier

    def verify_claim(self, request: Mapping[str, Any]) -> dict[str, Any]:
        """Explicit method alias for integrations that prefer named capability calls."""
        return self(request)

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        _validate_request(request)
        try:
            raw = self._verifier(deepcopy(dict(request)))
        except SARAExecutionError:
            raise
        except Exception as exc:
            return {
                "request_id": request["request_id"],
                "claim_id": request["claim"]["id"],
                "provider_id": "SARA",
                "status": "FAILED",
                "failure": {"code": "SARA_PROVIDER_EXECUTION_ERROR", "message": str(exc)},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        return _validate_response(request, raw)
