from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from review_resolution_provenance import ReviewResolutionProvenanceGate


def test_uncompleted_review_is_not_accepted():
    result = ReviewResolutionProvenanceGate().evaluate(
        review_completed=False,
        review_event_id=None,
        resolution=None,
    )
    assert not result.accepted
    assert result.resolution_status == "REVIEW_REQUIRED"
    assert result.truthfulness_status == "UNASSESSED"


def test_missing_review_event_id_is_rejected():
    result = ReviewResolutionProvenanceGate().evaluate(
        review_completed=True,
        review_event_id=None,
        resolution="UPHOLD",
    )
    assert not result.accepted
    assert result.resolution_status == "INVALID_REVIEW_PROVENANCE"


def test_unknown_resolution_fails_closed():
    result = ReviewResolutionProvenanceGate().evaluate(
        review_completed=True,
        review_event_id="review-1",
        resolution="UNKNOWN",
    )
    assert not result.accepted
    assert result.resolution_status == "INVALID_REVIEW_RESOLUTION"


def test_valid_review_resolution_is_accepted_without_truthfulness_promotion():
    result = ReviewResolutionProvenanceGate().evaluate(
        review_completed=True,
        review_event_id="review-1",
        resolution="UPHOLD",
    )
    assert result.accepted
    assert result.review_event_id == "review-1"
    assert result.resolution_status == "UPHOLD"
    assert result.truthfulness_status == "UNASSESSED"
