"""SARA v2.5 append-only provenance event ledger.

This is a small, transport-neutral, in-memory ledger with JSONL export/import.
It links events with hashes and can replay explicit state-commit events. An
event record is operational provenance, not research evidence. Proposed
verification results never alter the replayed committed verification status.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
from typing import Any, Iterable, Mapping

GENESIS_HASH = "0" * 64
EVENT_TYPES = {
    "CLAIM_REVISION_REGISTERED",
    "EVALUATOR_RUN_COMPLETED",
    "REVERIFICATION_ATTEMPT_COMPLETED",
    "VERIFICATION_RESULT_PROPOSED",
    "HUMAN_REVIEW_RESOLUTION",
    "CLAIM_STATUS_COMMITTED",
}
COMMITTED_STATUSES = {
    "VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED"
}


class ProvenanceLedgerError(ValueError):
    """Raised when an event violates ledger schema or hash-chain integrity."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ProvenanceLedgerError("EVENT_CONTAINS_NON_JSON_VALUE") from exc


class ProvenanceEventLedger:
    """Append-only event ledger; every returned event is detached from storage."""

    def __init__(self, events: Iterable[Mapping[str, Any]] = ()) -> None:
        self._events: list[dict[str, Any]] = []
        seen = set()
        for raw in events:
            if not isinstance(raw, Mapping):
                raise ProvenanceLedgerError("EVENT_MUST_BE_MAPPING")
            event = dict(raw)
            event_id = event.get("event_id")
            if not isinstance(event_id, str) or not event_id.strip():
                raise ProvenanceLedgerError("EVENT_ID_REQUIRED")
            if event_id in seen:
                raise ProvenanceLedgerError("DUPLICATE_EVENT_ID")
            seen.add(event_id)
            self._events.append(event)
        if self._events and not self.verify_chain()["valid"]:
            raise ProvenanceLedgerError("INVALID_IMPORTED_EVENT_CHAIN")

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)

    @property
    def head_hash(self) -> str:
        return self._events[-1]["event_hash"] if self._events else GENESIS_HASH

    def append_event(
        self,
        *,
        event_id: str,
        event_type: str,
        claim_id: str,
        revision_id: str,
        actor_id: str,
        occurred_at: str,
        input_digest: str,
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        required = (
            (event_id, "EVENT_ID_REQUIRED"),
            (claim_id, "CLAIM_ID_REQUIRED"),
            (revision_id, "REVISION_ID_REQUIRED"),
            (actor_id, "EVENT_ACTOR_REQUIRED"),
            (occurred_at, "EVENT_TIMESTAMP_REQUIRED"),
            (input_digest, "EVENT_INPUT_DIGEST_REQUIRED"),
        )
        for value, error in required:
            if not isinstance(value, str) or not value.strip():
                raise ProvenanceLedgerError(error)
        if event_type not in EVENT_TYPES:
            raise ProvenanceLedgerError("INVALID_EVENT_TYPE")
        if not isinstance(payload, Mapping):
            raise ProvenanceLedgerError("EVENT_PAYLOAD_MUST_BE_MAPPING")
        if any(item["event_id"] == event_id for item in self._events):
            raise ProvenanceLedgerError("DUPLICATE_EVENT_ID")

        safe_payload = deepcopy(dict(payload))
        # Pre-validate JSON encoding before mutating the ledger.
        _canonical(safe_payload)
        base = {
            "sequence": len(self._events) + 1,
            "event_id": event_id,
            "event_type": event_type,
            "claim_id": claim_id,
            "revision_id": revision_id,
            "actor_id": actor_id,
            "occurred_at": occurred_at,
            "input_digest": input_digest,
            "previous_event_hash": self.head_hash,
            "payload": safe_payload,
            "is_evidence": False,
            "source": "SARA_PROVENANCE_EVENT_LEDGER",
        }
        event_hash = sha256(_canonical(base).encode("utf-8")).hexdigest()
        record = {**base, "event_hash": event_hash}
        self._events.append(record)
        return deepcopy(record)

    def verify_chain(self) -> dict[str, Any]:
        previous_hash = GENESIS_HASH
        seen_ids = set()
        problems = []
        for expected_sequence, event in enumerate(self._events, start=1):
            if event.get("sequence") != expected_sequence:
                problems.append({"sequence": expected_sequence, "error": "SEQUENCE_MISMATCH"})
            if event.get("event_id") in seen_ids:
                problems.append({"sequence": expected_sequence, "error": "DUPLICATE_EVENT_ID"})
            seen_ids.add(event.get("event_id"))
            if event.get("previous_event_hash") != previous_hash:
                problems.append({"sequence": expected_sequence, "error": "PREVIOUS_HASH_MISMATCH"})
            base = {key: value for key, value in event.items() if key != "event_hash"}
            try:
                expected_hash = sha256(_canonical(base).encode("utf-8")).hexdigest()
            except ProvenanceLedgerError:
                problems.append({"sequence": expected_sequence, "error": "INVALID_EVENT_CONTENT"})
                expected_hash = None
            if event.get("event_hash") != expected_hash:
                problems.append({"sequence": expected_sequence, "error": "EVENT_HASH_MISMATCH"})
            if not isinstance(event.get("payload"), Mapping):
                problems.append({"sequence": expected_sequence, "error": "PAYLOAD_NOT_OBJECT"})
            previous_hash = event.get("event_hash", "")
        return {
            "valid": not problems,
            "event_count": len(self._events),
            "head_hash": self.head_hash,
            "problems": problems,
            "is_evidence": False,
        }

    def replay_claim(self, claim_id: str) -> dict[str, Any]:
        """Rebuild review metadata without promoting proposed results to state."""
        if not isinstance(claim_id, str) or not claim_id.strip():
            raise ProvenanceLedgerError("CLAIM_ID_REQUIRED")
        matching = [event for event in self._events if event.get("claim_id") == claim_id]
        current_revision_id = None
        committed_status = None
        committed_revision_id = None
        proposed_results = []
        review_events = []
        for event in matching:
            if event["event_type"] == "CLAIM_REVISION_REGISTERED":
                current_revision_id = event["revision_id"]
            elif event["event_type"] == "VERIFICATION_RESULT_PROPOSED":
                proposed_results.append({
                    "event_id": event["event_id"],
                    "revision_id": event["revision_id"],
                    "payload": deepcopy(event["payload"]),
                })
            elif event["event_type"] == "HUMAN_REVIEW_RESOLUTION":
                review_events.append({
                    "event_id": event["event_id"],
                    "revision_id": event["revision_id"],
                    "payload": deepcopy(event["payload"]),
                })
            elif event["event_type"] == "CLAIM_STATUS_COMMITTED":
                status = event["payload"].get("verification_status")
                if status not in COMMITTED_STATUSES:
                    raise ProvenanceLedgerError("INVALID_COMMITTED_VERIFICATION_STATUS")
                committed_status = status
                committed_revision_id = event["revision_id"]

        return {
            "claim_id": claim_id,
            "current_revision_id": current_revision_id,
            "committed_verification_status": committed_status,
            "committed_revision_id": committed_revision_id,
            "proposed_results": proposed_results,
            "review_events": review_events,
            "event_ids": [event["event_id"] for event in matching],
            "ledger_chain_valid": self.verify_chain()["valid"],
            "truthfulness_status": "UNASSESSED",
            "is_evidence": False,
            "source": "SARA_PROVENANCE_LEDGER_REPLAY",
        }

    def to_jsonl(self) -> str:
        """Export one canonical JSON event per line."""
        return "".join(_canonical(event) + "\n" for event in self._events)

    @classmethod
    def from_jsonl(cls, text: str) -> "ProvenanceEventLedger":
        if not isinstance(text, str):
            raise ProvenanceLedgerError("JSONL_MUST_BE_STRING")
        events = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ProvenanceLedgerError(f"INVALID_JSONL_LINE:{line_number}") from exc
            if not isinstance(event, dict):
                raise ProvenanceLedgerError(f"JSONL_EVENT_NOT_OBJECT:{line_number}")
            events.append(event)
        return cls(events)
