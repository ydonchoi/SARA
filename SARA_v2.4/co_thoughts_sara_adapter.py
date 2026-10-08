"""Co-thoughts v2.0 -> SARA v2.4 adapter.

Generation remains unverified; SARA evaluates the supplied epistemic objects.
"""
from __future__ import annotations
from typing import Any, Mapping
from sara_v24_epistemic import ClaimEvaluationState, PremiseEvaluation, validate_state

class CoThoughtsSARAAdapter:
    revision="co-thoughts-v2.0/sara-v2.4"

    def evaluate(self, payload:Mapping[str,Any])->dict[str,Any]:
        claim=payload.get("claim") or {}
        premises=payload.get("premises") or []
        if not claim.get("id") or not claim.get("text"): raise ValueError("CLAIM_ID_AND_TEXT_REQUIRED")
        p_eval=tuple(PremiseEvaluation(str(p["id"]), str(p.get("verification_status","UNVERIFIED"))) for p in premises if p.get("id"))
        state=validate_state(ClaimEvaluationState(
            claim_id=str(claim["id"]),
            verification_status=str(claim.get("verification_status","UNVERIFIED")),
            attribution_status=str(claim.get("attribution_status","UNKNOWN")),
            temporal_status=str(claim.get("temporal_status","CONTEMPORARY")),
            premise_evaluations=p_eval,
            provenance_ids=tuple(payload.get("provenance_ids") or ()),
        ))
        return {
            "adapter_revision":self.revision,
            "claim_id":state.claim_id,
            "verification_status":state.verification_status,
            "attribution_status":state.attribution_status,
            "temporal_status":state.temporal_status,
            "premise_evaluations":[{"premise_id":p.premise_id,"status":p.status} for p in state.premise_evaluations],
            "provenance_ids":list(state.provenance_ids),
            "is_evidence":False,
            "source":"SARA_VERIFICATION",
        }
