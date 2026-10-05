"""Validate internal integrity of a P20 human-review event record (P22)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewEventIntegrity:
    valid: bool
    status: str
    truthfulness_status: str

class ReviewEventIntegrityGate:
    VALID_RESOLUTIONS = {"UPHOLD", "REJECT", "REVISE"}
    VALID_PRIOR_STATES = {"REVIEW_REQUIRED", "REVISION_REQUIRED"}

    def evaluate(self, *, accepted: bool, event_id: str | None, claim_id: str | None,
                 prior_review_status: str, resolution_status: str,
                 event_type: str | None) -> ReviewEventIntegrity:
        if not accepted:
            return ReviewEventIntegrity(False, "RECORD_NOT_ACCEPTED", "UNASSESSED")
        if not event_id or not claim_id or not event_type:
            return ReviewEventIntegrity(False, "MISSING_EVENT_FIELDS", "UNASSESSED")
        if prior_review_status not in self.VALID_PRIOR_STATES:
            return ReviewEventIntegrity(False, "INVALID_PRIOR_REVIEW_STATE", "UNASSESSED")
        if resolution_status not in self.VALID_RESOLUTIONS:
            return ReviewEventIntegrity(False, "INVALID_RESOLUTION", "UNASSESSED")
        if event_type != "HUMAN_REVIEW_RESOLUTION":
            return ReviewEventIntegrity(False, "INVALID_EVENT_TYPE", "UNASSESSED")
        return ReviewEventIntegrity(True, "VALID", "UNASSESSED")
