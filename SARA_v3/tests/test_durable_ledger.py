"""G9: SQLite durable ledger — persistence, append-only storage, audit, recovery."""
from __future__ import annotations

import sqlite3

import pytest

from SARA_v3.durable_ledger import SQLiteProvenanceLedger, ledger_from_environment
from SARA_v3.verification import verify_claim_from_sources
from claim_identity import compute_content_digest
from provenance_ledger import ProvenanceLedgerError
from reverification_runner import compute_evidence_digest
from verification_commit_gate import commit_verification_proposal

CLAIM_TEXT = "The policy reduced cases by 20 percent."
SCOPE = {"time_range": "2024"}
EVIDENCE = [{"id": "E1", "provenance_id": "SRC-PROV-1", "text": "Independent source"}]


class Search:
    def __init__(self, item):
        self.item = item

    def search(self, _query, *, count):
        return [self.item]


class Fetcher:
    def __init__(self, item):
        self.item = item

    def search(self, _query):
        return []

    def fetch(self, _url):
        return dict(self.item)


def full_text_source():
    return {"evidence_id": "E1", "url": "https://official.example/study", "title": "Study",
            "access_level": "FULL_TEXT", "content": CLAIM_TEXT, "snippet": "", "source_type": "TEST_SOURCE"}


def propose(ledger, revision_id="R1", text=CLAIM_TEXT):
    item = full_text_source()
    return verify_claim_from_sources(
        {"claim": {"id": "C1", "text": text, "revision_id": revision_id}, "provenance_ids": ["INPUT-PROV-1"]},
        search_provider=Search(item), mcp_source=Fetcher(item),
        relation_assessor=lambda c, ev, t: {"evidence_id": ev["evidence_id"], "relation": "SUPPORTS",
                                            "rationale": "Direct quote.", "support_spans": [CLAIM_TEXT]},
        trusted_source_domains={"official.example"}, ledger=ledger,
    )


def register_and_propose(ledger):
    digest = compute_content_digest(CLAIM_TEXT, SCOPE)
    ledger.append_event(event_id="REG-1", event_type="CLAIM_REVISION_REGISTERED", claim_id="C1",
                        revision_id="R1", actor_id="test", occurred_at="2026-11-03T00:00:00Z",
                        input_digest=digest, payload={"content_digest": digest})
    ledger.append_event(event_id="PROP-1", event_type="VERIFICATION_RESULT_PROPOSED", claim_id="C1",
                        revision_id="R1", actor_id="SARA_V3", occurred_at="2026-11-03T00:00:01Z",
                        input_digest=digest, payload={
                            "proposed_verification_status": "VERIFIED", "external_result_id": "EXT-1",
                            "external_result_provenance_ids": ["RESULT-PROV-1"],
                            "input_provenance_ids": ["SRC-PROV-1"],
                            "evidence_digest": compute_evidence_digest(EVIDENCE),
                            "verifier_revision": "verify-1", "verification_contract_revision": "contract-1",
                            "commit_status": "NOT_COMMITTED"})
    return digest


