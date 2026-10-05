"""Bind human-review resolution provenance to a claim/state transition (P19).

This gate validates operational lineage only. It never promotes verification
or establishes truthfulness.
"""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewResolutionLineage:
    accepted: bool
    review_event_id: str | None
    claim_id: str | None
    prior_review_status: str
    resolution_status: str
    truthfulness_status: str

class ReviewResolutionLineageGate:
    VALID_RESOLUTIONS = {"UPHOLD", "REJECT", "REVISE"}
    VALID_PRIOR_STATES = {"REVIEW_REQUIRED", "REVISION_REQUIRED"}

    def evaluate(self, *, review_completed: bool, review_event_id: str | None,
                 claim_id: str | None, prior_review_status: str,
                 resolution: str | None) -> ReviewResolutionLineage:
        if not review_completed:
            return ReviewResolutionLineage(False, review_event_id, claim_id,
                                           prior_review_status, "REVIEW_REQUIRED",
                                           "UNASSESSED")
        if not review_event_id or not claim_id:
            return ReviewResolutionLineage(False, review_event_id, claim_id,
                                           prior_review_status, "INVALID_REVIEW_LINEAGE",
                                           "UNASSESSED")
        if prior_review_status not in self.VALID_PRIOR_STATES:
            return ReviewResolutionLineage(False, review_event_id, claim_id,
                                           prior_review_status, "INVALID_PRIOR_REVIEW_STATE",
                                           "UNASSESSED")
        if resolution not in self.VALID_RESOLUTIONS:
            return ReviewResolutionLineage(False, review_event_id, claim_id,
                                           prior_review_status, "INVALID_REVIEW_RESOLUTION",
                                           "UNASSESSED")
        return ReviewResolutionLineage(True, review_event_id, claim_id,
                                       prior_review_status, resolution,
                                       "UNASSESSED")
