from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from citation_fit import CitationFitEvaluator


def test_citation_fit_does_not_establish_truthfulness():
    result = CitationFitEvaluator().evaluate(
        "CLAIM-TRUTH-1",
        "The intervention improved retention",
        "The intervention improved retention.",
    )
    assert result.status == "VERIFIED"
    # Citation fit is only a scoped compatibility result.
    assert not hasattr(result, "truthfulness_status")


def test_unmatched_content_cannot_be_promoted_to_fit():
    result = CitationFitEvaluator().evaluate(
        "CLAIM-NO-FIT",
        "The intervention caused harm",
        "The intervention improved retention.",
    )
    assert result.status == "UNVERIFIED"
    assert result.matched is False
