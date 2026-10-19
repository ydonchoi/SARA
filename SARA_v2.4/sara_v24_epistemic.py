"""SARA v2.4 epistemic state and boundary validation.

This module validates state shape and preserves epistemic boundaries. It does
not fetch sources, establish truth, or perform semantic fallacy detection.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

TYPES = {"FACT", "INTERPRETATION", "INFERENCE", "HYPOTHESIS", "SIMULATION"}
VERIFICATION = {"VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"}
VERIFICATION_ALIASES = {"PARTIALLY VERIFIED": "PARTIALLY_VERIFIED"}
ATTRIBUTION = {
    "AUTHOR_EXPLICIT", "AUTHOR_SUPPORTED", "SOURCE_INFERRED",
    "FIELD_INTERPRETATION", "MODERN_INTERPRETATION", "SPECULATIVE", "UNKNOWN",
}
TEMPORAL = {"HISTORICAL", "POST_PUBLICATION", "CONTEMPORARY"}
ALIGNMENT = {
    "SUPPORTS_CLAIM", "SUPPORTS_PREMISE", "CHALLENGES_CLAIM",
    "CHALLENGES_PREMISE", "NEUTRAL", "UNASSESSED",
}


def normalize_verification_status(status: str) -> str:
    """Return the canonical schema spelling while accepting the legacy alias."""
    if not isinstance(status, str):
        raise ValueError("INVALID_VERIFICATION_STATUS")
    normalized = status.strip().upper()
    return VERIFICATION_ALIASES.get(normalized, normalized)


@dataclass(frozen=True)
class PremiseEvaluation:
    premise_id: str
    status: str = "UNVERIFIED"
    findings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ClaimEvaluationState:
    claim_id: str
    verification_status: str = "UNVERIFIED"
    attribution_status: str = "UNKNOWN"
    temporal_status: str = "CONTEMPORARY"
    premise_evaluations: tuple[PremiseEvaluation, ...] = ()
    provenance_ids: tuple[str, ...] = ()
    attribution_evidence_ids: tuple[str, ...] = ()


def validate_state(state: ClaimEvaluationState) -> ClaimEvaluationState:
    """Validate invariants and normalize legacy status spelling.

    AUTHOR_EXPLICIT depends on attributable source evidence, not on whether
    the claim is historical or contemporary. Temporal context and attribution
    are independent dimensions.
    """
    if not state.claim_id or not state.claim_id.strip():
        raise ValueError("CLAIM_ID_REQUIRED")
    if state.attribution_status not in ATTRIBUTION:
        raise ValueError("INVALID_ATTRIBUTION_STATUS")
    if state.temporal_status not in TEMPORAL:
        raise ValueError("INVALID_TEMPORAL_STATUS")

    claim_status = normalize_verification_status(state.verification_status)
    if claim_status not in VERIFICATION:
        raise ValueError("INVALID_VERIFICATION_STATUS")

    normalized_premises = []
    seen_premise_ids = set()
    for premise in state.premise_evaluations:
        if not premise.premise_id or not premise.premise_id.strip():
            raise ValueError("PREMISE_ID_REQUIRED")
        if premise.premise_id in seen_premise_ids:
            raise ValueError("DUPLICATE_PREMISE_ID")
        seen_premise_ids.add(premise.premise_id)
        premise_status = normalize_verification_status(premise.status)
        if premise_status not in VERIFICATION:
            raise ValueError("INVALID_PREMISE_VERIFICATION_STATUS")
        normalized_premises.append(replace(premise, status=premise_status))

    for values, error in (
        (state.provenance_ids, "EMPTY_PROVENANCE_ID"),
        (state.attribution_evidence_ids, "EMPTY_ATTRIBUTION_EVIDENCE_ID"),
    ):
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(error)

    if state.attribution_status == "AUTHOR_EXPLICIT" and not state.attribution_evidence_ids:
        raise ValueError("AUTHOR_EXPLICIT_REQUIRES_SOURCE_EVIDENCE")

    return replace(
        state,
        verification_status=claim_status,
        premise_evaluations=tuple(normalized_premises),
    )


def assessment_warnings(state: ClaimEvaluationState) -> tuple[str, ...]:
    """Return review signals without silently changing independent statuses."""
    validated = validate_state(state)
    warnings = []
    if (
        validated.verification_status == "VERIFIED"
        and any(p.status == "CONTRADICTED" for p in validated.premise_evaluations)
    ):
        warnings.append("CLAIM_VERIFIED_WITH_CONTRADICTED_PREMISE")
    return tuple(warnings)


def align_evidence(*, relation: str, target_id: str, evidence_id: str) -> dict:
    """Register a proposed alignment; the relation is not semantically assessed."""
    if relation not in ALIGNMENT:
        raise ValueError("INVALID_ALIGNMENT")
    if not target_id or not target_id.strip() or not evidence_id or not evidence_id.strip():
        raise ValueError("EVIDENCE_ALIGNMENT_IDS_REQUIRED")
    return {
        "evidence_id": evidence_id,
        "target_id": target_id,
        "relation": relation,
        "status": "UNASSESSED",
        "is_evidence": False,
    }
