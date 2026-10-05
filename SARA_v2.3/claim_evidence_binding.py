"""Bounded claim-evidence binding firewall for P12.

An evidence item is usable only when it explicitly supports the requested claim.
Binding does not establish truthfulness.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClaimEvidenceBinding:
    claim_id: str
    evidence_id: str
    bound: bool
    reason: str


class ClaimEvidenceBindingEvaluator:
    def evaluate(
        self,
        *,
        claim_id: str,
        evidence_id: str,
        supports_claim_ids: tuple[str, ...],
    ) -> ClaimEvidenceBinding:
        if not claim_id:
            raise ValueError("CLAIM_ID_REQUIRED")
        if not evidence_id:
            raise ValueError("EVIDENCE_ID_REQUIRED")
        bound = claim_id in supports_claim_ids
        return ClaimEvidenceBinding(
            claim_id=claim_id,
            evidence_id=evidence_id,
            bound=bound,
            reason="EXPLICIT_CLAIM_BINDING" if bound else "CLAIM_BINDING_MISSING",
        )
