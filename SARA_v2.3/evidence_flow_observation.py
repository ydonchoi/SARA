"""Non-epistemic observation records for evidence-flow diagnostics.

This module records operational flow outcomes only. Observation data is not
verification evidence and must never promote verification or truthfulness.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


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
    recovery_candidate: bool
    latency_ms: int | None

    def __post_init__(self) -> None:
        if not self.request_id:
            raise ValueError("OBSERVATION_REQUEST_ID_REQUIRED")
        if not self.claim_id:
            raise ValueError("OBSERVATION_CLAIM_ID_REQUIRED")
        if not isinstance(self.recovery_candidate, bool):
            raise ValueError("OBSERVATION_RECOVERY_CANDIDATE_INVALID")
        if self.verification_status not in {"VERIFIED", "UNVERIFIED"}:
            raise ValueError("OBSERVATION_VERIFICATION_STATUS_INVALID")
        if self.latency_ms is not None and self.latency_ms < 0:
            raise ValueError("OBSERVATION_LATENCY_INVALID")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_recovery_candidate(*, findings: tuple[str, ...]) -> bool:
    """Mark only operational candidates; never assert actual recoverability."""
    candidate_codes = {
        "P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",
        "P39_CONTENT_SCOPE_REQUIRES_A2_PIPELINE",
        "P37_SUBSTANTIVE_CONTENT_REQUIRES_RETRIEVED_PAYLOAD",
        "P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE",
    }
    return any(code in candidate_codes for code in findings)


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
        recovery_candidate=classify_recovery_candidate(findings=finding_codes),
        latency_ms=latency_ms,
    )
