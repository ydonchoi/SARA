from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from evidence_strength import EvidenceStrengthEvaluator


def test_full_alignment_is_strong_review_metadata():
    result = EvidenceStrengthEvaluator().evaluate(
        citation_fit="VERIFIED",
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access="RETRIEVED",
    )
    assert result.strength == "STRONG"


def test_missing_content_access_is_not_strong():
    result = EvidenceStrengthEvaluator().evaluate(
        citation_fit="VERIFIED",
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access="NOT_COMPLETED",
    )
    assert result.strength == "MODERATE"


def test_strength_is_not_truthfulness():
    result = EvidenceStrengthEvaluator().evaluate(
        citation_fit="VERIFIED",
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access="RETRIEVED",
    )
    assert result.strength == "STRONG"
    assert not hasattr(result, "truthfulness_status")
