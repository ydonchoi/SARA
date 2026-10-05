from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from verification_boundary_audit import VerificationBoundaryAuditGate

def test_review_audit_context_stays_within_boundary():
    r=VerificationBoundaryAuditGate().evaluate(audit_context_consumed=True,verification_promotion_requested=False)
    assert r.allowed and r.status=="REVIEW_AUDIT_BOUNDARY_INTACT"
    assert r.truthfulness_status=="UNASSESSED"

def test_review_audit_cannot_promote_verification():
    r=VerificationBoundaryAuditGate().evaluate(audit_context_consumed=True,verification_promotion_requested=True)
    assert not r.allowed and r.status=="REVIEW_AUDIT_CANNOT_PROMOTE_VERIFICATION"

def test_missing_context_fails_closed():
    r=VerificationBoundaryAuditGate().evaluate(audit_context_consumed=False,verification_promotion_requested=False)
    assert not r.allowed and r.status=="NO_REVIEW_AUDIT_CONTEXT"
