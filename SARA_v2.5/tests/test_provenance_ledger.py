from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from provenance_ledger import GENESIS_HASH, ProvenanceEventLedger, ProvenanceLedgerError


def append(
    ledger,
    event_id="EV-1",
    event_type="VERIFICATION_RESULT_PROPOSED",
    claim_id="C1",
    revision_id="R1",
    payload=None,
):
    if payload is None:
        if event_type == "CLAIM_REVISION_REGISTERED":
            payload = {"content_digest": "CLAIM-DIGEST-1"}
        elif event_type == "VERIFICATION_RESULT_PROPOSED":
            payload = {
                "proposed_verification_status": "VERIFIED",
                "external_result_id": f"RESULT-{event_id}",
                "external_result_provenance_ids": [f"RESULT-PROV-{event_id}"],
                "input_provenance_ids": [],
                "evidence_digest": "EVIDENCE-DIGEST-1",
                "verifier_revision": "verify-1",
                "verification_contract_revision": "contract-1",
                "commit_status": "NOT_COMMITTED",
            }
        elif event_type == "EVALUATOR_RUN_COMPLETED":
            payload = {"execution_status": "SUCCEEDED", "signal_status": "NO_ISSUE_REPORTED"}
        else:
            payload = {}
    if event_type == "CLAIM_REVISION_REGISTERED":
        input_digest = payload.get("content_digest")
    else:
        registered = next((
            event for event in reversed(ledger.events)
            if event.get("event_type") == "CLAIM_REVISION_REGISTERED"
            and event.get("claim_id") == claim_id
            and event.get("revision_id") == revision_id
        ), None)
        input_digest = (
            registered["payload"]["content_digest"]
            if registered is not None else "UNBOUND-DIGEST"
        )
    return ledger.append_event(
        event_id=event_id,
        event_type=event_type,
        claim_id=claim_id,
        revision_id=revision_id,
        actor_id="test-runner",
        occurred_at="2026-10-19T00:00:00Z",
        input_digest=input_digest,
        payload=payload,
    )


def proposal_payload(status="VERIFIED", event_id="EV-PROPOSAL"):
    return {
        "proposed_verification_status": status,
        "external_result_id": f"RESULT-{event_id}",
        "external_result_provenance_ids": [f"RESULT-PROV-{event_id}"],
        "input_provenance_ids": [],
        "evidence_digest": "EVIDENCE-DIGEST-1",
        "verifier_revision": "verify-1",
        "verification_contract_revision": "contract-1",
        "commit_status": "NOT_COMMITTED",
    }


def register(ledger, event_id="REV-REG", claim_id="C1", revision_id="R1", digest="D1"):
    return append(
        ledger, event_id, "CLAIM_REVISION_REGISTERED", claim_id, revision_id,
        {"content_digest": digest},
    )


def test_empty_ledger_has_genesis_head_and_valid_chain():
    ledger = ProvenanceEventLedger()
    result = ledger.verify_chain()
    assert ledger.head_hash == GENESIS_HASH
    assert result["valid"] is True
    assert result["event_count"] == 0
    assert ledger.verify_history()["valid"] is True


def test_append_builds_sequential_hash_chain():
    ledger = ProvenanceEventLedger()
    first = register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    second = append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    assert first["sequence"] == 1
    assert first["previous_event_hash"] == GENESIS_HASH
    assert second["sequence"] == 2
    assert second["previous_event_hash"] == first["event_hash"]
    assert ledger.verify_chain()["valid"] is True


def test_event_output_and_events_property_are_detached_copies():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    event = append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    event["payload"]["proposed_verification_status"] = "CONTRADICTED"
    exposed = ledger.events
    exposed[-1]["payload"]["proposed_verification_status"] = "UNVERIFIED"
    assert ledger.events[-1]["payload"]["proposed_verification_status"] == "VERIFIED"
    assert ledger.verify_chain()["valid"] is True


def test_tampering_event_payload_invalidates_hash_chain():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    raw = [deepcopy(item) for item in ledger.events]
    raw[-1]["payload"]["proposed_verification_status"] = "CONTRADICTED"
    restored = object.__new__(ProvenanceEventLedger)
    restored._events = raw
    result = restored.verify_chain()
    assert result["valid"] is False
    assert any(item["error"] == "EVENT_HASH_MISMATCH" for item in result["problems"])


def test_tampering_event_order_invalidates_chain():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    append(ledger, "EV-2", "EVALUATOR_RUN_COMPLETED")
    raw = list(ledger.events)
    raw.reverse()
    restored = object.__new__(ProvenanceEventLedger)
    restored._events = raw
    assert restored.verify_chain()["valid"] is False


