from copy import deepcopy
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from provenance_ledger import (
    GENESIS_HASH,
    ProvenanceEventLedger,
    ProvenanceLedgerError,
)


def append(ledger, event_id="EV-1", event_type="VERIFICATION_RESULT_PROPOSED",
           claim_id="C1", revision_id="R1", payload=None):
    return ledger.append_event(
        event_id=event_id,
        event_type=event_type,
        claim_id=claim_id,
        revision_id=revision_id,
        actor_id="test-runner",
        occurred_at="2026-10-19T00:00:00Z",
        input_digest="CLAIM-DIGEST-1",
        payload=payload or {"verification_status": "VERIFIED"},
    )


def test_empty_ledger_has_genesis_head_and_valid_chain():
    ledger = ProvenanceEventLedger()
    result = ledger.verify_chain()
    assert ledger.head_hash == GENESIS_HASH
    assert result["valid"] is True
    assert result["event_count"] == 0


def test_append_builds_sequential_hash_chain():
    ledger = ProvenanceEventLedger()
    first = append(ledger)
    second = append(ledger, event_id="EV-2", event_type="EVALUATOR_RUN_COMPLETED")
    assert first["sequence"] == 1
    assert first["previous_event_hash"] == GENESIS_HASH
    assert second["sequence"] == 2
    assert second["previous_event_hash"] == first["event_hash"]
    assert ledger.verify_chain()["valid"] is True


def test_event_output_and_events_property_are_detached_copies():
    ledger = ProvenanceEventLedger()
    event = append(ledger)
    event["payload"]["verification_status"] = "CONTRADICTED"
    exposed = ledger.events
    exposed[0]["payload"]["verification_status"] = "UNVERIFIED"
    assert ledger.events[0]["payload"]["verification_status"] == "VERIFIED"
    assert ledger.verify_chain()["valid"] is True


def test_tampering_event_payload_invalidates_hash_chain():
    ledger = ProvenanceEventLedger()
    append(ledger)
    raw = [dict(item) for item in ledger.events]
    raw[0] = deepcopy(raw[0])
    raw[0]["payload"]["verification_status"] = "CONTRADICTED"
    restored = object.__new__(ProvenanceEventLedger)
    restored._events = raw
    result = restored.verify_chain()
    assert result["valid"] is False
    assert any(item["error"] == "EVENT_HASH_MISMATCH" for item in result["problems"])


def test_tampering_event_order_invalidates_chain():
    ledger = ProvenanceEventLedger()
    append(ledger, "EV-1")
    append(ledger, "EV-2", "EVALUATOR_RUN_COMPLETED")
    raw = list(ledger.events)
    raw.reverse()
    restored = object.__new__(ProvenanceEventLedger)
    restored._events = raw
    assert restored.verify_chain()["valid"] is False


def test_duplicate_event_id_and_unknown_event_type_are_rejected():
    ledger = ProvenanceEventLedger()
    append(ledger)
    with pytest.raises(ProvenanceLedgerError, match="DUPLICATE_EVENT_ID"):
        append(ledger)
    with pytest.raises(ProvenanceLedgerError, match="INVALID_EVENT_TYPE"):
        append(ledger, event_id="EV-2", event_type="MAGIC_TRUTH")


def test_invalid_payload_is_rejected_before_ledger_mutation():
    ledger = ProvenanceEventLedger()
    with pytest.raises(ProvenanceLedgerError, match="EVENT_CONTAINS_NON_JSON_VALUE"):
        append(ledger, payload={"invalid": object()})
    assert ledger.events == ()
    assert ledger.verify_chain()["valid"] is True


def test_jsonl_round_trip_preserves_events_and_chain():
    ledger = ProvenanceEventLedger()
    append(ledger, "EV-1", "CLAIM_REVISION_REGISTERED", payload={"text": "Claim A"})
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED", payload={"verification_status": "VERIFIED"})
    restored = ProvenanceEventLedger.from_jsonl(ledger.to_jsonl())
    assert restored.events == ledger.events
    assert restored.verify_chain()["valid"] is True


def test_invalid_imported_chain_is_rejected():
    ledger = ProvenanceEventLedger()
    append(ledger)
    raw = ledger.to_jsonl().replace('"verification_status":"VERIFIED"', '"verification_status":"CONTRADICTED"')
    with pytest.raises(ProvenanceLedgerError, match="INVALID_IMPORTED_EVENT_CHAIN"):
        ProvenanceEventLedger.from_jsonl(raw)


def test_replay_keeps_proposed_status_separate_from_committed_status():
    ledger = ProvenanceEventLedger()
    append(ledger, "EV-1", "CLAIM_REVISION_REGISTERED", payload={"text": "Claim A"})
    append(ledger, "EV-2", "VERIFICATION_RESULT_PROPOSED", payload={"verification_status": "VERIFIED"})
    replay = ledger.replay_claim("C1")
    assert replay["current_revision_id"] == "R1"
    assert replay["committed_verification_status"] is None
    assert replay["proposed_results"][0]["payload"]["verification_status"] == "VERIFIED"
    assert replay["truthfulness_status"] == "UNASSESSED"


def test_explicit_status_commit_changes_replayed_status_and_not_truthfulness():
    ledger = ProvenanceEventLedger()
    append(ledger, "EV-1", "CLAIM_REVISION_REGISTERED", payload={"text": "Claim A"})
    append(ledger, "EV-2", "CLAIM_STATUS_COMMITTED", payload={"verification_status": "UNVERIFIED"})
    replay = ledger.replay_claim("C1")
    assert replay["committed_verification_status"] == "UNVERIFIED"
    assert replay["committed_revision_id"] == "R1"
    assert replay["truthfulness_status"] == "UNASSESSED"


def test_invalid_committed_status_is_rejected_during_replay():
    ledger = ProvenanceEventLedger()
    append(ledger, "EV-1", "CLAIM_STATUS_COMMITTED", payload={"verification_status": "ABSOLUTELY_TRUE"})
    with pytest.raises(ProvenanceLedgerError, match="INVALID_COMMITTED_VERIFICATION_STATUS"):
        ledger.replay_claim("C1")


def test_empty_required_event_fields_are_rejected():
    ledger = ProvenanceEventLedger()
    with pytest.raises(ProvenanceLedgerError, match="EVENT_ACTOR_REQUIRED"):
        ledger.append_event(
            event_id="EV-X", event_type="EVALUATOR_RUN_COMPLETED",
            claim_id="C1", revision_id="R1", actor_id=" ",
            occurred_at="2026-10-19T00:00:00Z", input_digest="D1",
            payload={},
        )
    assert ledger.events == ()
