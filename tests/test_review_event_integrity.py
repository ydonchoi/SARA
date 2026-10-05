from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from review_event_integrity import ReviewEventIntegrityGate

BASE=dict(accepted=True,event_id="review-1",claim_id="claim-1",prior_review_status="REVISION_REQUIRED",resolution_status="UPHOLD",event_type="HUMAN_REVIEW_RESOLUTION")

def test_valid_record_is_accepted_without_truthfulness():
    r=ReviewEventIntegrityGate().evaluate(**BASE)
    assert r.valid and r.status=="VALID" and r.truthfulness_status=="UNASSESSED"

def test_missing_field_fails_closed():
    x=dict(BASE); x["claim_id"]=None
    r=ReviewEventIntegrityGate().evaluate(**x)
    assert not r.valid and r.status=="MISSING_EVENT_FIELDS"

def test_invalid_state_fails_closed():
    x=dict(BASE); x["prior_review_status"]="VERIFIED"
    r=ReviewEventIntegrityGate().evaluate(**x)
    assert not r.valid and r.status=="INVALID_PRIOR_REVIEW_STATE"

def test_invalid_event_type_fails_closed():
    x=dict(BASE); x["event_type"]="VERIFICATION"
    r=ReviewEventIntegrityGate().evaluate(**x)
    assert not r.valid and r.status=="INVALID_EVENT_TYPE"

def test_integrity_never_promotes_truthfulness():
    assert ReviewEventIntegrityGate().evaluate(**BASE).truthfulness_status=="UNASSESSED"
