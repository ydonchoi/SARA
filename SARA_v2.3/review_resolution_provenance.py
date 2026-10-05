"""Audit provenance gate for human-review resolution events (P18).

A review resolution is operational provenance. It is not evidence of claim
truth and cannot establish truthfulness by itself.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewResolutionProvenance:
    accepted: bool
    review_event_id: str | None
    resolution_status: str
    truthfulness_status: str


class ReviewResolutionProvenanceGate:
    def evaluate(
        self,
        *,
        review_completed: bool,
        review_event_id: str | None,
        resolution: str | None,
    ) -> ReviewResolutionProvenance:
        if not review_completed:
            return ReviewResolutionProvenance(
                False, None, "REVIEW_REQUIRED", "UNASSESSED"
            )

        if not review_event_id:
            return ReviewResolutionProvenance(
                False, None, "INVALID_REVIEW_PROVENANCE", "UNASSESSED"
            )

        if resolution not in {"UPHOLD", "REJECT", "REVISE"}:
            return ReviewResolutionProvenance(
                False, review_event_id, "INVALID_REVIEW_RESOLUTION", "UNASSESSED"
            )

        return ReviewResolutionProvenance(
            True, review_event_id, resolution, "UNASSESSED"
        )
