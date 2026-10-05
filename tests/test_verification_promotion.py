from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from verification_promotion import VerificationPromotionGate


def test_aligned_evidence_can_promote_verification():
    result = VerificationPromotionGate().evaluate(
        claim_bound=True,
        citation_fit="VERIFIED",
        evidence_strength="STRONG",
    )
    assert result.promoted is True
    assert result.verification_status == "VERIFIED"
    assert result.truthfulness_status == "UNASSESSED"


def test_unbound_evidence_cannot_promote():
    result = VerificationPromotionGate().evaluate(
        claim_bound=False,
        citation_fit="VERIFIED",
        evidence_strength="STRONG",
    )
    assert result.promoted is False
    assert result.verification_status == "UNVERIFIED"


def test_fit_without_sufficient_strength_cannot_promote():
    result = VerificationPromotionGate().evaluate(
        claim_bound=True,
        citation_fit="VERIFIED",
        evidence_strength="WEAK",
    )
    assert result.promoted is False


def test_verification_does_not_establish_truthfulness():
    result = VerificationPromotionGate().evaluate(
        claim_bound=True,
        citation_fit="VERIFIED",
        evidence_strength="STRONG",
    )
    assert result.truthfulness_status != "ESTABLISHED"
