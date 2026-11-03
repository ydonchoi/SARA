"""Local release-gate contracts (G3, G4, G5, G7 in docs/v3-promotion-status.md)."""
from __future__ import annotations

import json

import pytest

from SARA_v3.contracts import create_assessment_envelope, normalize_evidence, validate_relation_result
from SARA_v3.mcp_adapter import MCPAdapterError, MCPSourceAdapter
from SARA_v3.provenance import ProvenanceEventLedger
from SARA_v3.verification import verify_claim_from_sources

CLAIM_TEXT = "The policy reduced cases by 20 percent."
SECRET = "sk-test-secret-value"


def source(*, access="FULL_TEXT", domain="official.example", content=CLAIM_TEXT, snippet=CLAIM_TEXT,
           evidence_id="E1", path="study"):
    return {
        "evidence_id": evidence_id,
        "url": f"https://{domain}/{path}",
        "title": "Study",
        "access_level": access,
        "content": content if access == "FULL_TEXT" else "",
        "snippet": snippet if access != "FULL_TEXT" else "",
        "source_type": "TEST_SOURCE",
        "provenance": {"provider": "test"},
    }


def relation(evidence, kind="SUPPORTS", span=CLAIM_TEXT):
    return {
        "evidence_id": evidence["evidence_id"],
        "relation": kind,
        "rationale": "The quoted source span directly addresses the claim.",
        "support_spans": [span] if kind in {"SUPPORTS", "CHALLENGES", "MIXED"} else [],
    }


class Search:
    def __init__(self, results):
        self.results = results

    def search(self, _query, *, count):
        return list(self.results)


class Fetcher:
    """Host-trusted fetch adapter keyed by URL."""
    def __init__(self, *items):
        self.by_url = {item["url"]: item for item in items}

    def search(self, _query):
        return []

    def fetch(self, url):
        return dict(self.by_url[url])


def claim(text=CLAIM_TEXT, **extra):
    return {"claim": {"id": "C1", "text": text, **extra}}


def envelope_for(evidence_items, relations, trusted=frozenset({"official.example"})):
    evidence = [normalize_evidence(item, fallback_id=item["evidence_id"]) for item in evidence_items]
    by_id = {item["evidence_id"]: item for item in evidence}
    validated = [validate_relation_result(r, evidence=by_id[r["evidence_id"]]) for r in relations]
    return create_assessment_envelope(claim=claim()["claim"], evidence=evidence, relations=validated,
                                      trusted_source_domains=set(trusted))


# G3: every non-full-text access level stays UNVERIFIED, even with a trusted SUPPORTS relation.

@pytest.mark.parametrize("access", ["SEARCH_SNIPPET", "METADATA", "ABSTRACT"])
def test_non_full_text_access_levels_cannot_verify(access):
    item = source(access=access)
    result = envelope_for([item], [relation(item)])
    assert result["verification_status"] == "UNVERIFIED"
    assert "FULL_TEXT_NOT_ACCESSED" in result["uncertainty"]
    assert result["evidence_access_levels"] == {"E1": access}


def test_unavailable_source_cannot_verify():
    item = source(access="UNAVAILABLE", snippet="")
    result = envelope_for([item], [relation(item, kind="INSUFFICIENT")])
    assert result["verification_status"] == "UNVERIFIED"
    assert "FULL_TEXT_NOT_ACCESSED" in result["uncertainty"]


def test_empty_search_reports_no_evidence_retrieved():
    result = verify_claim_from_sources(
        claim(), search_provider=Search([]), mcp_source=None,
        relation_assessor=lambda c, item, t: relation(item), trusted_source_domains={"official.example"},
    )
    assert result["status"] == "SUCCEEDED"
    assert result["verification_status"] == "UNVERIFIED"
    assert "NO_SOURCE_EVIDENCE_RETRIEVED" in result["findings"]


def test_mcp_fetch_without_full_text_scope_is_abstract_and_does_not_verify():
    hit = source(access="SEARCH_SNIPPET")
    adapter = MCPSourceAdapter(
        lambda _tool, args: {"structuredContent": {"url": args["url"], "content": CLAIM_TEXT}},
        fetch_tool="read", allowed_tools={"read"}, fetch_allowed_domains={"official.example"},
    )
    result = verify_claim_from_sources(
        claim(), search_provider=Search([hit]), mcp_source=adapter,
        relation_assessor=lambda c, item, t: relation(item), trusted_source_domains={"official.example"},
    )
    assert result["evidence"][0]["access_level"] == "ABSTRACT"
    assert result["verification_status"] == "UNVERIFIED"
    assert "FULL_TEXT_NOT_ACCESSED" in result["findings"]


