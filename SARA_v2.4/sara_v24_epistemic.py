"""SARA v2.4 epistemic model.

Pure validation layer for Claim/Premise/Evidence/Context state.
It does not fetch sources and does not infer truth from model output.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Iterable

TYPES={"FACT","INTERPRETATION","INFERENCE","HYPOTHESIS","SIMULATION"}
VERIFICATION={"VERIFIED","PARTIALLY_VERIFIED","UNVERIFIED","CONTRADICTED"}
ATTRIBUTION={"AUTHOR_EXPLICIT","AUTHOR_SUPPORTED","SOURCE_INFERRED","FIELD_INTERPRETATION","MODERN_INTERPRETATION","SPECULATIVE","UNKNOWN"}
TEMPORAL={"HISTORICAL","POST_PUBLICATION","CONTEMPORARY"}
ALIGNMENT={"SUPPORTS_CLAIM","SUPPORTS_PREMISE","CHALLENGES_CLAIM","CHALLENGES_PREMISE","NEUTRAL","UNASSESSED"}

@dataclass(frozen=True)
class PremiseEvaluation:
    premise_id:str
    status:str="UNVERIFIED"
    findings:tuple[str,...]=()

@dataclass(frozen=True)
class ClaimEvaluationState:
    claim_id:str
    verification_status:str="UNVERIFIED"
    attribution_status:str="UNKNOWN"
    temporal_status:str="CONTEMPORARY"
    premise_evaluations:tuple[PremiseEvaluation,...]=()
    provenance_ids:tuple[str,...]=()
    attribution_evidence_ids:tuple[str,...]=()

def _normalize_verification(value: str) -> str:
    return "PARTIALLY_VERIFIED" if value == "PARTIALLY VERIFIED" else value

def validate_state(
    state: ClaimEvaluationState,
    *,
    available_evidence_ids: Iterable[str] | None = None,
) -> ClaimEvaluationState:
    if not isinstance(state, ClaimEvaluationState):
        raise ValueError("CLAIM_EVALUATION_STATE_REQUIRED")
    status = _normalize_verification(state.verification_status)
    if status not in VERIFICATION:
        raise ValueError("INVALID_VERIFICATION_STATUS")
    if state.attribution_status not in ATTRIBUTION:
        raise ValueError("INVALID_ATTRIBUTION_STATUS")
    if state.temporal_status not in TEMPORAL:
        raise ValueError("INVALID_TEMPORAL_STATUS")

    premises = []
    premise_ids = set()
    for premise in state.premise_evaluations:
        if not isinstance(premise, PremiseEvaluation):
            raise ValueError("INVALID_PREMISE_EVALUATION")
        if not premise.premise_id or premise.premise_id in premise_ids:
            raise ValueError("DUPLICATE_PREMISE_ID")
        premise_ids.add(premise.premise_id)
        premise_status = _normalize_verification(premise.status)
        if premise_status not in VERIFICATION:
            raise ValueError("INVALID_PREMISE_VERIFICATION_STATUS")
        premises.append(replace(premise, status=premise_status))

    evidence_ids = tuple(state.attribution_evidence_ids)
    if state.attribution_status == "AUTHOR_EXPLICIT":
        available = set(available_evidence_ids or ())
        if not evidence_ids:
            raise ValueError("AUTHOR_EXPLICIT_REQUIRES_SOURCE_EVIDENCE")
        if any(
            not isinstance(evidence_id, str)
            or not evidence_id.strip()
            or evidence_id not in available
            for evidence_id in evidence_ids
        ):
            raise ValueError("AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN")

    return replace(
        state,
        verification_status=status,
        premise_evaluations=tuple(premises),
        attribution_evidence_ids=evidence_ids,
    )

def assessment_warnings(state: ClaimEvaluationState) -> tuple[str, ...]:
    if (
        state.verification_status == "VERIFIED"
        and any(p.status == "CONTRADICTED" for p in state.premise_evaluations)
    ):
        return ("CLAIM_VERIFIED_WITH_CONTRADICTED_PREMISE",)
    return ()

def align_evidence(*, relation:str, target_id:str, evidence_id:str)->dict:
    if relation not in ALIGNMENT: raise ValueError("INVALID_ALIGNMENT")
    if not target_id or not evidence_id: raise ValueError("EVIDENCE_ALIGNMENT_IDS_REQUIRED")
    return {"evidence_id":evidence_id,"target_id":target_id,"relation":relation,"status":"UNASSESSED","is_evidence":False}
