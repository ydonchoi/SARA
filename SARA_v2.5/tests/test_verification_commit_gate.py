from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_identity import compute_content_digest
from provenance_ledger import ProvenanceEventLedger
from reverification_runner import compute_evidence_digest
from verification_commit_gate import VerificationCommitError, commit_verification_proposal


SCOPE = {
    "population": "adults",
    "setting": "one hospital",
    "time_range": "2020-2024",
    "modality": "observational",
    "outcome": "readmission",
    "causal_strength": "association",
}
EVIDENCE = [{"id": "E1", "provenance_id": "SRC-PROV-1", "text": "Independent source"}]


def current_revision(claim_id="C1", revision_id="R1", text="A bounded claim."):
    return {
        "claim_id": claim_id,
        "revision_id": revision_id,
        "text": text,
        "scope": dict(SCOPE),
        "content_digest": compute_content_digest(text, SCOPE),
    }


def prepared_ledger(
    *,
    status="VERIFIED",
    decision="ACCEPT",
    review_proposal_id="PROP-1",
    revision=None,
    evidence=None,
    verifier_revision="verify-1",
    contract_revision="contract-1",
    review_rationale="Reviewed the evidence alignment and accepted the bounded result.",
):
    revision = revision or current_revision()
    evidence = EVIDENCE if evidence is None else evidence
    claim_digest = revision["content_digest"]
    evidence_digest = compute_evidence_digest(evidence)
    ledger = ProvenanceEventLedger()
    ledger.append_event(
        event_id="REG-1",
        event_type="CLAIM_REVISION_REGISTERED",
        claim_id=revision["claim_id"],
        revision_id=revision["revision_id"],
        actor_id="test-runner",
        occurred_at="2026-10-19T00:00:00Z",
        input_digest=claim_digest,
        payload={"content_digest": claim_digest},
    )
    ledger.append_event(
        event_id="PROP-1",
        event_type="VERIFICATION_RESULT_PROPOSED",
        claim_id=revision["claim_id"],
        revision_id=revision["revision_id"],
        actor_id="verifier",
        occurred_at="2026-10-19T00:00:01Z",
        input_digest=claim_digest,
        payload={
            "proposed_verification_status": status,
            "external_result_id": "EXT-1",
            "external_result_provenance_ids": ["RESULT-PROV-1"],
            "input_provenance_ids": [
                item["provenance_id"] for item in evidence if item.get("provenance_id")
            ],
            "evidence_digest": evidence_digest,
            "verifier_revision": verifier_revision,
            "verification_contract_revision": contract_revision,
            "commit_status": "NOT_COMMITTED",
        },
    )
    ledger.append_event(
        event_id="REV-1",
        event_type="HUMAN_REVIEW_RESOLUTION",
        claim_id=revision["claim_id"],
        revision_id=revision["revision_id"],
        actor_id="reviewer-1",
        occurred_at="2026-10-19T00:00:02Z",
        input_digest=claim_digest,
        payload={
            "reviewer_id": "reviewer-1",
            "decision": decision,
            "rationale": review_rationale,
            "proposal_event_id": review_proposal_id,
        },
    )
    return ledger, revision, evidence, evidence_digest


def commit(ledger, revision, evidence, evidence_digest, **overrides):
    args = {
        "ledger": ledger,
        "claim_revision": revision,
        "current_evidence": evidence,
        "verifier_revision": "verify-1",
        "verification_contract_revision": "contract-1",
        "proposal_event_id": "PROP-1",
        "review_event_id": "REV-1",
        "commit_event_id": "COMMIT-1",
        "commit_actor_id": "commit-gateway",
        "expected_reviewer_id": "reviewer-1",
    }
    args.update(overrides)
    return commit_verification_proposal(**args)


def test_status_commit_requires_proposal_and_accepted_review_and_keeps_truthfulness_unassessed():
    ledger, revision, evidence, evidence_digest = prepared_ledger()
    result = commit(ledger, revision, evidence, evidence_digest)
    assert result["status"] == "COMMITTED"
    assert result["verification_status"] == "VERIFIED"
    assert result["truthfulness_status"] == "UNASSESSED"
    assert result["is_evidence"] is False
    replay = ledger.replay_claim("C1")
    assert replay["committed_verification_status"] == "VERIFIED"
    assert replay["committed_status_current"] is True
    assert ledger.verify_chain()["valid"] is True


def test_proposed_result_without_accept_review_cannot_be_committed():
    ledger, revision, evidence, digest = prepared_ledger(decision="REJECT")
    with pytest.raises(VerificationCommitError, match="HUMAN_REVIEW_DID_NOT_ACCEPT_PROPOSAL"):
        commit(ledger, revision, evidence, digest)
    assert ledger.replay_claim("C1")["committed_verification_status"] is None


def test_commit_must_reference_exact_proposal():
    ledger, revision, evidence, digest = prepared_ledger()
    with pytest.raises(VerificationCommitError, match="VERIFICATION_PROPOSAL_NOT_FOUND"):
        commit(ledger, revision, evidence, digest, proposal_event_id="OTHER-PROP")


def test_claim_revision_and_content_digest_must_be_current():
    ledger, revision, evidence, digest = prepared_ledger()
    stale = dict(revision)
    stale["revision_id"] = "R-OLD"
    with pytest.raises(VerificationCommitError, match="CLAIM_REVISION_IS_NOT_CURRENT"):
        commit(ledger, stale, evidence, digest)

    stale = dict(revision, content_digest="STALE-DIGEST")
    with pytest.raises(VerificationCommitError, match="CURRENT_CLAIM_DIGEST_MISMATCH"):
        commit(ledger, stale, evidence, digest)


def test_current_evidence_change_blocks_old_proposal():
    ledger, revision, evidence, digest = prepared_ledger()
    changed_evidence = evidence + [{"id": "E2", "provenance_id": "SRC-PROV-2"}]
    with pytest.raises(VerificationCommitError, match="PROPOSAL_EVIDENCE_DIGEST_STALE"):
        commit(ledger, revision, changed_evidence, digest)


def test_verifier_or_contract_change_blocks_old_proposal():
    ledger, revision, evidence, digest = prepared_ledger()
    with pytest.raises(VerificationCommitError, match="PROPOSAL_VERIFIER_REVISION_STALE"):
        commit(ledger, revision, evidence, digest, verifier_revision="verify-2")

    ledger, revision, evidence, digest = prepared_ledger()
    with pytest.raises(VerificationCommitError, match="PROPOSAL_CONTRACT_REVISION_STALE"):
        commit(ledger, revision, evidence, digest, verification_contract_revision="contract-2")


def test_expected_reviewer_identity_can_be_checked():
    ledger, revision, evidence, digest = prepared_ledger()
    with pytest.raises(VerificationCommitError, match="REVIEWER_IDENTITY_MISMATCH"):
        commit(ledger, revision, evidence, digest, expected_reviewer_id="untrusted-reviewer")


def test_duplicate_commit_event_id_is_rejected_without_mutating_status():
    ledger, revision, evidence, digest = prepared_ledger()
    commit(ledger, revision, evidence, digest)
    with pytest.raises(VerificationCommitError, match="LEDGER_COMMIT_REJECTED:DUPLICATE_EVENT_ID"):
        commit(ledger, revision, evidence, digest)
    assert ledger.replay_claim("C1")["committed_verification_status"] == "VERIFIED"
