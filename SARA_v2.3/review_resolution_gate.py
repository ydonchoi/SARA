"""Bounded human-review resolution gate for P17."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewResolution:
    verification_status: str
    resolution_status: str
    truthfulness_status: str


class ReviewResolutionGate:
    def evaluate(
        self,
        *,
        review_completed: bool,
        resolution: str,
    ) -> ReviewResolution:
        if not review_completed:
            return ReviewResolution("CONTRADICTED", "REVIEW_REQUIRED", "UNASSESSED")
        if resolution == "UPHOLD":
            return ReviewResolution("VERIFIED", "UPHELD", "UNASSESSED")
        if resolution == "REJECT":
            return ReviewResolution("UNVERIFIED", "REJECTED", "UNASSESSED")
        if resolution == "REVISE":
            return ReviewResolution("UNVERIFIED", "REVISION_REQUIRED", "UNASSESSED")
        raise ValueError("UNKNOWN_REVIEW_RESOLUTION")
