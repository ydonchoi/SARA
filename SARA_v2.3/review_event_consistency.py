"""Validate consistency between P19 lineage and P20 review-event records."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewEventConsistency:
    consistent: bool
    status: str
    truthfulness_status: str

class ReviewEventConsistencyGate:
    def evaluate(self, *, lineage_accepted: bool, lineage_event_id: str | None,
                 lineage_claim_id: str | None, lineage_prior_status: str,
                 lineage_resolution: str | None, record_accepted: bool,
                 record_event_id: str | None, record_claim_id: str | None,
                 record_prior_status: str, record_resolution: str | None) -> ReviewEventConsistency:
        if not lineage_accepted or not record_accepted:
            return ReviewEventConsistency(False, "INVALID_UPSTREAM_RECORD", "UNASSESSED")
        if (lineage_event_id != record_event_id or lineage_claim_id != record_claim_id
                or lineage_prior_status != record_prior_status
                or lineage_resolution != record_resolution):
            return ReviewEventConsistency(False, "LINEAGE_RECORD_MISMATCH", "UNASSESSED")
        return ReviewEventConsistency(True, "CONSISTENT", "UNASSESSED")
