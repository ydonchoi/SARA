"""Claim-level evidence conflict aggregation for P15.

Conflicting evidence forces an unresolved claim state; aggregation is not
itself a truthfulness judgment.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimEvidenceConflictState:
    claim_id: str
    verification_status: str
    conflict_detected: bool
    truthfulness_status: str


class ClaimEvidenceConflictEvaluator:
    def evaluate(
        self,
        *,
        claim_id: str,
        evidence_verification_statuses: tuple[str, ...],
    ) -> ClaimEvidenceConflictState:
        if not claim_id:
            raise ValueError("CLAIM_ID_REQUIRED")
        conflict = "VERIFIED" in evidence_verification_statuses and "CONTRADICTED" in evidence_verification_statuses
        if conflict:
            status = "CONTRADICTED"
        elif "CONTRADICTED" in evidence_verification_statuses:
            status = "CONTRADICTED"
        elif "VERIFIED" in evidence_verification_statuses:
            status = "VERIFIED"
        else:
            status = "UNVERIFIED"
        return ClaimEvidenceConflictState(
            claim_id=claim_id,
            verification_status=status,
            conflict_detected=conflict,
            truthfulness_status="UNASSESSED",
        )
