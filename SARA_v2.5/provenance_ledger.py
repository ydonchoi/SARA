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


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _is_registered_revision(events: list[dict[str, Any]], claim_id: str, revision_id: str) -> bool:
    return any(
        event.get("event_type") == "CLAIM_REVISION_REGISTERED"
        and event.get("claim_id") == claim_id
        and event.get("revision_id") == revision_id
        for event in events
    )


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
        if self._events and not self._verify_event_semantics():
            raise ProvenanceLedgerError("INVALID_IMPORTED_EVENT_HISTORY")

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(event) for event in self._events)

    @property
    def head_hash(self) -> str:
        return self._events[-1].get("event_hash", GENESIS_HASH) if self._events else GENESIS_HASH

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
        if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
            raise ProvenanceLedgerError("INVALID_EVENT_TYPE")
        if not isinstance(payload, Mapping):
            raise ProvenanceLedgerError("EVENT_PAYLOAD_MUST_BE_MAPPING")
        if any(item["event_id"] == event_id for item in self._events):
            raise ProvenanceLedgerError("DUPLICATE_EVENT_ID")

        safe_payload = deepcopy(dict(payload))
        self._validate_next_event(
            event_type=event_type,
            claim_id=claim_id,
            revision_id=revision_id,
            input_digest=input_digest,
            payload=safe_payload,
            prior_events=self._events,
        )
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

    @staticmethod
    def _find_event(events: list[dict[str, Any]], event_id: str) -> dict[str, Any] | None:
        return next((event for event in events if event.get("event_id") == event_id), None)

    @staticmethod
    def _registered_revision(
        events: list[dict[str, Any]], claim_id: str, revision_id: str
    ) -> dict[str, Any] | None:
        return next((
            event for event in reversed(events)
            if event.get("event_type") == "CLAIM_REVISION_REGISTERED"
            and event.get("claim_id") == claim_id
            and event.get("revision_id") == revision_id
        ), None)

    @classmethod
    def _validate_next_event(
        cls,
        *,
        event_type: str,
        claim_id: str,
        revision_id: str,
        input_digest: str,
        payload: Mapping[str, Any],
        prior_events: list[dict[str, Any]],
    ) -> None:
        if not isinstance(event_type, str) or event_type not in EVENT_TYPES:
            raise ProvenanceLedgerError("INVALID_EVENT_TYPE")
        for value, error in (
            (claim_id, "CLAIM_ID_REQUIRED"),
            (revision_id, "REVISION_ID_REQUIRED"),
            (input_digest, "EVENT_INPUT_DIGEST_REQUIRED"),
        ):
            if not _is_nonempty_string(value):
                raise ProvenanceLedgerError(error)
        if not isinstance(payload, Mapping):
            raise ProvenanceLedgerError("EVENT_PAYLOAD_MUST_BE_MAPPING")
        registered = cls._registered_revision(prior_events, claim_id, revision_id)

        if event_type == "CLAIM_REVISION_REGISTERED":
            digest = payload.get("content_digest")
            if not _is_nonempty_string(digest) or digest != input_digest:
                raise ProvenanceLedgerError("CLAIM_REVISION_DIGEST_MISMATCH")
            existing_revision = cls._registered_revision(prior_events, claim_id, revision_id)
            if existing_revision is not None:
                existing_digest = existing_revision.get("payload", {}).get("content_digest")
                if existing_digest != digest:
                    raise ProvenanceLedgerError("CLAIM_REVISION_ID_REBOUND_TO_DIFFERENT_DIGEST")
                raise ProvenanceLedgerError("CLAIM_REVISION_ALREADY_REGISTERED")
            return

        if event_type in {
            "EVALUATOR_RUN_COMPLETED",
            "VERIFICATION_RESULT_PROPOSED",
            "HUMAN_REVIEW_RESOLUTION",
            "CLAIM_STATUS_COMMITTED",
        }:
            if registered is None:
                if event_type == "CLAIM_STATUS_COMMITTED":
                    raise ProvenanceLedgerError("COMMIT_REVISION_NOT_REGISTERED")
                raise ProvenanceLedgerError("EVENT_REVISION_NOT_REGISTERED")
            if input_digest != registered.get("payload", {}).get("content_digest"):
                raise ProvenanceLedgerError("EVENT_INPUT_DIGEST_MISMATCH")

        if event_type == "EVALUATOR_RUN_COMPLETED":
            if "verification_status" in payload or "proposed_verification_status" in payload:
                raise ProvenanceLedgerError("EVALUATOR_EVENT_MUST_NOT_SET_VERIFICATION_STATUS")
            execution = payload.get("execution_status")
            if execution not in {"SUCCEEDED", "FAILED", "TIMEOUT", "INVALID_OUTPUT", "INCOMPLETE"}:
                raise ProvenanceLedgerError("INVALID_EVALUATOR_EXECUTION_STATUS")
            if execution != "SUCCEEDED" and payload.get("signal_status") != "NOT_AVAILABLE":
                raise ProvenanceLedgerError("FAILED_EVALUATOR_SIGNAL_MUST_BE_NOT_AVAILABLE")

        elif event_type == "REVERIFICATION_ATTEMPT_COMPLETED":
            if "verification_status" in payload:
                raise ProvenanceLedgerError("REVERIFICATION_ATTEMPT_MUST_NOT_COMMIT_STATUS")
            execution = payload.get("execution_status")
            if execution not in {"FAILED", "TIMEOUT", "INVALID_OUTPUT", "INCOMPLETE"}:
                raise ProvenanceLedgerError("INVALID_FAILED_REVERIFICATION_STATUS")
            if payload.get("commit_status", "NOT_COMMITTED") != "NOT_COMMITTED":
                raise ProvenanceLedgerError("FAILED_REVERIFICATION_MUST_NOT_COMMIT")

        elif event_type == "VERIFICATION_RESULT_PROPOSED":
            if "verification_status" in payload:
                raise ProvenanceLedgerError("PROPOSED_RESULT_MUST_NOT_SET_COMMITTED_STATUS")
            if payload.get("proposed_verification_status") not in COMMITTED_STATUSES:
                raise ProvenanceLedgerError("INVALID_PROPOSED_VERIFICATION_STATUS")
            if not _is_nonempty_string(payload.get("external_result_id")):
                raise ProvenanceLedgerError("PROPOSED_RESULT_ID_REQUIRED")
            result_prov = payload.get("external_result_provenance_ids")
            if (
                not isinstance(result_prov, (list, tuple))
                or not result_prov
                or any(not _is_nonempty_string(item) for item in result_prov)
                or len(set(result_prov)) != len(result_prov)
            ):
                raise ProvenanceLedgerError("PROPOSED_RESULT_PROVENANCE_REQUIRED")
            input_prov = payload.get("input_provenance_ids", [])
            if not isinstance(input_prov, (list, tuple)) or any(not _is_nonempty_string(item) for item in input_prov):
                raise ProvenanceLedgerError("INVALID_INPUT_PROVENANCE")
            if set(input_prov) & set(result_prov):
                raise ProvenanceLedgerError("RESULT_PROVENANCE_REUSES_INPUT_PROVENANCE")
            for field in ("evidence_digest", "verifier_revision", "verification_contract_revision"):
                if not _is_nonempty_string(payload.get(field)):
                    raise ProvenanceLedgerError(f"PROPOSED_RESULT_{field.upper()}_REQUIRED")
            if payload.get("commit_status", "NOT_COMMITTED") != "NOT_COMMITTED":
                raise ProvenanceLedgerError("PROPOSED_RESULT_MUST_NOT_COMMIT")

        elif event_type == "HUMAN_REVIEW_RESOLUTION":
            if not _is_nonempty_string(payload.get("reviewer_id")):
                raise ProvenanceLedgerError("REVIEWER_ID_REQUIRED")
            if payload.get("decision") not in {"ACCEPT", "REJECT", "REQUEST_REVISION"}:
                raise ProvenanceLedgerError("INVALID_HUMAN_REVIEW_DECISION")
            if not _is_nonempty_string(payload.get("rationale")):
                raise ProvenanceLedgerError("HUMAN_REVIEW_RATIONALE_REQUIRED")
            proposal_event_id = payload.get("proposal_event_id")
            if proposal_event_id is not None:
                proposal = cls._find_event(prior_events, proposal_event_id)
                if (
                    proposal is None
                    or proposal.get("event_type") != "VERIFICATION_RESULT_PROPOSED"
                    or proposal.get("claim_id") != claim_id
                    or proposal.get("revision_id") != revision_id
                ):
                    raise ProvenanceLedgerError("REVIEW_PROPOSAL_BINDING_MISMATCH")

        elif event_type == "CLAIM_STATUS_COMMITTED":
            status = payload.get("verification_status")
            if status not in COMMITTED_STATUSES:
                raise ProvenanceLedgerError("INVALID_COMMITTED_VERIFICATION_STATUS")
            review_event_id = payload.get("review_event_id")
            proposal_event_id = payload.get("proposal_event_id")
            if not _is_nonempty_string(review_event_id):
                raise ProvenanceLedgerError("STATUS_COMMIT_REVIEW_EVENT_REQUIRED")
            if not _is_nonempty_string(proposal_event_id):
                raise ProvenanceLedgerError("STATUS_COMMIT_PROPOSAL_EVENT_REQUIRED")
            proposal = cls._find_event(prior_events, proposal_event_id)
            if (
                proposal is None
                or proposal.get("event_type") != "VERIFICATION_RESULT_PROPOSED"
                or proposal.get("claim_id") != claim_id
                or proposal.get("revision_id") != revision_id
                or proposal.get("payload", {}).get("proposed_verification_status") != status
            ):
                raise ProvenanceLedgerError("STATUS_COMMIT_PROPOSAL_BINDING_MISMATCH")
            proposal_payload = proposal.get("payload", {})
            for field in ("evidence_digest", "verifier_revision", "verification_contract_revision"):
                if (
                    not _is_nonempty_string(payload.get(field))
                    or payload.get(field) != proposal_payload.get(field)
                ):
                    raise ProvenanceLedgerError("STATUS_COMMIT_VERSION_BINDING_MISMATCH")
            review = cls._find_event(prior_events, review_event_id)
            if (
                review is None
                or review.get("event_type") != "HUMAN_REVIEW_RESOLUTION"
                or review.get("claim_id") != claim_id
                or review.get("revision_id") != revision_id
                or review.get("payload", {}).get("decision") != "ACCEPT"
                or review.get("payload", {}).get("proposal_event_id") != proposal_event_id
            ):
                raise ProvenanceLedgerError("STATUS_COMMIT_REVIEW_NOT_ACCEPTED")

    def _verify_event_semantics(self) -> bool:
        prior: list[dict[str, Any]] = []
        try:
            for event in self._events:
                if not isinstance(event, Mapping):
                    return False
                for key in ("event_id", "event_type", "claim_id", "revision_id", "actor_id", "occurred_at", "input_digest"):
                    if not _is_nonempty_string(event.get(key)):
                        return False
                if not isinstance(event.get("payload"), Mapping):
                    return False
                self._validate_next_event(
                    event_type=event["event_type"],
                    claim_id=event["claim_id"],
                    revision_id=event["revision_id"],
                    input_digest=event["input_digest"],
                    payload=event["payload"],
                    prior_events=prior,
                )
                prior.append(event)
        except (KeyError, TypeError, ProvenanceLedgerError):
            return False
        return True

    def verify_history(self) -> dict[str, Any]:
        """Verify both hash-chain integrity and event transition semantics."""
        chain = self.verify_chain()
        semantic_valid = self._verify_event_semantics()
        return {
            "valid": chain["valid"] and semantic_valid,
            "chain_valid": chain["valid"],
            "semantic_history_valid": semantic_valid,
            "event_count": chain["event_count"],
            "head_hash": chain["head_hash"],
            "problems": list(chain["problems"]) + (
                [] if semantic_valid else [{"error": "EVENT_TRANSITION_POLICY_VIOLATION"}]
            ),
            "is_evidence": False,
        }

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
        history = self.verify_history()
        if not history["valid"]:
            raise ProvenanceLedgerError("INVALID_PROVENANCE_HISTORY")
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

        current_status = (
            committed_status
            if committed_revision_id is not None and committed_revision_id == current_revision_id
            else None
        )
        return {
            "claim_id": claim_id,
            "current_revision_id": current_revision_id,
            "committed_verification_status": current_status,
            "last_committed_verification_status": committed_status,
            "committed_status_current": (
                committed_revision_id is not None
                and committed_revision_id == current_revision_id
            ),
            "reverification_required": (
                current_revision_id is not None
                and committed_revision_id != current_revision_id
            ),
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
