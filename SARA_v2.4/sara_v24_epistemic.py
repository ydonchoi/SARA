"""SARA v2.4 epistemic model.

Pure validation layer for Claim/Premise/Evidence/Context state.
It does not fetch sources and does not infer truth from model output.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

TYPES={"FACT","INTERPRETATION","INFERENCE","HYPOTHESIS","SIMULATION"}
VERIFICATION={"VERIFIED","PARTIALLY VERIFIED","UNVERIFIED","CONTRADICTED"}
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

def validate_state(state: ClaimEvaluationState)->ClaimEvaluationState:
    if state.verification_status not in VERIFICATION: raise ValueError("INVALID_VERIFICATION_STATUS")
    if state.attribution_status not in ATTRIBUTION: raise ValueError("INVALID_ATTRIBUTION_STATUS")
    if state.temporal_status not in TEMPORAL: raise ValueError("INVALID_TEMPORAL_STATUS")
    for p in state.premise_evaluations:
        if p.status not in VERIFICATION: raise ValueError("INVALID_PREMISE_VERIFICATION_STATUS")
    if state.attribution_status=="AUTHOR_EXPLICIT" and state.temporal_status!="HISTORICAL":
        raise ValueError("AUTHOR_EXPLICIT_REQUIRES_HISTORICAL_CONTEXT")
    return state

def align_evidence(*, relation:str, target_id:str, evidence_id:str)->dict:
    if relation not in ALIGNMENT: raise ValueError("INVALID_ALIGNMENT")
    if not target_id or not evidence_id: raise ValueError("EVIDENCE_ALIGNMENT_IDS_REQUIRED")
    return {"evidence_id":evidence_id,"target_id":target_id,"relation":relation,"status":"UNASSESSED"}
