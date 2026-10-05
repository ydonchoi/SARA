"""Bounded citation-fit evaluation for P9.

Citation fit checks whether the supplied claim text is present in retrieved
content. It does not establish claim truth.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CitationFitResult:
    status: str
    claim_id: str
    matched: bool
    findings: tuple[str, ...]


class CitationFitEvaluator:
    def evaluate(self, claim_id: str, claim_text: str, content: str) -> CitationFitResult:
        if not claim_id:
            raise ValueError("CLAIM_ID_REQUIRED")
        if not claim_text:
            raise ValueError("CLAIM_TEXT_REQUIRED")
        if not content:
            return CitationFitResult(
                status="UNVERIFIED",
                claim_id=claim_id,
                matched=False,
                findings=("CONTENT_EMPTY",),
            )

        normalized_claim = " ".join(claim_text.lower().split())
        normalized_content = " ".join(content.lower().split())
        matched = normalized_claim in normalized_content

        return CitationFitResult(
            status="VERIFIED" if matched else "UNVERIFIED",
            claim_id=claim_id,
            matched=matched,
            findings=(
                "CITATION_FIT_COMPLETED"
                if matched
                else "CLAIM_TEXT_NOT_FOUND_IN_CONTENT",
            ),
        )
