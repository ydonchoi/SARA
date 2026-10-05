from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from review_resolution_gate import ReviewResolutionGate


def test_unresolved_conflict_cannot_be_verified():
    result = ReviewResolutionGate().evaluate(
        review_completed=False,
        resolution="UPHOLD",
    )
    assert result.verification_status == "CONTRADICTED"
    assert result.resolution_status == "REVIEW_REQUIRED"


def test_human_uphold_can_restore_verification():
    result = ReviewResolutionGate().evaluate(
        review_completed=True,
        resolution="UPHOLD",
    )
    assert result.verification_status == "VERIFIED"
    assert result.resolution_status == "UPHELD"


def test_reject_and_revise_do_not_promote_verification():
    gate = ReviewResolutionGate()
    rejected = gate.evaluate(review_completed=True, resolution="REJECT")
    revised = gate.evaluate(review_completed=True, resolution="REVISE")
    assert rejected.verification_status == "UNVERIFIED"
    assert revised.verification_status == "UNVERIFIED"


def test_review_resolution_never_establishes_truthfulness():
    result = ReviewResolutionGate().evaluate(
        review_completed=True,
        resolution="UPHOLD",
    )
    assert result.truthfulness_status == "UNASSESSED"