def test_duplicate_event_id_and_unknown_event_type_are_rejected():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    with pytest.raises(ProvenanceLedgerError, match="DUPLICATE_EVENT_ID"):
        append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    with pytest.raises(ProvenanceLedgerError, match="INVALID_EVENT_TYPE"):
        append(ledger, "EV-3", "MAGIC_TRUTH")


def test_invalid_payload_is_rejected_before_ledger_mutation():
    ledger = ProvenanceEventLedger()
    with pytest.raises(ProvenanceLedgerError, match="EVENT_CONTAINS_NON_JSON_VALUE"):
        append(
            ledger, "EV-1", "CLAIM_REVISION_REGISTERED",
            payload={"content_digest": "D1", "invalid": object()},
        )
    assert ledger.events == ()
    assert ledger.verify_chain()["valid"] is True


def test_jsonl_round_trip_preserves_events_and_chain():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="D1")
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    restored = ProvenanceEventLedger.from_jsonl(ledger.to_jsonl())
    assert restored.events == ledger.events
    assert restored.verify_chain()["valid"] is True


def test_invalid_imported_chain_is_rejected():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    raw = ledger.to_jsonl().replace(
        '"proposed_verification_status":"VERIFIED"',
        '"proposed_verification_status":"CONTRADICTED"',
    )
    with pytest.raises(ProvenanceLedgerError, match="INVALID_IMPORTED_EVENT_CHAIN"):
        ProvenanceEventLedger.from_jsonl(raw)


def test_replay_keeps_proposed_status_separate_from_committed_status():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="D1")
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    replay = ledger.replay_claim("C1")
    assert replay["current_revision_id"] == "R1"
    assert replay["committed_verification_status"] is None
    assert replay["proposed_results"][0]["payload"]["proposed_verification_status"] == "VERIFIED"
    assert replay["truthfulness_status"] == "UNASSESSED"


def test_explicit_status_commit_requires_bound_proposal_and_human_review():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="D1")
    append(
        ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED",
        payload=proposal_payload("UNVERIFIED", "EV-2"),
    )
    append(
        ledger, "EV-3", "HUMAN_REVIEW_RESOLUTION",
        payload={
            "reviewer_id": "reviewer-1",
            "decision": "ACCEPT",
            "rationale": "Reviewed the source alignment and accepted the bounded result.",
            "proposal_event_id": "EV-2",
        },
    )
    append(
        ledger, "EV-4", "CLAIM_STATUS_COMMITTED",
        payload={
            "verification_status": "UNVERIFIED",
            "review_event_id": "EV-3",
            "proposal_event_id": "EV-2",
            "evidence_digest": "EVIDENCE-DIGEST-1",
            "verifier_revision": "verify-1",
            "verification_contract_revision": "contract-1",
        },
    )
    replay = ledger.replay_claim("C1")
    assert replay["committed_verification_status"] == "UNVERIFIED"
    assert replay["last_committed_verification_status"] == "UNVERIFIED"
    assert replay["committed_status_current"] is True
    assert replay["reverification_required"] is False
    assert replay["committed_revision_id"] == "R1"
    assert replay["truthfulness_status"] == "UNASSESSED"


def test_commit_without_review_event_is_rejected():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="D1")
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED")
    with pytest.raises(ProvenanceLedgerError, match="STATUS_COMMIT_REVIEW_NOT_ACCEPTED"):
        append(
            ledger, "EV-3", "CLAIM_STATUS_COMMITTED",
            payload={
                "verification_status": "VERIFIED",
                "review_event_id": "MISSING-REVIEW",
                "proposal_event_id": "EV-2",
                "evidence_digest": "EVIDENCE-DIGEST-1",
                "verifier_revision": "verify-1",
                "verification_contract_revision": "contract-1",
            },
        )


def test_commit_rejects_proposal_or_review_from_another_claim_or_revision():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", claim_id="C1", revision_id="R1", digest="D1")
    register(ledger, "EV-2", claim_id="C1", revision_id="R2", digest="D2")
    append(
        ledger, "EV-3", "VERIFICATION_RESULT_PROPOSED", revision_id="R1",
        payload=proposal_payload("VERIFIED", "EV-3"),
    )
    append(
        ledger, "EV-4", "HUMAN_REVIEW_RESOLUTION", revision_id="R1",
        payload={
            "reviewer_id": "reviewer-1", "decision": "ACCEPT",
            "rationale": "Accepted for R1.", "proposal_event_id": "EV-3",
        },
    )
    with pytest.raises(ProvenanceLedgerError, match="STATUS_COMMIT_PROPOSAL_BINDING_MISMATCH"):
        append(
            ledger, "EV-5", "CLAIM_STATUS_COMMITTED", revision_id="R2",
            payload={
                "verification_status": "VERIFIED",
                "review_event_id": "EV-4",
                "proposal_event_id": "EV-3",
            },
        )