def test_v3_proposals_persist_across_reopen(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with SQLiteProvenanceLedger(path) as ledger:
        result = propose(ledger)
        head = ledger.head_hash
    assert result["provenance"]["ledger_status"] == "DURABLE_SQLITE"
    assert result["provenance"]["commit_status"] == "NOT_COMMITTED"

    with SQLiteProvenanceLedger(path) as reopened:
        assert reopened.head_hash == head
        assert [e["event_type"] for e in reopened.events] == ["CLAIM_REVISION_REGISTERED",
                                                              "VERIFICATION_RESULT_PROPOSED"]
        assert reopened.replay_claim("C1")["committed_verification_status"] is None
        assert reopened.verify_storage()["valid"] is True
        assert reopened.verify_storage()["matches_loaded_ledger"] is True


def test_storage_rejects_update_and_delete(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with SQLiteProvenanceLedger(path) as ledger:
        propose(ledger)
    connection = sqlite3.connect(path)
    with pytest.raises(sqlite3.IntegrityError, match="LEDGER_APPEND_ONLY"):
        connection.execute("UPDATE provenance_events SET event_json = '{}' WHERE sequence = 1")
    with pytest.raises(sqlite3.IntegrityError, match="LEDGER_APPEND_ONLY"):
        connection.execute("DELETE FROM provenance_events WHERE sequence = 2")
    connection.close()


def test_tampered_storage_is_refused_on_load(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with SQLiteProvenanceLedger(path) as ledger:
        propose(ledger)
    connection = sqlite3.connect(path)
    connection.execute("DROP TRIGGER provenance_events_no_update")
    row = connection.execute("SELECT event_json FROM provenance_events WHERE sequence = 2").fetchone()[0]
    connection.execute("UPDATE provenance_events SET event_json = ? WHERE sequence = 2",
                       (row.replace('"VERIFIED"', '"CONTRADICTED"'),))
    connection.commit()
    connection.close()
    with pytest.raises(ProvenanceLedgerError, match="INVALID_IMPORTED_EVENT_CHAIN"):
        SQLiteProvenanceLedger(path)


def test_concurrent_writer_cannot_fork_the_chain(tmp_path):
    path = tmp_path / "ledger.sqlite"
    first = SQLiteProvenanceLedger(path)
    second = SQLiteProvenanceLedger(path)
    propose(first)
    with pytest.raises(ProvenanceLedgerError, match="LEDGER_CONCURRENT_APPEND"):
        second.append_event(**_registration("C2"))
    assert second.events == ()
    first.close()
    second.close()
    with SQLiteProvenanceLedger(path) as reopened:
        assert len(reopened.events) == 2


def test_failed_storage_write_leaves_memory_unchanged(tmp_path):
    ledger = SQLiteProvenanceLedger(tmp_path / "ledger.sqlite")
    ledger.close()
    with pytest.raises(ProvenanceLedgerError, match="LEDGER_STORAGE_WRITE_FAILED"):
        ledger.append_event(**_registration("C1"))
    assert ledger.events == ()


def test_stale_revision_is_rejected_by_durable_ledger(tmp_path):
    with SQLiteProvenanceLedger(tmp_path / "ledger.sqlite") as ledger:
        propose(ledger, revision_id="R1")
        stale = propose(ledger, revision_id="R1", text="The policy reduced cases by 30 percent.")
        assert stale["provenance"]["ledger_status"] == "FAILED"
        assert len(ledger.events) == 2
        assert ledger.verify_storage()["matches_loaded_ledger"] is True


def test_export_and_restore_round_trip(tmp_path):
    with SQLiteProvenanceLedger(tmp_path / "ledger.sqlite") as ledger:
        propose(ledger)
        exported = ledger.to_jsonl()
        head = ledger.head_hash
    with SQLiteProvenanceLedger.restore_from_jsonl(tmp_path / "restored.sqlite", exported) as restored:
        assert restored.head_hash == head
        assert restored.verify_storage()["valid"] is True
    with pytest.raises(ProvenanceLedgerError, match="LEDGER_RESTORE_TARGET_NOT_EMPTY"):
        SQLiteProvenanceLedger.restore_from_jsonl(tmp_path / "ledger.sqlite", exported)


def test_status_commit_requires_recorded_accept_review_and_persists(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with SQLiteProvenanceLedger(path) as ledger:
        digest = register_and_propose(ledger)
        with pytest.raises(ProvenanceLedgerError, match="STATUS_COMMIT_MUST_USE_VERIFICATION_GATE"):
            ledger.append_event(event_id="FORGED", event_type="CLAIM_STATUS_COMMITTED", claim_id="C1",
                                revision_id="R1", actor_id="attacker", occurred_at="2026-11-03T00:00:02Z",
                                input_digest=digest, payload={"verification_status": "VERIFIED"})
        ledger.append_event(event_id="REV-1", event_type="HUMAN_REVIEW_RESOLUTION", claim_id="C1",
                            revision_id="R1", actor_id="reviewer-1", occurred_at="2026-11-03T00:00:03Z",
                            input_digest=digest, payload={"reviewer_id": "reviewer-1", "decision": "ACCEPT",
                                                          "rationale": "Checked the source span.",
                                                          "proposal_event_id": "PROP-1"})
        commit_verification_proposal(
            ledger=ledger,
            claim_revision={"claim_id": "C1", "revision_id": "R1", "text": CLAIM_TEXT, "scope": SCOPE,
                            "content_digest": digest},
            current_evidence=EVIDENCE, verifier_revision="verify-1",
            verification_contract_revision="contract-1", proposal_event_id="PROP-1",
            review_event_id="REV-1", commit_event_id="COMMIT-1", commit_actor_id="sara-commit-gate",
            expected_reviewer_id="reviewer-1",
        )
    with SQLiteProvenanceLedger(path) as reopened:
        assert reopened.replay_claim("C1")["committed_verification_status"] == "VERIFIED"
        assert reopened.events[-1]["actor_id"] == "sara-commit-gate"


def test_ledger_is_selected_from_environment(tmp_path):
    assert ledger_from_environment({}) is None
    ledger = ledger_from_environment({"SARA_PROVENANCE_LEDGER_PATH": str(tmp_path / "env.sqlite")})
    assert isinstance(ledger, SQLiteProvenanceLedger)
    ledger.close()


def _registration(claim_id):
    digest = compute_content_digest("Another claim.", {})
    return dict(event_id=f"REG-{claim_id}", event_type="CLAIM_REVISION_REGISTERED", claim_id=claim_id,
                revision_id="R1", actor_id="test", occurred_at="2026-11-03T00:00:00Z",
                input_digest=digest, payload={"content_digest": digest})
