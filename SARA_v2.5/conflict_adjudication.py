"""SARA v2.5 prototype: evidence conflict classification without truth promotion."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

POSITIONS = {"SUPPORTS", "CHALLENGES", "NEUTRAL"}
EVIDENCE_STATUSES = {
    "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"
}
POLARITY_STATUSES = {"VERIFIED", "PARTIALLY_VERIFIED"}


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
    """Classify opposing evidence signals without deciding the claim's truth.

    VERIFIED opposing evidence in matching scope/time yields UNRESOLVED_CONFLICT.
    If one side is only PARTIALLY_VERIFIED, yield POTENTIAL_CONFLICT_REVIEW.
    Opposing evidence from different scope/time yields CONTEXTUAL_DIVERGENCE_REVIEW.
    No majority vote or claim truth promotion is performed.
    """
    if not claim_id or not claim_id.strip():
        raise ValueError("CLAIM_ID_REQUIRED")
    items = tuple(evidence_positions)
    seen = set()
    for item in items:
        if not isinstance(item.evidence_id, str) or not item.evidence_id.strip():
            raise ValueError("EVIDENCE_ID_REQUIRED")
        if item.evidence_id in seen:
            raise ValueError("DUPLICATE_EVIDENCE_ID")
        seen.add(item.evidence_id)
        if item.relation not in POSITIONS:
            raise ValueError("INVALID_EVIDENCE_RELATION")
        if item.evidence_status not in EVIDENCE_STATUSES:
            raise ValueError("INVALID_EVIDENCE_STATUS")
        for value, error in (
            (item.scope_key, "INVALID_SCOPE_KEY"),
            (item.time_key, "INVALID_TIME_KEY"),
            (item.source_independence_key, "INVALID_SOURCE_INDEPENDENCE_KEY"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(error)

    eligible = [
        item for item in items
        if item.evidence_status in POLARITY_STATUSES
        and item.relation in {"SUPPORTS", "CHALLENGES"}
    ]
    verified_supports = [
        item for item in eligible
        if item.relation == "SUPPORTS" and item.evidence_status == "VERIFIED"
    ]
    verified_challenges = [
        item for item in eligible
        if item.relation == "CHALLENGES" and item.evidence_status == "VERIFIED"
    ]
    partial_supports = [
        item for item in eligible
        if item.relation == "SUPPORTS" and item.evidence_status == "PARTIALLY_VERIFIED"
    ]
    partial_challenges = [
        item for item in eligible
        if item.relation == "CHALLENGES" and item.evidence_status == "PARTIALLY_VERIFIED"
    ]
    support_side = verified_supports + partial_supports
    challenge_side = verified_challenges + partial_challenges

    if not eligible:
        status = "UNASSESSED"
        reason = "NO_VERIFIED_OR_PARTIALLY_VERIFIED_POLARITY_EVIDENCE"
    elif support_side and challenge_side:
        verified_same_context = any(
            (support.scope_key, support.time_key) == (challenge.scope_key, challenge.time_key)
            for support in verified_supports for challenge in verified_challenges
        )
        any_verified_opposition = bool(verified_supports and verified_challenges)
        partial_same_context = any(
            (support.scope_key, support.time_key) == (challenge.scope_key, challenge.time_key)
            for support in support_side for challenge in challenge_side
            if support.evidence_status == "PARTIALLY_VERIFIED"
            or challenge.evidence_status == "PARTIALLY_VERIFIED"
        )
        if verified_same_context:
            status = "UNRESOLVED_CONFLICT"
            reason = "MIXED_VERIFIED_SUPPORT_AND_CHALLENGE_IN_MATCHING_SCOPE_TIME"
        elif any_verified_opposition:
            status = "CONTEXTUAL_DIVERGENCE_REVIEW"
            reason = "VERIFIED_OPPOSING_EVIDENCE_HAS_NO_MATCHING_SCOPE_TIME_PAIR"
        elif partial_same_context:
            status = "POTENTIAL_CONFLICT_REVIEW"
            reason = "PARTIALLY_VERIFIED_OPPOSING_EVIDENCE_REQUIRES_REVIEW"
        else:
            status = "CONTEXTUAL_DIVERGENCE_REVIEW"
            reason = "OPPOSING_EVIDENCE_SPANS_DIFFERENT_SCOPE_OR_TIME"
    else:
        status = "NO_CROSS_POLARITY_CONFLICT_OBSERVED"
        reason = "ONLY_ONE_ELIGIBLE_EVIDENCE_POLARITY_OBSERVED"

    non_eligible = [
        item.evidence_id for item in items
        if item not in eligible
    ]
    return {
        "claim_id": claim_id,
        "conflict_status": status,
        "reason": reason,
        "supporting_evidence_ids": [item.evidence_id for item in verified_supports],
        "challenging_evidence_ids": [item.evidence_id for item in verified_challenges],
        "partially_verified_supporting_evidence_ids": [
            item.evidence_id for item in partial_supports
        ],
        "partially_verified_challenging_evidence_ids": [
            item.evidence_id for item in partial_challenges
        ],
        "non_eligible_evidence_ids": non_eligible,
        "claim_verification_status": "UNASSESSED",
        "truthfulness_status": "UNASSESSED",
        "source_independence_keys": sorted({
            item.source_independence_key for item in eligible
        }),
        "source_independence_status": "NOT_ADJUDICATED",
        "automatic_majority_resolution": False,
        "is_evidence": False,
        "source": "SARA_EVIDENCE_CONFLICT_ADJUDICATION",
    }
