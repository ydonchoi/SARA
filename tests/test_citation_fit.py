from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from citation_fit import CitationFitEvaluator


def test_citation_fit_matches_claim_in_content():
    result = CitationFitEvaluator().evaluate(
        "CLAIM-1",
        "The intervention improved retention",
        "Results: The intervention improved retention in the observed cohort.",
    )
    assert result.status == "VERIFIED"
    assert result.matched is True
    assert result.findings == ("CITATION_FIT_COMPLETED",)


def test_citation_fit_rejects_unmatched_claim():
    result = CitationFitEvaluator().evaluate(
        "CLAIM-2",
        "The intervention caused a 50 percent increase",
        "Results: The intervention improved retention.",
    )
    assert result.status == "UNVERIFIED"
    assert result.matched is False


def test_citation_fit_never_treats_empty_content_as_verified():
    result = CitationFitEvaluator().evaluate(
        "CLAIM-3",
        "The intervention improved retention",
        "",
    )
    assert result.status == "UNVERIFIED"
    assert result.matched is False
