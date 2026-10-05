"""Bounded evidence-strength classification for P10.

Strength is review metadata. It is not a truthfulness assertion.
"""
from __future__ import annotations

from dataclasses import dataclass


_ALLOWED = {"STRONG", "MODERATE", "WEAK", "UNASSESSED"}


@dataclass(frozen=True)
class EvidenceStrengthResult:
    strength: str
    rationale: str


class EvidenceStrengthEvaluator:
    def evaluate(
        self,
        *,
        citation_fit: str,
        source_exists: bool,
        bibliographic_accuracy: str,
        content_access: str,
    ) -> EvidenceStrengthResult:
        if citation_fit == "VERIFIED" and source_exists and bibliographic_accuracy == "VERIFIED" and content_access == "RETRIEVED":
            return EvidenceStrengthResult("STRONG", "source identity, access, and citation fit all verified")
        if citation_fit == "VERIFIED" and source_exists:
            return EvidenceStrengthResult("MODERATE", "citation fit and source existence verified")
        if source_exists:
            return EvidenceStrengthResult("WEAK", "source existence verified without sufficient alignment")
        return EvidenceStrengthResult("UNASSESSED", "insufficient source verification")

    @staticmethod
    def allowed_strengths() -> tuple[str, ...]:
        return tuple(sorted(_ALLOWED))
