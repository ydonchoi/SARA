from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from review_event_record import ReviewEventRecordGate

def test_valid_review_becomes_auditable_event_record_without_truthfulness():
    r = ReviewEventRecordGate().evaluate(review_completed=True, review_event_id="review-001", claim_id="claim-001", prior_review_status="REVISION_REQUIRED", resolution="UPHOLD")
    assert r.accepted and r.event_id == "review-001" and r.claim_id == "claim-001"
    assert r.event_type == "HUMAN_REVIEW_RESOLUTION"
    assert r.resolution_status == "UPHOLD" and r.truthfulness_status == "UNASSESSED"

def test_missing_identifiers_reject_event_record():
    r = ReviewEventRecordGate().evaluate(review_completed=True, review_event_id=None, claim_id="claim-001", prior_review_status="REVISION_REQUIRED", resolution="UPHOLD")
    assert not r.accepted and r.resolution_status == "INVALID_REVIEW_EVENT"

def test_invalid_prior_state_rejects_event():
    r = ReviewEventRecordGate().evaluate(review_completed=True, review_event_id="review-001", claim_id="claim-001", prior_review_status="VERIFIED", resolution="UPHOLD")
    assert not r.accepted and r.resolution_status == "INVALID_PRIOR_REVIEW_STATE"

def test_unknown_resolution_fails_closed():
    r = ReviewEventRecordGate().evaluate(review_completed=True, review_event_id="review-001", claim_id="claim-001", prior_review_status="REVISION_REQUIRED", resolution="UNKNOWN")
    assert not r.accepted and r.resolution_status == "INVALID_REVIEW_RESOLUTION"

def test_incomplete_review_is_not_recorded():
    r = ReviewEventRecordGate().evaluate(review_completed=False, review_event_id="review-001", claim_id="claim-001", prior_review_status="REVISION_REQUIRED", resolution="UPHOLD")
    assert not r.accepted and r.event_type is None
