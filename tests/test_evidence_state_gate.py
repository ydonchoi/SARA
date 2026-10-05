from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from evidence_state_gate import EvidenceStateGate


def test_strong_aligned_evidence_can_support_verification():
    result = EvidenceStateGate().decide(
        evidence_strength="STRONG",
        citation_fit="VERIFIED",
        source_exists=True,
    )
    assert result.verification_status == "VERIFIED"
    assert result.truthfulness_status == "UNASSESSED"


def test_strength_without_alignment_cannot_promote_verification():
    result = EvidenceStateGate().decide(
        evidence_strength="STRONG",
        citation_fit="UNVERIFIED",
        source_exists=True,
    )
    assert result.verification_status == "UNVERIFIED"
    assert result.truthfulness_status == "UNASSESSED"


def test_verification_never_implies_truthfulness():
    result = EvidenceStateGate().decide(
        evidence_strength="STRONG",
        citation_fit="VERIFIED",
        source_exists=True,
    )
    assert result.verification_status == "VERIFIED"
    assert result.truthfulness_status != "ESTABLISHED"
