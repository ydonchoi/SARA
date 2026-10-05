from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from claim_evidence_binding import ClaimEvidenceBindingEvaluator


def test_explicit_claim_binding_is_required():
    result = ClaimEvidenceBindingEvaluator().evaluate(
        claim_id="CLAIM-1",
        evidence_id="EVIDENCE-1",
        supports_claim_ids=("CLAIM-1",),
    )
    assert result.bound is True


def test_unrelated_evidence_cannot_bind():
    result = ClaimEvidenceBindingEvaluator().evaluate(
        claim_id="CLAIM-1",
        evidence_id="EVIDENCE-2",
        supports_claim_ids=("CLAIM-2",),
    )
    assert result.bound is False


def test_binding_is_not_truthfulness():
    result = ClaimEvidenceBindingEvaluator().evaluate(
        claim_id="CLAIM-1",
        evidence_id="EVIDENCE-1",
        supports_claim_ids=("CLAIM-1",),
    )
    assert result.bound is True
    assert not hasattr(result, "truthfulness_status")