# G4: retrieval, literal fit, semantic relation, SARA proposal and reviewer commit stay separate.

@pytest.mark.parametrize("domain, trusted, kind, expected", [
    ("official.example", {"official.example"}, "SUPPORTS", "VERIFIED"),
    ("sub.official.example", {"official.example"}, "SUPPORTS", "VERIFIED"),
    ("other.example", {"official.example"}, "SUPPORTS", "PARTIALLY_VERIFIED"),
    ("official.example", set(), "SUPPORTS", "PARTIALLY_VERIFIED"),
    ("official.example", {"official.example"}, "CHALLENGES", "CONTRADICTED"),
    ("official.example", {"official.example"}, "MIXED", "PARTIALLY_VERIFIED"),
    ("official.example", {"official.example"}, "IRRELEVANT", "UNVERIFIED"),
    ("official.example", {"official.example"}, "INSUFFICIENT", "UNVERIFIED"),
])
def test_full_text_status_transitions(domain, trusted, kind, expected):
    item = source(domain=domain)
    result = envelope_for([item], [relation(item, kind=kind)], trusted=trusted)
    assert result["verification_status"] == expected
    assert result["workflow_status"] == "PROPOSED"
    assert result["truthfulness_status"] == "UNASSESSED"


def test_retrieval_and_literal_match_without_relation_assessor_do_not_verify():
    item = source()
    result = verify_claim_from_sources(
        claim(), search_provider=Search([item]), mcp_source=Fetcher(item),
        relation_assessor=None, trusted_source_domains={"official.example"},
    )
    assert result["evidence"][0]["access_level"] == "FULL_TEXT"
    assert result["assessment"]["literal_citation_fit_signals"][0]["status"] == "LITERAL_MATCH"
    assert result["verification_status"] == "UNVERIFIED"
    assert "SOURCE_RELATION_ASSESSOR_NOT_CONFIGURED" in result["findings"]


def test_proposal_recording_never_commits_status():
    item = source()
    ledger = ProvenanceEventLedger()
    result = verify_claim_from_sources(
        claim(), search_provider=Search([item]), mcp_source=Fetcher(item),
        relation_assessor=lambda c, ev, t: relation(ev), trusted_source_domains={"official.example"},
        ledger=ledger,
    )
    assert result["verification_status"] == "VERIFIED"
    assert result["provenance"]["commit_status"] == "NOT_COMMITTED"
    assert {event["event_type"] for event in ledger.events} == {
        "CLAIM_REVISION_REGISTERED", "VERIFICATION_RESULT_PROPOSED",
    }


# G5: MCP malformed responses, timeouts and secret redaction.

@pytest.mark.parametrize("response, code", [
    (["not", "a", "mapping"], "MCP_RESULT_MUST_BE_MAPPING"),
    ({"isError": True, "content": []}, "MCP_TOOL_CALL_FAILED"),
    ({"content": [{"type": "text", "text": "not json"}]}, "MCP_STRUCTURED_RESULT_REQUIRED"),
    ({"structuredContent": {"results": "nope"}}, "MCP_SEARCH_RESULTS_REQUIRED"),
])
def test_mcp_malformed_search_response_is_rejected(response, code):
    adapter = MCPSourceAdapter(lambda *_: response, search_tool="find", allowed_tools={"find"})
    with pytest.raises(MCPAdapterError, match=code):
        adapter.search("query")


@pytest.mark.parametrize("response, code", [
    ({"structuredContent": {"url": "https://official.example/other", "content": "x"}}, "MCP_FETCH_URL_MISMATCH"),
    ({"structuredContent": {"url": "https://official.example/study", "content": "  "}}, "MCP_FETCH_CONTENT_REQUIRED"),
])
def test_mcp_malformed_fetch_response_is_rejected(response, code):
    adapter = MCPSourceAdapter(lambda *_: response, fetch_tool="read", allowed_tools={"read"},
                               fetch_allowed_domains={"official.example"})
    with pytest.raises(MCPAdapterError, match=code):
        adapter.fetch("https://official.example/study")


@pytest.mark.parametrize("url", [
    "http://official.example/study",
    f"https://user:{SECRET}@official.example/study",
])
def test_mcp_fetch_rejects_plain_http_and_credential_urls(url):
    adapter = MCPSourceAdapter(lambda *_: pytest.fail("tool must not be called"), fetch_tool="read",
                               allowed_tools={"read"}, fetch_allowed_domains={"official.example"})
    with pytest.raises(MCPAdapterError, match="MCP_FETCH_URL_OUTSIDE_DOMAIN_ALLOWLIST"):
        adapter.fetch(url)


