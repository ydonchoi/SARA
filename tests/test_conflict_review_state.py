from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from conflict_review_state import ConflictReviewStateEvaluator


def test_conflict_requires_human_review():
    result = ConflictReviewStateEvaluator().evaluate(conflict_detected=True)
    assert result.status == "REVISION_REQUIRED"
    assert result.requires_human_review is True


def test_no_conflict_does_not_require_review():
    result = ConflictReviewStateEvaluator().evaluate(conflict_detected=False)
    assert result.status == "NO_CONFLICT"
    assert result.requires_human_review is False


def test_review_state_does_not_establish_truthfulness():
    result = ConflictReviewStateEvaluator().evaluate(conflict_detected=True)
    assert result.truthfulness_status == "UNASSESSED"
