from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from review_resolution_gate import ReviewResolutionGate


def test_unresolved_conflict_requires_review():
    result = ReviewResolutionGate().evaluate(
        review_completed=False,
        resolution="UPHOLD",
    )
    assert result.verification_status == "CONTRADICTED"
    assert result.resolution_status == "REVIEW_REQUIRED"
    assert result.truthfulness_status == "UNASSESSED"


def test_human_uphold_does_not_promote_verification():
    result = ReviewResolutionGate().evaluate(
        review_completed=True,
        resolution="UPHOLD",
    )
    assert result.verification_status == "UNVERIFIED"
    assert result.resolution_status == "UPHELD"
    assert result.truthfulness_status == "UNASSESSED"


def test_reject_and_revise_remain_unverified():
    gate = ReviewResolutionGate()
    rejected = gate.evaluate(review_completed=True, resolution="REJECT")
    revised = gate.evaluate(review_completed=True, resolution="REVISE")
    assert rejected.verification_status == "UNVERIFIED"
    assert revised.verification_status == "UNVERIFIED"


def test_unknown_resolution_fails_closed():
    gate = ReviewResolutionGate()
    try:
        gate.evaluate(review_completed=True, resolution="UNKNOWN")
    except ValueError as exc:
        assert str(exc) == "UNKNOWN_REVIEW_RESOLUTION"
    else:
        raise AssertionError("unknown resolution must fail closed")
