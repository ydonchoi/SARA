from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from review_audit_summary import ReviewAuditSummaryBuilder

def test_complete_operational_chain_is_reported_without_truthfulness():
    r=ReviewAuditSummaryBuilder().build(provenance_ok=True,lineage_ok=True,record_ok=True,consistency_ok=True,integrity_ok=True)
    assert r.complete and r.status=="P18_P22_OPERATIONAL_CHAIN_COMPLETE"
    assert r.truthfulness_status=="UNASSESSED"

def test_incomplete_chain_is_reported():
    r=ReviewAuditSummaryBuilder().build(provenance_ok=True,lineage_ok=True,record_ok=False,consistency_ok=True,integrity_ok=True)
    assert not r.complete and r.status=="P18_P22_OPERATIONAL_CHAIN_INCOMPLETE"
