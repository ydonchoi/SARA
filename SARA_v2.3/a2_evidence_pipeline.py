"""Bounded A2 evidence-pipeline integration for P31.

This module wires the already-verified P8-P13 capabilities into one
claim-level path. It is an integration boundary, not a truth oracle.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from claim_evidence_binding import ClaimEvidenceBindingEvaluator
from citation_fit import CitationFitEvaluator
from evidence_strength import EvidenceStrengthEvaluator
from verification_promotion import VerificationPromotionGate


@dataclass(frozen=True)
class A2EvidencePipelineResult:
    verification_status: str
    truthfulness_status: str
    citation_fit: str
    evidence_strength: str
    claim_bound: bool
    findings: tuple[str, ...]


class A2EvidencePipeline:
    """Execute the bounded P8 -> P9 -> P10 -> P12 -> P13 path."""

    def __init__(
        self,
        *,
        citation_fit: CitationFitEvaluator | None = None,
        evidence_strength: EvidenceStrengthEvaluator | None = None,
        binding: ClaimEvidenceBindingEvaluator | None = None,
        promotion: VerificationPromotionGate | None = None,
    ) -> None:
        self._citation_fit = citation_fit or CitationFitEvaluator()
        self._evidence_strength = evidence_strength or EvidenceStrengthEvaluator()
        self._binding = binding or ClaimEvidenceBindingEvaluator()
        self._promotion = promotion or VerificationPromotionGate()

    def evaluate(
        self,
        *,
        claim_id: str,
        claim_text: str,
        evidence_id: str,
        supports_claim_ids: tuple[str, ...],
        source_exists: bool,
        bibliographic_accuracy: str,
        content_access: Mapping[str, Any],
        content_scope: str = "UNKNOWN",
    ) -> A2EvidencePipelineResult:
        if not claim_id:
            raise ValueError("CLAIM_ID_REQUIRED")
        if not evidence_id:
            raise ValueError("EVIDENCE_ID_REQUIRED")
        if not isinstance(content_access, Mapping):
            raise ValueError("CONTENT_ACCESS_RESULT_INVALID")

        content_status = content_access.get("status")
        content = content_access.get("content", "")
        citation = self._citation_fit.evaluate(claim_id, claim_text, content)

        strength = self._evidence_strength.evaluate(
            citation_fit=citation.status,
            source_exists=source_exists,
            bibliographic_accuracy=bibliographic_accuracy,
            content_access=content_status or "UNASSESSED",
        )

        binding = self._binding.evaluate(
            claim_id=claim_id,
            evidence_id=evidence_id,
            supports_claim_ids=supports_claim_ids,
        )

        promotion = self._promotion.evaluate(
            claim_bound=binding.bound,
            citation_fit=citation.status,
            evidence_strength=strength.strength,
        )
        if content_scope == "BIBLIOGRAPHIC_METADATA":
            promotion_status = "UNVERIFIED"
            scope_findings = ("P31_BIBLIOGRAPHIC_METADATA_NOT_SUBSTANTIVE_EVIDENCE",)
        elif content_scope == "SUBSTANTIVE_CONTENT":
            if content_status != "RETRIEVED" or not content:
                promotion_status = "UNVERIFIED"
                scope_findings = ("P37_SUBSTANTIVE_CONTENT_REQUIRES_RETRIEVED_PAYLOAD",)
            else:
                promotion_status = promotion.verification_status
                scope_findings = ()
        else:
            promotion_status = "UNVERIFIED"
            scope_findings = ("P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE",)

        findings = (
            "P31_P8_CONTENT_PAYLOAD_CONSUMED",
            "P31_P9_CITATION_FIT_EXECUTED",
            "P31_P10_EVIDENCE_STRENGTH_EXECUTED",
            "P31_P12_CLAIM_BINDING_EXECUTED",
            "P31_P13_PROMOTION_EXECUTED",
        ) + scope_findings
        return A2EvidencePipelineResult(
            verification_status=promotion_status,
            truthfulness_status="UNASSESSED",
            citation_fit=citation.status,
            evidence_strength=strength.strength,
            claim_bound=binding.bound,
            findings=findings,
        )
