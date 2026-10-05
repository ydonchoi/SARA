"""Adapter boundary for operational evidence-flow observations.

This adapter converts an already-computed observation into a sink write.
It does not call verification, promotion, content access, or truthfulness
logic, and it cannot replace the verification result.
"""
from __future__ import annotations

from typing import Protocol

from evidence_flow_observation import EvidenceFlowObservation


class EvidenceFlowObservationRecorder(Protocol):
    def record(self, observation: EvidenceFlowObservation) -> None:
        ...


class EvidenceFlowObservationAdapter:
    def __init__(self, recorder: EvidenceFlowObservationRecorder) -> None:
        self._recorder = recorder

    def observe(
        self, observation: EvidenceFlowObservation
    ) -> EvidenceFlowObservation:
        self._recorder.record(observation)
        return observation
