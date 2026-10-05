"""Bounded review-state transition for claim evidence conflicts (P16)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConflictReviewState:
    status: str
    requires_human_review: bool
    truthfulness_status: str


class ConflictReviewStateEvaluator:
    def evaluate(self, *, conflict_detected: bool) -> ConflictReviewState:
        if conflict_detected:
            return ConflictReviewState(
                status="REVISION_REQUIRED",
                requires_human_review=True,
                truthfulness_status="UNASSESSED",
            )
        return ConflictReviewState(
            status="NO_CONFLICT",
            requires_human_review=False,
            truthfulness_status="UNASSESSED",
        )
