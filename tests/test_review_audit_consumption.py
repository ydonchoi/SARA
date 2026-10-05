from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from review_audit_consumption import ReviewAuditConsumptionGate

def test_complete_audit_can_be_consumed_as_context():
    r=ReviewAuditConsumptionGate().evaluate(audit_complete=True,audit_status="P18_P22_OPERATIONAL_CHAIN_COMPLETE",requested_action="HUMAN_REVIEW_CONTEXT")
    assert r.accepted and r.status=="CONSUMED_AS_OPERATIONAL_CONTEXT"
    assert r.truthfulness_status=="UNASSESSED"

def test_incomplete_audit_is_rejected():
    r=ReviewAuditConsumptionGate().evaluate(audit_complete=False,audit_status="P18_P22_OPERATIONAL_CHAIN_INCOMPLETE",requested_action="HUMAN_REVIEW_CONTEXT")
    assert not r.accepted and r.status=="AUDIT_INCOMPLETE"

def test_unsupported_consumption_fails_closed():
    r=ReviewAuditConsumptionGate().evaluate(audit_complete=True,audit_status="P18_P22_OPERATIONAL_CHAIN_COMPLETE",requested_action="VERIFICATION_PROMOTION")
    assert not r.accepted and r.status=="UNSUPPORTED_CONSUMPTION"

def test_consumption_never_promotes_truthfulness():
    r=ReviewAuditConsumptionGate().evaluate(audit_complete=True,audit_status="P18_P22_OPERATIONAL_CHAIN_COMPLETE",requested_action="AUDIT_RECORD")
    assert r.truthfulness_status=="UNASSESSED"
