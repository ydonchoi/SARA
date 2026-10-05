"""Bounded verification promotion firewall for P13.

Verification requires aligned evidence; truthfulness remains a separate state.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerificationPromotion:
    verification_status: str
    truthfulness_status: str
    promoted: bool


class VerificationPromotionGate:
    def evaluate(
        self,
        *,
        claim_bound: bool,
        citation_fit: str,
        evidence_strength: str,
    ) -> VerificationPromotion:
        promoted = (
            claim_bound
            and citation_fit == "VERIFIED"
            and evidence_strength in {"STRONG", "MODERATE"}
        )
        return VerificationPromotion(
            verification_status="VERIFIED" if promoted else "UNVERIFIED",
            truthfulness_status="UNASSESSED",
            promoted=promoted,
        )