def test_mcp_timeouts_fail_closed_without_leaking_exception_text():
    def call_tool(_tool, _args):
        raise TimeoutError(f"https://mcp.internal/read?api_key={SECRET}")

    adapter = MCPSourceAdapter(call_tool, search_tool="find", fetch_tool="read", allowed_tools={"find", "read"},
                               fetch_allowed_domains={"official.example"})
    result = verify_claim_from_sources(
        claim(), search_provider=Search([source(access="SEARCH_SNIPPET")]), mcp_source=adapter,
        relation_assessor=lambda c, item, t: relation(item), trusted_source_domains={"official.example"},
    )
    assert result["verification_status"] == "UNVERIFIED"
    assert "MCP_SEARCH_FAILED" in result["findings"]
    assert "MCP_FETCH_FAILED" in result["findings"]
    assert SECRET not in json.dumps(result, default=str)


def test_relation_assessor_error_text_is_not_reflected():
    item = source()

    def assessor(*_args):
        raise RuntimeError(f"provider said Authorization: Bearer {SECRET}")

    result = verify_claim_from_sources(
        claim(), search_provider=Search([item]), mcp_source=Fetcher(item),
        relation_assessor=assessor, trusted_source_domains={"official.example"},
    )
    assert "SOURCE_RELATION_ASSESSMENT_FAILED" in result["findings"]
    assert SECRET not in json.dumps(result, default=str)


# G7: conflict, stale revision and partial failure fail closed.

def test_trusted_support_and_challenge_conflict_is_not_verified():
    support = source(evidence_id="E1", path="a")
    challenge = source(evidence_id="E2", path="b", content="The policy did not reduce cases.")
    relations = {"E1": relation(support), "E2": relation(challenge, kind="CHALLENGES",
                                                        span="The policy did not reduce cases.")}
    result = verify_claim_from_sources(
        claim(), search_provider=Search([support, challenge]), mcp_source=Fetcher(support, challenge),
        relation_assessor=lambda c, item, t: relations[item["evidence_id"]],
        trusted_source_domains={"official.example"},
    )
    assert result["verification_status"] == "PARTIALLY_VERIFIED"
    assert "CONFLICTING_OR_MIXED_SOURCE_EVIDENCE" in result["findings"]
    assert result["assessment"]["conflict_assessment"]["automatic_majority_resolution"] is False


def test_stale_revision_id_with_changed_text_is_not_recorded_as_proposal():
    item = source()
    ledger = ProvenanceEventLedger()
    kwargs = dict(search_provider=Search([item]), mcp_source=Fetcher(item),
                  relation_assessor=lambda c, ev, t: relation(ev),
                  trusted_source_domains={"official.example"}, ledger=ledger)
    first = verify_claim_from_sources(claim(revision_id="R-1"), **kwargs)
    assert first["provenance"]["ledger_status"] == "IN_MEMORY_ONLY"

    stale = verify_claim_from_sources(claim(text="The policy reduced cases by 30 percent.", revision_id="R-1"),
                                      **kwargs)
    assert stale["provenance"] == {"ledger_status": "FAILED", "error_code": "PROVENANCE_RECORDING_FAILED",
                                   "commit_status": "NOT_COMMITTED"}
    assert "PROVENANCE_RECORDING_FAILED" in stale["findings"]
    proposals = [e for e in ledger.events if e["event_type"] == "VERIFICATION_RESULT_PROPOSED"]
    assert len(proposals) == 1


def test_partial_relation_failure_keeps_only_validated_support():
    good = source(evidence_id="E1", path="a", domain="other.example")
    bad = source(evidence_id="E2", path="b")

    def assessor(_claim, item, _timeout):
        if item["evidence_id"] == "E2":
            return relation(item, span="invented quotation")
        return relation(item)

    result = verify_claim_from_sources(
        claim(), search_provider=Search([good, bad]), mcp_source=Fetcher(good, bad),
        relation_assessor=assessor, trusted_source_domains={"official.example"},
    )
    assert [r["evidence_id"] for r in result["evidence_relations"]] == ["E1"]
    assert "EVIDENCE_RELATION_SPAN_NOT_IN_SOURCE" in result["findings"]
    assert result["verification_status"] == "PARTIALLY_VERIFIED"
