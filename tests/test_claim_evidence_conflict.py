from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from claim_evidence_conflict import ClaimEvidenceConflictEvaluator


def test_mixed_verified_and_contradicted_evidence_is_conflict():
    result = ClaimEvidenceConflictEvaluator().evaluate(
        claim_id="CLAIM-1",
        evidence_verification_statuses=("VERIFIED", "CONTRADICTED"),
    )
    assert result.conflict_detected is True
    assert result.verification_status == "CONTRADICTED"


def test_only_verified_evidence_can_remain_verified():
    result = ClaimEvidenceConflictEvaluator().evaluate(
        claim_id="CLAIM-2",
        evidence_verification_statuses=("VERIFIED", "VERIFIED"),
    )
    assert result.verification_status == "VERIFIED"
    assert result.conflict_detected is False


def test_conflict_does_not_establish_truthfulness():
    result = ClaimEvidenceConflictEvaluator().evaluate(
        claim_id="CLAIM-1",
        evidence_verification_statuses=("VERIFIED", "CONTRADICTED"),
    )
    assert result.truthfulness_status == "UNASSESSED"
