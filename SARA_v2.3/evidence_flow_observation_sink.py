"""Bounded operational sink for evidence-flow observations.

The sink stores diagnostics only. It has no authority over verification,
promotion, truthfulness, or evidence state.
"""
from __future__ import annotations

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
        total = len(self._records)
        verified = sum(r.verification_status == "VERIFIED" for r in self._records)
        recovery_candidates = sum(
            r.recovery_candidate for r in self._records
        )
        return {
            "total": total,
            "verified": verified,
            "unverified": total - verified,
            "recovery_candidates": recovery_candidates,
        }

    def telemetry_summary(self) -> dict[str, Any]:
        """Return bounded operational metrics without changing observation state."""
        total = len(self._records)
        verified = sum(r.verification_status == "VERIFIED" for r in self._records)
        unverified = total - verified
        recovery_candidates = sum(
            r.recovery_candidate for r in self._records
        )
        provider_completed = sum(
            r.provider_status == "SUCCEEDED" for r in self._records
        )
        content_retrieved = sum(
            r.content_access_status == "RETRIEVED" for r in self._records
        )
        content_scope_resolved = sum(
            r.content_scope != "UNKNOWN" for r in self._records
        )
        evidence_identity_matched = sum(
            r.evidence_identity_status == "MATCHED" for r in self._records
        )

        gate_finding_codes = {
            "P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",
            "P39_CONTENT_SCOPE_REQUIRES_A2_PIPELINE",
            "P37_SUBSTANTIVE_CONTENT_REQUIRES_RETRIEVED_PAYLOAD",
            "P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE",
            "P38_EVIDENCE_IDENTITY_MISMATCH",
        }
        a2_rejection_by_finding = {
            code: sum(code in r.finding_codes for r in self._records)
            for code in sorted(gate_finding_codes)
        }

        recovery_reverified = 0
        seen_recovery_candidate: set[tuple[str, str]] = set()
        for record in self._records:
            key = (record.request_id, record.claim_id)
            if record.recovery_candidate and record.verification_status == "UNVERIFIED":
                seen_recovery_candidate.add(key)
            elif (
                record.verification_status == "VERIFIED"
                and key in seen_recovery_candidate
            ):
                recovery_reverified += 1

        latencies = [
            r.latency_ms for r in self._records if r.latency_ms is not None
        ]

        return {
            "total": total,
            "verified": verified,
            "unverified": unverified,
            "recovery_candidates": recovery_candidates,
            "provider_completion_rate": (
                provider_completed / total if total else 0.0
            ),
            "content_retrieval_success_rate": (
                content_retrieved / total if total else 0.0
            ),
            "content_scope_resolution_rate": (
                content_scope_resolved / total if total else 0.0
            ),
            "evidence_identity_match_rate": (
                evidence_identity_matched / total if total else 0.0
            ),
            "a2_rejection_rate_by_finding": {
                code: count / total if total else 0.0
                for code, count in a2_rejection_by_finding.items()
            },
            "recoverable_unverified": recovery_candidates,
            "non_recoverable_unverified": unverified - recovery_candidates,
            "reverification_success_after_recovery": recovery_reverified,
            "latency_ms": {
                "count": len(latencies),
                "min": min(latencies) if latencies else None,
                "max": max(latencies) if latencies else None,
                "average": (
                    sum(latencies) / len(latencies) if latencies else None
                ),
            },
        }
