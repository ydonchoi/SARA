from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from review_event_consistency import ReviewEventConsistencyGate

BASE=dict(lineage_accepted=True,lineage_event_id="review-1",lineage_claim_id="claim-1",lineage_prior_status="REVISION_REQUIRED",lineage_resolution="UPHOLD",record_accepted=True,record_event_id="review-1",record_claim_id="claim-1",record_prior_status="REVISION_REQUIRED",record_resolution="UPHOLD")

def test_matching_records_are_consistent():
    r=ReviewEventConsistencyGate().evaluate(**BASE)
    assert r.consistent and r.status=="CONSISTENT" and r.truthfulness_status=="UNASSESSED"

def test_mismatch_is_rejected():
    x=dict(BASE); x["record_claim_id"]="claim-2"
    r=ReviewEventConsistencyGate().evaluate(**x)
    assert not r.consistent and r.status=="LINEAGE_RECORD_MISMATCH"

def test_unaccepted_upstream_fails_closed():
    x=dict(BASE); x["lineage_accepted"]=False
    r=ReviewEventConsistencyGate().evaluate(**x)
    assert not r.consistent and r.status=="INVALID_UPSTREAM_RECORD"

def test_consistency_never_promotes_truthfulness():
    assert ReviewEventConsistencyGate().evaluate(**BASE).truthfulness_status=="UNASSESSED"
