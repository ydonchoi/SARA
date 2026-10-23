"""SARA v2.5 prototype: immutable claim revision and stale-verification guard.

This module establishes deterministic revision identity from exact claim text
and scope. It does not infer that two different revisions express the same
proposition; semantic identity changes require explicit review.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

REVIEW_STATES = {"CURRENT", "STALE", "REQUIRES_REVERIFICATION", "UNRESOLVED"}
VERIFICATION_STATUSES = {
    "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"
}
REQUIRED_SCOPE_FIELDS = (
    "population", "setting", "time_range", "modality", "outcome", "causal_strength"
)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("CLAIM_REVISION_CONTAINS_NON_JSON_VALUE") from exc


def _canonical_scope(scope: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(scope, Mapping):
        raise ValueError("CLAIM_SCOPE_MUST_BE_MAPPING")
    canonical = {key: "UNSPECIFIED" for key in REQUIRED_SCOPE_FIELDS}
    canonical.update(dict(scope))
    _canonical_json(canonical)  # validate JSON serializability
    return canonical


@dataclass(frozen=True)
class ClaimRevision:
    claim_id: str
    revision_id: str
    text: str
    scope_json: str
    content_digest: str
    supersedes_revision_id: str | None = None
    derived_from_claim_id: str | None = None
    revision_reason: str = ""
    provenance_ids: tuple[str, ...] = ()

    @property
    def scope(self) -> dict[str, Any]:
        return json.loads(self.scope_json)

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["scope"] = self.scope
        result.pop("scope_json")
        result["provenance_ids"] = list(self.provenance_ids)
        return result


def compute_content_digest(text: str, scope: Mapping[str, Any]) -> str:
    if not isinstance(text, str) or not text:
        raise ValueError("CLAIM_TEXT_REQUIRED")
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n")
    payload = {"text": canonical_text, "scope": _canonical_scope(scope)}
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def create_claim_revision(
    *,
    claim_id: str,
    revision_id: str,
    text: str,
    scope: Mapping[str, Any],
    supersedes_revision_id: str | None = None,
    derived_from_claim_id: str | None = None,
    revision_reason: str = "",
    provenance_ids: tuple[str, ...] = (),
) -> ClaimRevision:
    if not claim_id or not claim_id.strip():
        raise ValueError("CLAIM_ID_REQUIRED")
    if not revision_id or not revision_id.strip():
        raise ValueError("REVISION_ID_REQUIRED")
    if not isinstance(provenance_ids, (tuple, list)) or not provenance_ids:
        raise ValueError("CLAIM_REVISION_PROVENANCE_REQUIRED")
    if any(not isinstance(item, str) or not item.strip() for item in provenance_ids):
        raise ValueError("EMPTY_PROVENANCE_ID")
    if len(set(provenance_ids)) != len(provenance_ids):
        raise ValueError("DUPLICATE_PROVENANCE_ID")
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n") if isinstance(text, str) else text
    canonical_scope = _canonical_scope(scope)
    digest = compute_content_digest(canonical_text, canonical_scope)
    return ClaimRevision(
        claim_id=claim_id,
        revision_id=revision_id,
        text=canonical_text,
        scope_json=_canonical_json(canonical_scope),
        content_digest=digest,
        supersedes_revision_id=supersedes_revision_id,
        derived_from_claim_id=derived_from_claim_id,
        revision_reason=revision_reason,
        provenance_ids=tuple(provenance_ids),
    )


def assess_verification_reuse(
    *,
    revision: ClaimRevision,
    prior_binding: Mapping[str, Any],
    current_verifier_revision: str,
    current_contract_revision: str,
    current_evidence_digest: str,
) -> dict[str, Any]:
    """Decide whether a prior verification binding can be reused for this revision."""
    if not current_verifier_revision:
        raise ValueError("VERIFIER_REVISION_REQUIRED")
    if not current_contract_revision:
        raise ValueError("VERIFICATION_CONTRACT_REVISION_REQUIRED")
    if not current_evidence_digest:
        raise ValueError("CURRENT_EVIDENCE_DIGEST_REQUIRED")
    prior_status = prior_binding.get("verification_status")
    if prior_status not in VERIFICATION_STATUSES:
        raise ValueError("INVALID_PRIOR_VERIFICATION_STATUS")

    reasons = []
    if prior_binding.get("claim_id") != revision.claim_id:
        reasons.append("CLAIM_ID_CHANGED")
    if prior_binding.get("revision_id") != revision.revision_id:
        reasons.append("CLAIM_REVISION_CHANGED")
    if prior_binding.get("content_digest") != revision.content_digest:
        reasons.append("CLAIM_CONTENT_OR_SCOPE_CHANGED")
    if prior_binding.get("verifier_revision") != current_verifier_revision:
        reasons.append("VERIFIER_REVISION_CHANGED")
    if prior_binding.get("verification_contract_revision") != current_contract_revision:
        reasons.append("VERIFICATION_CONTRACT_CHANGED")
    if prior_binding.get("evidence_digest") != current_evidence_digest:
        reasons.append("RELEVANT_EVIDENCE_CHANGED")

    if reasons:
        review_state = "REQUIRES_REVERIFICATION"
    elif prior_status == "UNVERIFIED":
        review_state = "UNRESOLVED"
        reasons.append("PRIOR_RESULT_UNVERIFIED")
    else:
        review_state = "CURRENT"

    return {
        "claim_id": revision.claim_id,
        "revision_id": revision.revision_id,
        "content_digest": revision.content_digest,
        "verification_contract_revision": current_contract_revision,
        "prior_verification_status": prior_status,
        "review_state": review_state,
        "reuse_allowed": review_state == "CURRENT",
        "reasons": reasons,
        "source": "SARA_CLAIM_REVISION_GUARD",
        "is_evidence": False,
    }