def test_invalid_committed_status_is_rejected_at_append():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="D1")
    with pytest.raises(ProvenanceLedgerError, match="INVALID_COMMITTED_VERIFICATION_STATUS"):
        append(
            ledger, "EV-2", "CLAIM_STATUS_COMMITTED",
            payload={
                "verification_status": "ABSOLUTELY_TRUE",
                "review_event_id": "REVIEW-1",
                "proposal_event_id": "EV-1",
            },
        )


def test_new_claim_revision_invalidates_replayed_old_commit():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", revision_id="R1", digest="DIGEST-R1")
    append(
        ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED", revision_id="R1",
        payload=proposal_payload("VERIFIED", "EV-2"),
    )
    append(
        ledger, "EV-3", "HUMAN_REVIEW_RESOLUTION", revision_id="R1",
        payload={
            "reviewer_id": "reviewer-1", "decision": "ACCEPT",
            "rationale": "Reviewed the bounded result.", "proposal_event_id": "EV-2",
        },
    )
    append(
        ledger, "EV-4", "CLAIM_STATUS_COMMITTED", revision_id="R1",
        payload={
            "verification_status": "VERIFIED",
            "review_event_id": "EV-3",
            "proposal_event_id": "EV-2",
            "evidence_digest": "EVIDENCE-DIGEST-1",
            "verifier_revision": "verify-1",
            "verification_contract_revision": "contract-1",
        },
    )
    register(ledger, "EV-5", revision_id="R2", digest="DIGEST-R2")
    replay = ledger.replay_claim("C1")
    assert replay["current_revision_id"] == "R2"
    assert replay["committed_verification_status"] is None
    assert replay["last_committed_verification_status"] == "VERIFIED"
    assert replay["committed_status_current"] is False
    assert replay["reverification_required"] is True


def test_import_rejects_semantically_invalid_history_even_if_hashes_are_recomputed():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", digest="CLAIM-DIGEST-1")
    append(ledger, "EV-2", "EVALUATOR_RUN_COMPLETED")
    events = [deepcopy(event) for event in ledger.events]
    events[1]["event_type"] = "UNRECOGNIZED_TRANSITION"

    previous_hash = "0" * 64
    for sequence, event in enumerate(events, start=1):
        event["sequence"] = sequence
        event["previous_event_hash"] = previous_hash
        event.pop("event_hash", None)
        canonical = json.dumps(
            event, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
        event_hash = sha256(canonical.encode("utf-8")).hexdigest()
        event["event_hash"] = event_hash
        previous_hash = event_hash

    text = "".join(
        json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for event in events
    )
    with pytest.raises(ProvenanceLedgerError, match="INVALID_IMPORTED_EVENT_HISTORY"):
        ProvenanceEventLedger.from_jsonl(text)


def test_claim_revision_id_cannot_be_rebound_to_new_digest():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", claim_id="C1", revision_id="R1", digest="DIGEST-1")
    with pytest.raises(
        ProvenanceLedgerError,
        match="CLAIM_REVISION_ID_REBOUND_TO_DIFFERENT_DIGEST",
    ):
        register(ledger, "EV-2", claim_id="C1", revision_id="R1", digest="DIGEST-2")
    assert len(ledger.events) == 1
    assert ledger.verify_history()["valid"] is True


def test_claim_revision_cannot_be_registered_twice_even_with_same_digest():
    ledger = ProvenanceEventLedger()
    register(ledger, "EV-1", claim_id="C1", revision_id="R1", digest="DIGEST-1")
    with pytest.raises(ProvenanceLedgerError, match="CLAIM_REVISION_ALREADY_REGISTERED"):
        register(ledger, "EV-2", claim_id="C1", revision_id="R1", digest="DIGEST-1")
    assert len(ledger.events) == 1
    assert ledger.verify_history()["valid"] is True


def test_empty_required_event_fields_are_rejected():
    ledger = ProvenanceEventLedger()
    with pytest.raises(ProvenanceLedgerError, match="EVENT_ACTOR_REQUIRED"):
        ledger.append_event(
            event_id="EV-X",
            event_type="EVALUATOR_RUN_COMPLETED",
            claim_id="C1",
            revision_id="R1",
            actor_id=" ",
            occurred_at="2026-10-19T00:00:00Z",
            input_digest="D1",
            payload={},
        )
    assert ledger.events == ()
