from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from contradiction_firewall import ContradictionFirewall


def test_contradiction_blocks_verification_promotion():
    result = ContradictionFirewall().evaluate(
        claim_bound=True,
        citation_fit="VERIFIED",
        evidence_strength="STRONG",
        contradiction_detected=True,
    )
    assert result.verification_status == "CONTRADICTED"
    assert result.contradiction_detected is True


def test_no_contradiction_preserves_bounded_promotion():
    result = ContradictionFirewall().evaluate(
        claim_bound=True,
        citation_fit="VERIFIED",
        evidence_strength="STRONG",
        contradiction_detected=False,
    )
    assert result.verification_status == "VERIFIED"


def test_contradiction_does_not_establish_truthfulness():
    result = ContradictionFirewall().evaluate(
        claim_bound=True,
        citation_fit="VERIFIED",
        evidence_strength="STRONG",
        contradiction_detected=True,
    )
    assert result.truthfulness_status == "UNASSESSED"
