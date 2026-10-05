"""Bounded operational sink for evidence-flow observations.

The sink stores diagnostics only. It has no authority over verification,
promotion, truthfulness, or evidence state.
"""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from evidence_flow_observation import EvidenceFlowObservation


class EvidenceFlowObservationSink:
    def __init__(self, *, max_records: int = 1000) -> None:
        if max_records <= 0:
            raise ValueError("OBSERVATION_SINK_CAPACITY_INVALID")
        self._max_records = max_records
        self._records: list[EvidenceFlowObservation] = []

    def record(self, observation: EvidenceFlowObservation) -> None:
        if len(self._records) >= self._max_records:
            raise OverflowError("OBSERVATION_SINK_CAPACITY_EXCEEDED")
        self._records.append(observation)

    def records(self) -> tuple[EvidenceFlowObservation, ...]:
        return tuple(self._records)

    def summary(self) -> dict[str, Any]:
        records: Iterable[EvidenceFlowObservation] = self._records
        total = len(self._records)
        verified = sum(r.verification_status == "VERIFIED" for r in records)
        recoverable = sum(r.recoverability == "RECOVERABLE" for r in self._records)
        return {
            "total": total,
            "verified": verified,
            "unverified": total - verified,
            "recoverable": recoverable,
            "truthfulness_status": "UNASSESSED",
        }
