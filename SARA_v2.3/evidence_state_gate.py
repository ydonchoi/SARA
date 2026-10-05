"""Bounded gate connecting evidence metadata to verification state.

Evidence strength may support review, but cannot by itself establish truthfulness.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvidenceStateDecision:
    verification_status: str
    truthfulness_status: str
    reason: str


class EvidenceStateGate:
    def decide(
        self,
        *,
        evidence_strength: str,
        citation_fit: str,
        source_exists: bool,
    ) -> EvidenceStateDecision:
        if evidence_strength == "STRONG" and citation_fit == "VERIFIED" and source_exists:
            return EvidenceStateDecision(
                verification_status="VERIFIED",
                truthfulness_status="UNASSESSED",
                reason="evidence alignment supports verification but not truthfulness establishment",
            )
        return EvidenceStateDecision(
            verification_status="UNVERIFIED",
            truthfulness_status="UNASSESSED",
            reason="insufficient aligned evidence",
        )
