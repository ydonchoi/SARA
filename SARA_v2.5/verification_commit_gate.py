"""Explicit human-review gate for committing a proposed verification status.

A successful verifier result is not committed automatically. This gate verifies
current claim/evidence/verifier/contract bindings against a prior proposal and
requires a bound ACCEPT review event before appending CLAIM_STATUS_COMMITTED.
The caller must enforce reviewer authentication/authorization outside this
transport-neutral prototype. Truthfulness remains UNASSESSED.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from claim_identity import VERIFICATION_STATUSES, compute_content_digest
from provenance_ledger import ProvenanceEventLedger, ProvenanceLedgerError
from reverification_runner import compute_evidence_digest


class VerificationCommitError(ValueError):
    """Raised when a verification proposal is stale, unreviewed, or unbound."""


def commit_verification_proposal(
    *,
    ledger: ProvenanceEventLedger,
    claim_revision: Mapping[str, Any],
    current_evidence: list[Mapping[str, Any]],
    verifier_revision: str,
    verification_contract_revision: str,
    proposal_event_id: str,
    review_event_id: str,
    commit_event_id: str,
    commit_actor_id: str,
    expected_reviewer_id: str | None = None,
) -> dict[str, Any]:
    """Commit one matching proposal only after a recorded ACCEPT review."""
    if not isinstance(ledger, ProvenanceEventLedger):
        raise VerificationCommitError("PROVENANCE_LEDGER_REQUIRED")
    if not ledger.verify_history()["valid"]:
        raise VerificationCommitError("PROVENANCE_HISTORY_INVALID")
    if not isinstance(claim_revision, Mapping):
        raise VerificationCommitError("CURRENT_CLAIM_REVISION_REQUIRED")

    for value, error in (
        (claim_revision.get("claim_id"), "CLAIM_ID_REQUIRED"),
        (claim_revision.get("revision_id"), "CLAIM_REVISION_ID_REQUIRED"),
        (claim_revision.get("text"), "CLAIM_TEXT_REQUIRED"),
        (verifier_revision, "VERIFIER_REVISION_REQUIRED"),
        (verification_contract_revision, "VERIFICATION_CONTRACT_REVISION_REQUIRED"),
        (proposal_event_id, "PROPOSAL_EVENT_ID_REQUIRED"),
        (review_event_id, "REVIEW_EVENT_ID_REQUIRED"),
        (commit_event_id, "COMMIT_EVENT_ID_REQUIRED"),
        (commit_actor_id, "COMMIT_ACTOR_REQUIRED"),
    ):
        if not isinstance(value, str) or not value.strip():
            raise VerificationCommitError(error)

    claim_id = claim_revision["claim_id"]
    revision_id = claim_revision["revision_id"]
    try:
        current_content_digest = compute_content_digest(
            claim_revision["text"], claim_revision["scope"]
        )
        current_evidence_digest = compute_evidence_digest(current_evidence)
    except (KeyError, TypeError, ValueError) as exc:
        raise VerificationCommitError("CURRENT_REVISION_OR_EVIDENCE_INVALID") from exc

    if claim_revision.get("content_digest") != current_content_digest:
        raise VerificationCommitError("CURRENT_CLAIM_DIGEST_MISMATCH")

    replay = ledger.replay_claim(claim_id)
    if replay["current_revision_id"] != revision_id:
        raise VerificationCommitError("CLAIM_REVISION_IS_NOT_CURRENT")

    events = {event["event_id"]: event for event in ledger.events}
    proposal = events.get(proposal_event_id)
    review = events.get(review_event_id)
    if proposal is None or proposal.get("event_type") != "VERIFICATION_RESULT_PROPOSED":
        raise VerificationCommitError("VERIFICATION_PROPOSAL_NOT_FOUND")
    if proposal.get("claim_id") != claim_id or proposal.get("revision_id") != revision_id:
        raise VerificationCommitError("PROPOSAL_CLAIM_REVISION_MISMATCH")
    proposal_payload = proposal.get("payload", {})
    if proposal.get("input_digest") != current_content_digest:
        raise VerificationCommitError("PROPOSAL_CONTENT_DIGEST_STALE")
    if proposal_payload.get("evidence_digest") != current_evidence_digest:
        raise VerificationCommitError("PROPOSAL_EVIDENCE_DIGEST_STALE")
    if proposal_payload.get("verifier_revision") != verifier_revision:
        raise VerificationCommitError("PROPOSAL_VERIFIER_REVISION_STALE")
    if proposal_payload.get("verification_contract_revision") != verification_contract_revision:
        raise VerificationCommitError("PROPOSAL_CONTRACT_REVISION_STALE")
    status = proposal_payload.get("proposed_verification_status")
    if status not in VERIFICATION_STATUSES:
        raise VerificationCommitError("INVALID_PROPOSED_VERIFICATION_STATUS")

    if review is None or review.get("event_type") != "HUMAN_REVIEW_RESOLUTION":
        raise VerificationCommitError("HUMAN_REVIEW_EVENT_NOT_FOUND")
    if review.get("claim_id") != claim_id or review.get("revision_id") != revision_id:
        raise VerificationCommitError("REVIEW_CLAIM_REVISION_MISMATCH")
    review_payload = review.get("payload", {})
    if review_payload.get("decision") != "ACCEPT":
        raise VerificationCommitError("HUMAN_REVIEW_DID_NOT_ACCEPT_PROPOSAL")
    if review_payload.get("proposal_event_id") != proposal_event_id:
        raise VerificationCommitError("REVIEW_PROPOSAL_BINDING_MISMATCH")
    reviewer_id = review_payload.get("reviewer_id")
    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        raise VerificationCommitError("REVIEWER_ID_REQUIRED")
    if expected_reviewer_id is not None and reviewer_id != expected_reviewer_id:
        raise VerificationCommitError("REVIEWER_IDENTITY_MISMATCH")
    if not isinstance(review_payload.get("rationale"), str) or not review_payload["rationale"].strip():
        raise VerificationCommitError("HUMAN_REVIEW_RATIONALE_REQUIRED")

    try:
        event = ledger.append_event(
            event_id=commit_event_id,
            event_type="CLAIM_STATUS_COMMITTED",
            claim_id=claim_id,
            revision_id=revision_id,
            actor_id=commit_actor_id,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            input_digest=current_content_digest,
            payload={
                "verification_status": status,
                "review_event_id": review_event_id,
                "proposal_event_id": proposal_event_id,
                "reviewer_id": reviewer_id,
                "evidence_digest": current_evidence_digest,
                "verifier_revision": verifier_revision,
                "verification_contract_revision": verification_contract_revision,
            },
        )
    except ProvenanceLedgerError as exc:
        raise VerificationCommitError(f"LEDGER_COMMIT_REJECTED:{str(exc)}") from exc

    return {
        "status": "COMMITTED",
        "claim_id": claim_id,
        "revision_id": revision_id,
        "verification_status": status,
        "commit_event_id": event["event_id"],
        "commit_event_hash": event["event_hash"],
        "review_event_id": review_event_id,
        "proposal_event_id": proposal_event_id,
        "truthfulness_status": "UNASSESSED",
        "is_evidence": False,
        "source": "SARA_VERIFICATION_COMMIT_GATE",
    }
