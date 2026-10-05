"""Bounded contradiction firewall for P14.

Contradictory evidence blocks automatic verification promotion.
It does not itself establish the truth of either side.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContradictionDecision:
    verification_status: str
    contradiction_detected: bool
    truthfulness_status: str


class ContradictionFirewall:
    def evaluate(
        self,
        *,
        claim_bound: bool,
        citation_fit: str,
        evidence_strength: str,
        contradiction_detected: bool,
    ) -> ContradictionDecision:
        if contradiction_detected:
            return ContradictionDecision(
                verification_status="CONTRADICTED",
                contradiction_detected=True,
                truthfulness_status="UNASSESSED",
            )
        promotable = (
            claim_bound
            and citation_fit == "VERIFIED"
            and evidence_strength in {"STRONG", "MODERATE"}
        )
        return ContradictionDecision(
            verification_status="VERIFIED" if promotable else "UNVERIFIED",
            contradiction_detected=False,
            truthfulness_status="UNASSESSED",
        )
