"""Non-epistemic observation records for evidence-flow diagnostics.

This module records operational flow outcomes only. Observation data is not
verification evidence and must never promote verification or truthfulness.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Mapping


@dataclass(frozen=True)
class EvidenceFlowObservation:
    request_id: str
    claim_id: str
    provider_status: str
    content_access_status: str
    content_scope: str
    evidence_identity_status: str
    verification_status: str
    finding_codes: tuple[str, ...]
    recoverability: str
    latency_ms: int | None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("OBSERVATION_REQUEST_ID_REQUIRED")
        if not self.claim_id:
            raise ValueError("OBSERVATION_CLAIM_ID_REQUIRED")
        if self.recoverability not in {"UNKNOWN", "RECOVERABLE", "IRRECOVERABLE"}:
            raise ValueError("OBSERVATION_RECOVERABILITY_INVALID")
        if self.verification_status not in {"VERIFIED", "UNVERIFIED"}:
            raise ValueError("OBSERVATION_VERIFICATION_STATUS_INVALID")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_recoverability(*, findings: tuple[str, ...]) -> str:
    """Classify operational recovery potential; never changes verification."""
    recoverable_codes = {
        "P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",
        "P39_CONTENT_SCOPE_REQUIRES_A2_PIPELINE",
        "P37_SUBSTANTIVE_CONTENT_REQUIRES_RETRIEVED_PAYLOAD",
        "P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE",
    }
    if any(code in recoverable_codes for code in findings):
        return "RECOVERABLE"
    if findings:
        return "UNKNOWN"
    return "UNKNOWN"


def build_observation(
    *,
    request_id: str,
    claim_id: str,
    provider_status: str,
    content_access_status: str,
    content_scope: str,
    evidence_identity_status: str,
    verification_status: str,
    finding_codes: tuple[str, ...],
    latency_ms: int | None = None,
) -> EvidenceFlowObservation:
    return EvidenceFlowObservation(
        request_id=request_id,
        claim_id=claim_id,
        provider_status=provider_status,
        content_access_status=content_access_status,
        content_scope=content_scope,
        evidence_identity_status=evidence_identity_status,
        verification_status=verification_status,
        finding_codes=finding_codes,
        recoverability=classify_recoverability(findings=finding_codes),
        latency_ms=latency_ms,
    )
