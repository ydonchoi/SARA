"""Co-thoughts v2.0 -> SARA v2.4 adapter.

Generation remains unverified; SARA validates supplied epistemic objects.
The adapter does not fetch sources or promote generated text to evidence.
"""
from __future__ import annotations

from typing import Any, Mapping

from sara_v24_epistemic import (
    ClaimEvaluationState,
    PremiseEvaluation,
    assessment_warnings,
    validate_state,
)


class CoThoughtsSARAAdapter:
    revision = "co-thoughts-v2.0/sara-v2.4"

    def evaluate(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        claim = payload.get("claim") or {}
        premises = payload.get("premises") or []
        if not claim.get("id") or not claim.get("text"):
            raise ValueError("CLAIM_ID_AND_TEXT_REQUIRED")

        premise_evaluations = tuple(
            PremiseEvaluation(
                premise_id=str(p["id"]),
                status=str(p.get("verification_status", "UNVERIFIED")),
            )
            for p in premises
            if p.get("id")
        )
        evidence_items = payload.get("evidence") or []
        if not isinstance(evidence_items, (list, tuple)):
            raise ValueError("EVIDENCE_ITEMS_MUST_BE_LIST")
        provenance_ids = payload.get("provenance_ids") or []
        if not isinstance(provenance_ids, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip() for item in provenance_ids
        ):
            raise ValueError("PROVENANCE_IDS_MUST_BE_LIST_OF_NONEMPTY_STRINGS")
        attribution_evidence_ids = claim.get("attribution_evidence_ids") or []
        if not isinstance(attribution_evidence_ids, (list, tuple)) or any(
            not isinstance(item, str) or not item.strip()
            for item in attribution_evidence_ids
        ):
            raise ValueError(
                "ATTRIBUTION_EVIDENCE_IDS_MUST_BE_LIST_OF_NONEMPTY_STRINGS"
            )
        # Attribution evidence must carry an actual source; an arbitrary ID is
        # not enough to support AUTHOR_EXPLICIT attribution.
        available_evidence_ids = {
            item["id"]
            for item in evidence_items
            if (
                isinstance(item, Mapping)
                and isinstance(item.get("id"), str)
                and item["id"].strip()
                and isinstance(item.get("source"), str)
                and item["source"].strip()
            )
        }
        state = validate_state(
            ClaimEvaluationState(
                claim_id=str(claim["id"]),
                verification_status=str(claim.get("verification_status", "UNVERIFIED")),
                attribution_status=str(claim.get("attribution_status", "UNKNOWN")),
                temporal_status=str(claim.get("temporal_status", "CONTEMPORARY")),
                premise_evaluations=premise_evaluations,
                provenance_ids=tuple(provenance_ids),
                attribution_evidence_ids=tuple(attribution_evidence_ids),
            ),
            available_evidence_ids=available_evidence_ids,
        )
        warnings = assessment_warnings(state)
        return {
            "adapter_revision": self.revision,
            "claim_id": state.claim_id,
            "verification_status": state.verification_status,
            "attribution_status": state.attribution_status,
            "attribution_evidence_ids": list(state.attribution_evidence_ids),
            "temporal_status": state.temporal_status,
            "premise_evaluations": [
                {"premise_id": p.premise_id, "status": p.status}
                for p in state.premise_evaluations
            ],
            "assessment_warnings": list(warnings),
            "review_required": bool(warnings),
            "logical_audit_status": "NOT_RUN",
            "provenance_ids": list(state.provenance_ids),
            "is_evidence": False,
            "source": "SARA_VERIFICATION",
        }
