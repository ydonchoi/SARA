"""Create an auditable review-event record from P18/P19 inputs (P20)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewEventRecord:
    accepted: bool
    event_id: str | None
    claim_id: str | None
    prior_review_status: str
    resolution_status: str
    truthfulness_status: str
    event_type: str | None

class ReviewEventRecordGate:
    VALID_RESOLUTIONS = {"UPHOLD", "REJECT", "REVISE"}
    VALID_PRIOR_STATES = {"REVIEW_REQUIRED", "REVISION_REQUIRED"}

    def evaluate(self, *, review_completed: bool, review_event_id: str | None,
                 claim_id: str | None, prior_review_status: str,
                 resolution: str | None) -> ReviewEventRecord:
        if not review_completed:
            return ReviewEventRecord(False, review_event_id, claim_id, prior_review_status, "REVIEW_REQUIRED", "UNASSESSED", None)
        if not review_event_id or not claim_id:
            return ReviewEventRecord(False, review_event_id, claim_id, prior_review_status, "INVALID_REVIEW_EVENT", "UNASSESSED", None)
        if prior_review_status not in self.VALID_PRIOR_STATES:
            return ReviewEventRecord(False, review_event_id, claim_id, prior_review_status, "INVALID_PRIOR_REVIEW_STATE", "UNASSESSED", None)
        if resolution not in self.VALID_RESOLUTIONS:
            return ReviewEventRecord(False, review_event_id, claim_id, prior_review_status, "INVALID_REVIEW_RESOLUTION", "UNASSESSED", None)
        return ReviewEventRecord(True, review_event_id, claim_id, prior_review_status, resolution, "UNASSESSED", "HUMAN_REVIEW_RESOLUTION")
