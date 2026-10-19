"""SARA v2.4 epistemic model.

Pure validation layer for Claim/Premise/Evidence/Context state.
It does not fetch sources and does not infer truth from model output.
"""
from __future__ import annotations
from dataclasses import dataclass, replace
from typing import Iterable

TYPES={"FACT","INTERPRETATION","INFERENCE","HYPOTHESIS","SIMULATION"}
VERIFICATION={"VERIFIED","PARTIALLY_VERIFIED","UNVERIFIED","CONTRADICTED"}
VERIFICATION_ALIASES={"PARTIALLY VERIFIED":"PARTIALLY_VERIFIED"}
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

def normalize_verification_status(status: str)->str:
    if not isinstance(status, str): raise ValueError("INVALID_VERIFICATION_STATUS")
    normalized=status.strip().upper()
    return VERIFICATION_ALIASES.get(normalized, normalized)

def validate_state(state: ClaimEvaluationState, *, available_evidence_ids: Iterable[str] | None = None)->ClaimEvaluationState:
    if not state.claim_id or not state.claim_id.strip(): raise ValueError("CLAIM_ID_REQUIRED")
    if state.attribution_status not in ATTRIBUTION: raise ValueError("INVALID_ATTRIBUTION_STATUS")
    if state.temporal_status not in TEMPORAL: raise ValueError("INVALID_TEMPORAL_STATUS")
    status=normalize_verification_status(state.verification_status)
    if status not in VERIFICATION: raise ValueError("INVALID_VERIFICATION_STATUS")
    normalized=[]
    seen=set()
    for p in state.premise_evaluations:
        if not p.premise_id or not p.premise_id.strip(): raise ValueError("PREMISE_ID_REQUIRED")
        if p.premise_id in seen: raise ValueError("DUPLICATE_PREMISE_ID")
        seen.add(p.premise_id)
        pstatus=normalize_verification_status(p.status)
        if pstatus not in VERIFICATION: raise ValueError("INVALID_PREMISE_VERIFICATION_STATUS")
        normalized.append(replace(p,status=pstatus))
    if any(not isinstance(x,str) or not x.strip() for x in state.provenance_ids): raise ValueError("EMPTY_PROVENANCE_ID")
    if any(not isinstance(x,str) or not x.strip() for x in state.attribution_evidence_ids): raise ValueError("EMPTY_ATTRIBUTION_EVIDENCE_ID")
    if state.attribution_status=="AUTHOR_EXPLICIT" and not state.attribution_evidence_ids:
        raise ValueError("AUTHOR_EXPLICIT_REQUIRES_SOURCE_EVIDENCE")
    if available_evidence_ids is not None and state.attribution_status=="AUTHOR_EXPLICIT" and not set(state.attribution_evidence_ids).issubset(set(available_evidence_ids)):
        raise ValueError("AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN")
    return replace(state,verification_status=status,premise_evaluations=tuple(normalized))

def align_evidence(*, relation:str, target_id:str, evidence_id:str)->dict:
    if relation not in ALIGNMENT: raise ValueError("INVALID_ALIGNMENT")
    if not target_id or not evidence_id: raise ValueError("EVIDENCE_ALIGNMENT_IDS_REQUIRED")
    return {"evidence_id":evidence_id,"target_id":target_id,"relation":relation,"status":"UNASSESSED"}
