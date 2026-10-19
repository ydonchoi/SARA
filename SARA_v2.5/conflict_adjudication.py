"""SARA v2.5 prototype: evidence conflict classification without truth promotion."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

POSITIONS = {"SUPPORTS", "CHALLENGES", "NEUTRAL"}
EVIDENCE_STATUSES = {
    "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"
}


@dataclass(frozen=True)
class EvidencePosition:
    evidence_id: str
    relation: str
    evidence_status: str
    scope_key: str = "UNSPECIFIED"
    time_key: str = "UNSPECIFIED"
    source_independence_key: str = "UNSPECIFIED"


def adjudicate_evidence_conflict(
    *,
    claim_id: str,
    evidence_positions: Iterable[EvidencePosition],
) -> dict:
    """Report unresolved polarity conflict; never infer that the claim is false."""
    if not claim_id or not claim_id.strip():
        raise ValueError("CLAIM_ID_REQUIRED")
    items = tuple(evidence_positions)
    seen = set()
    for item in items:
        if not item.evidence_id or not item.evidence_id.strip():
            raise ValueError("EVIDENCE_ID_REQUIRED")
        if item.evidence_id in seen:
            raise ValueError("DUPLICATE_EVIDENCE_ID")
        seen.add(item.evidence_id)
        if item.relation not in POSITIONS:
            raise ValueError("INVALID_EVIDENCE_RELATION")
        if item.evidence_status not in EVIDENCE_STATUSES:
            raise ValueError("INVALID_EVIDENCE_STATUS")

    eligible = [
        item for item in items
        if item.evidence_status == "VERIFIED" and item.relation in {"SUPPORTS", "CHALLENGES"}
    ]
    supports = [item for item in eligible if item.relation == "SUPPORTS"]
    challenges = [item for item in eligible if item.relation == "CHALLENGES"]

    if not eligible:
        status = "UNASSESSED"
        reason = "NO_VERIFIED_POLARITY_EVIDENCE"
    elif not supports or not challenges:
        status = "NO_CROSS_POLARITY_CONFLICT_OBSERVED"
        reason = "ONLY_ONE_VERIFIED_POLARITY_OBSERVED"
    else:
        same_context = any(
            (support.scope_key, support.time_key) == (challenge.scope_key, challenge.time_key)
            for support in supports for challenge in challenges
        )
        status = "UNRESOLVED_CONFLICT" if same_context else "CONTEXTUAL_DIVERGENCE_REVIEW"
        reason = "MIXED_VERIFIED_SUPPORT_AND_CHALLENGE_REQUIRES_ADJUDICATION"

    return {
        "claim_id": claim_id,
        "conflict_status": status,
        "reason": reason,
        "supporting_evidence_ids": [item.evidence_id for item in supports],
        "challenging_evidence_ids": [item.evidence_id for item in challenges],
        "claim_verification_status": "UNASSESSED",
        "truthfulness_status": "UNASSESSED",
        "source_independence_keys": sorted({
            item.source_independence_key for item in eligible
        }),
        "automatic_majority_resolution": False,
        "is_evidence": False,
        "source": "SARA_EVIDENCE_CONFLICT_ADJUDICATION",
    }
