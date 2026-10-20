from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from external_evidence import ExternalEvidenceError, collect_external_evidence


CLAIM = {"id": "C-1", "text": "The policy caused the decline.", "scope": {"time_range": "2024"}}
CONTEXT = {"turn_id": "T-1", "input_revision_digest": "a" * 64}


def test_external_search_collects_candidates_without_verifying_claim():
    captured = {}

    def search(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return [
            {"url": "https://example.org/paper", "title": "Study", "snippet": "The study reports an association."},
            {"url": "https://example.org/paper", "title": "Study duplicate", "snippet": "The study reports an association."},
        ]

    result = collect_external_evidence(
        search, claim=CLAIM, context=CONTEXT, timeout_seconds=2
    )
    assert captured["request"]["claim_id"] == "C-1"
    assert captured["timeout"] == 2
    assert result["status"] == "COLLECTED"
    assert result["result_count"] == 1
    assert result["results"][0]["verification_status"] == "UNASSESSED"
    assert result["results"][0]["is_evidence"] is False
    assert result["claim_truth_assessed"] is False


def test_empty_search_result_is_not_a_false_claim_verdict():
    result = collect_external_evidence(
        lambda *_: [], claim=CLAIM, context=CONTEXT, timeout_seconds=1
    )
    assert result["status"] == "NO_RESULTS"
    assert result["result_count"] == 0
    assert result["claim_truth_assessed"] is False


@pytest.mark.parametrize(
    "raw, expected",
    [
        ({"results": []}, "EXTERNAL_SEARCH_RESULTS_MUST_BE_LIST"),
        ([{"title": "No URL", "snippet": "Text"}], "EXTERNAL_SEARCH_RESULT_URL_REQUIRED"),
        ([{"url": "https://example.org"}], "EXTERNAL_SEARCH_RESULT_TEXT_REQUIRED"),
    ],
)
def test_malformed_search_results_fail_closed(raw, expected):
    with pytest.raises(ExternalEvidenceError, match=expected):
        collect_external_evidence(
            lambda *_: raw, claim=CLAIM, context=CONTEXT, timeout_seconds=1
        )


def test_search_timeout_is_explicit():
    def search(*_):
        raise TimeoutError()

    with pytest.raises(ExternalEvidenceError, match="EXTERNAL_SEARCH_TIMEOUT"):
        collect_external_evidence(
            search, claim=CLAIM, context=CONTEXT, timeout_seconds=1
        )


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://example.org/file",
        "https:///missing-host",
        "https://user:password@example.org/private",
        "not a URL",
    ],
)
def test_non_http_or_credential_bearing_urls_fail_closed(url):
    with pytest.raises(ExternalEvidenceError, match="EXTERNAL_SEARCH_RESULT_URL_MUST_BE_HTTP"):
        collect_external_evidence(
            lambda *_: [{"url": url, "title": "Source", "snippet": "Candidate text"}],
            claim=CLAIM,
            context=CONTEXT,
            timeout_seconds=1,
        )


@pytest.mark.parametrize("url", ["https://example.org/source", "http://example.org/source"])
def test_absolute_http_urls_are_accepted_as_unverified_candidates(url):
    result = collect_external_evidence(
        lambda *_: [{"url": url, "title": "Source", "snippet": "Candidate text"}],
        claim=CLAIM,
        context=CONTEXT,
        timeout_seconds=1,
    )
    assert result["status"] == "COLLECTED"
    assert result["results"][0]["url"] == url
    assert result["results"][0]["verification_status"] == "UNASSESSED"
