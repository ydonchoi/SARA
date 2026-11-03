"""SQLite-backed append-only provenance ledger (reference durable adapter).

Events keep the v2.5 ledger's hash chain and transition rules. Each append is
validated in memory first and then written in one SQLite transaction; the table
rejects UPDATE and DELETE. A write that sees a different stored head (another
process appended) is refused instead of forking the chain.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping

from .provenance import ProvenanceEventLedger

from provenance_ledger import ProvenanceLedgerError, _canonical  # noqa: E402  (path set by .provenance)

_SCHEMA = (
    """CREATE TABLE IF NOT EXISTS provenance_events (
        sequence INTEGER PRIMARY KEY,
        event_id TEXT NOT NULL UNIQUE,
        event_hash TEXT NOT NULL UNIQUE,
        previous_event_hash TEXT NOT NULL,
        event_json TEXT NOT NULL
    )""",
    """CREATE TRIGGER IF NOT EXISTS provenance_events_no_update
        BEFORE UPDATE ON provenance_events
        BEGIN SELECT RAISE(ABORT, 'LEDGER_APPEND_ONLY'); END""",
    """CREATE TRIGGER IF NOT EXISTS provenance_events_no_delete
        BEFORE DELETE ON provenance_events
        BEGIN SELECT RAISE(ABORT, 'LEDGER_APPEND_ONLY'); END""",
)


def _connect(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path, isolation_level=None, timeout=10)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA synchronous=FULL")
    for statement in _SCHEMA:
        connection.execute(statement)
    return connection


def _stored_events(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = connection.execute("SELECT sequence, event_json FROM provenance_events ORDER BY sequence").fetchall()
    events = []
    for sequence, raw in rows:
        try:
            event = json.loads(raw)
        except json.JSONDecodeError:
            raise ProvenanceLedgerError(f"STORED_EVENT_NOT_JSON:{sequence}") from None
        if not isinstance(event, dict) or event.get("sequence") != sequence:
            raise ProvenanceLedgerError(f"STORED_EVENT_SEQUENCE_MISMATCH:{sequence}")
        events.append(event)
    return events


class SQLiteProvenanceLedger(ProvenanceEventLedger):
    """Durable ledger; loading re-verifies the whole stored chain and history."""

    ledger_status = "DURABLE_SQLITE"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._connection = _connect(self.path)
        super().__init__(_stored_events(self._connection))

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> "SQLiteProvenanceLedger":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()

    def append_event(self, **kwargs: Any) -> dict[str, Any]:
        record = super().append_event(**kwargs)
        try:
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                head = self._connection.execute(
                    "SELECT event_hash FROM provenance_events ORDER BY sequence DESC LIMIT 1").fetchone()
                if (head[0] if head else "0" * 64) != record["previous_event_hash"]:
                    raise ProvenanceLedgerError("LEDGER_CONCURRENT_APPEND")
                self._connection.execute(
                    "INSERT INTO provenance_events (sequence, event_id, event_hash, previous_event_hash, event_json)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (record["sequence"], record["event_id"], record["event_hash"],
                     record["previous_event_hash"], _canonical(record)),
                )
                self._connection.execute("COMMIT")
            except BaseException:
                self._connection.execute("ROLLBACK")
                raise
        except sqlite3.Error:
            self._events.pop()
            raise ProvenanceLedgerError("LEDGER_STORAGE_WRITE_FAILED") from None
        except BaseException:
            self._events.pop()
            raise
        return record

    def verify_storage(self) -> dict[str, Any]:
        """Audit: re-read the database and compare it with the in-memory chain."""
        stored = ProvenanceEventLedger(_stored_events(self._connection))
        history = stored.verify_history()
        return {**history, "matches_loaded_ledger": stored.head_hash == self.head_hash
                and history["event_count"] == len(self._events)}

    @classmethod
    def restore_from_jsonl(cls, path: str | Path, text: str) -> "SQLiteProvenanceLedger":
        """Rebuild a new database from a JSONL export after full validation."""
        validated = ProvenanceEventLedger.from_jsonl(text)
        target = Path(path)
        if target.exists() and target.stat().st_size:
            raise ProvenanceLedgerError("LEDGER_RESTORE_TARGET_NOT_EMPTY")
        connection = _connect(target)
        try:
            connection.execute("BEGIN IMMEDIATE")
            for event in validated.events:
                connection.execute(
                    "INSERT INTO provenance_events (sequence, event_id, event_hash, previous_event_hash, event_json)"
                    " VALUES (?, ?, ?, ?, ?)",
                    (event["sequence"], event["event_id"], event["event_hash"],
                     event["previous_event_hash"], _canonical(event)),
                )
            connection.execute("COMMIT")
        finally:
            connection.close()
        return cls(target)


def ledger_from_environment(environ: Mapping[str, str]) -> SQLiteProvenanceLedger | None:
    path = environ.get("SARA_PROVENANCE_LEDGER_PATH", "").strip()
    return SQLiteProvenanceLedger(path) if path else None
