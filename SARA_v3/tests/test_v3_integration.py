from __future__ import annotations

from typing import Any, Mapping

import pytest

from SARA_v3.contracts import V3ContractError, create_assessment_envelope, normalize_evidence, validate_relation_result
from SARA_v3.mcp_adapter import MCPAdapterError, MCPSourceAdapter
from SARA_v3.provenance import ProvenanceEventLedger
from SARA_v3.runtime import SARA_v3Runtime
from SARA_v3.verification import verify_claim_from_sources
from internal_judgment_model import compute_judgment_input_digest


def source(*, access="FULL_TEXT", domain="official.example", content="The policy reduced cases by 20 percent.", evidence_id="E1"):
    return {
        "evidence_id": evidence_id,
        "url": f"https://{domain}/study",
        "title": "Study",
        "access_level": access,
        "content": content if access == "FULL_TEXT" else "",
        "snippet": "The policy reduced cases by 20 percent." if access != "FULL_TEXT" else "",
        "source_type": "TEST_SOURCE",
        "provenance": {"provider": "test"},
    }


def relation(evidence, kind="SUPPORTS", span="The policy reduced cases by 20 percent."):
    return {
        "evidence_id": evidence["evidence_id"],
        "relation": kind,
        "rationale": "The quoted source span directly addresses the claim.",
        "support_spans": [span] if kind in {"SUPPORTS", "CHALLENGES", "MIXED"} else [],
    }


class FullTextFetcher:
    def __init__(self, evidence):
        self.evidence = evidence

    def search(self, _query):
        return []

    def fetch(self, url):
        assert url == self.evidence["url"]
        return self.evidence


def test_source_provider_cannot_set_claim_verification_status():
    with pytest.raises(V3ContractError, match="SOURCE_PROVIDER_MUST_NOT_SET_VERIFICATION_STATUS"):
        normalize_evidence({**source(), "verification_status": "VERIFIED"}, fallback_id="E1")


def test_search_snippet_is_never_enough_for_verified_status():
    evidence = source(access="SEARCH_SNIPPET")
    result = verify_claim_from_sources(
        {"claim": {"id": "C1", "text": "The policy reduced cases by 20 percent."}},
        search_provider=type("Search", (), {"search": lambda self, *_a, **_k: [evidence]})(),
        mcp_source=None,
        relation_assessor=lambda claim, item, timeout: relation(item),
        trusted_source_domains={"official.example"},
    )
    assert result["verification_status"] == "UNVERIFIED"
    assert "FULL_TEXT_NOT_ACCESSED" in result["assessment"]["uncertainty"]


def test_search_provider_cannot_assert_full_text_access():
    evidence = source()
    result = verify_claim_from_sources(
        {"claim": {"id": "C1", "text": "The policy reduced cases by 20 percent."}},
        search_provider=type("Search", (), {"search": lambda self, *_a, **_k: [evidence]})(),
        mcp_source=None,
        relation_assessor=lambda claim, item, timeout: relation(item),
        trusted_source_domains={"official.example"},
    )
    assert result["verification_status"] == "UNVERIFIED"


def test_full_text_source_records_uncommitted_v25_proposal_without_runtime_error():
    evidence = source()
    result = verify_claim_from_sources(
        {"claim": {"id": "C1", "text": "The policy reduced cases by 20 percent."}},
        search_provider=type("Search", (), {"search": lambda self, *_a, **_k: [evidence]})(),
        mcp_source=FullTextFetcher(evidence),
        relation_assessor=lambda claim, item, timeout: relation(item),
        trusted_source_domains={"official.example"},
        ledger=ProvenanceEventLedger(),
    )
    assert result["verification_status"] == "VERIFIED"
    assert result["provenance"]["commit_status"] == "NOT_COMMITTED"
    assert result["provenance"]["ledger_status"] == "IN_MEMORY_ONLY"
    assert result["assessment"]["provenance"]["proposal_event_id"]


def test_provider_error_text_is_not_reflected_in_assessment():
    class FailingSearch:
        def search(self, *_args, **_kwargs):
            raise RuntimeError("https://private.invalid/path?token=secret")

    result = verify_claim_from_sources(
        {"claim": {"id": "C1", "text": "A bounded claim."}},
        search_provider=FailingSearch(), mcp_source=None, relation_assessor=None,
    )
    assert result["status"] == "FAILED"
    assert result["findings"] == ["WEB_SEARCH_FAILED", "SOURCE_RELATION_ASSESSOR_NOT_CONFIGURED",
                                   "SOURCE_VERIFICATION_EXECUTION_FAILED"]


def test_trusted_full_text_support_is_a_proposal_and_keeps_v24_dimensions():
    evidence = source()
    result = verify_claim_from_sources(
        {"claim": {"id": "C1", "text": "The policy reduced cases by 20 percent.", "scope": {"time_range": "2024"}}},
        search_provider=type("Search", (), {"search": lambda self, *_a, **_k: [evidence]})(),
        mcp_source=FullTextFetcher(evidence),
        relation_assessor=lambda claim, item, timeout: relation(item),
        trusted_source_domains={"official.example"},
    )
    assessment = result["assessment"]
    assert assessment["verification_status"] == "VERIFIED"
    assert assessment["workflow_status"] == "PROPOSED"
    assert assessment["truthfulness_status"] == "UNASSESSED"
    assert assessment["v24_epistemic_assessment"]["is_evidence"] is False
    assert assessment["v24_logical_audit"]["audit_status"] == "NOT_RUN"
    assert assessment["literal_citation_fit_signals"][0]["promotes_verification_status"] is False


def test_relation_spans_must_exist_verbatim_in_source():
    evidence = normalize_evidence(source(), fallback_id="E1")
    with pytest.raises(V3ContractError, match="EVIDENCE_RELATION_SPAN_NOT_IN_SOURCE"):
        validate_relation_result(relation(evidence, span="invented quotation"), evidence=evidence)


def test_mcp_fetch_requires_allowlisted_tool_and_domain():
    with pytest.raises(MCPAdapterError, match="MCP_TOOL_NOT_ALLOWLISTED"):
        MCPSourceAdapter(lambda *_: {}, fetch_tool="read", allowed_tools=set())
    adapter = MCPSourceAdapter(lambda *_: {}, fetch_tool="read", allowed_tools={"read"}, fetch_allowed_domains={"example.org"})
    with pytest.raises(MCPAdapterError, match="MCP_FETCH_URL_OUTSIDE_DOMAIN_ALLOWLIST"):
        adapter.fetch("https://attacker.invalid/page")


def _dialogue_request():
    return {
        "request_id": "REQ-1", "conversation_id": "CONV-1", "turn_id": "TURN-1",
        "content": "Sales rose after the campaign, therefore the campaign caused the increase.",
        "claim_candidates": [{"id": "C1", "text": "The campaign caused the increase."}],
        "evidence": [], "provenance_ids": ["INPUT-PROV-1"],
    }


def test_sara_assessment_is_returned_to_external_llm_as_bound_context():
    captured: dict[str, Any] = {}
    evidence = source(domain="official.example", content="The campaign caused the increase.")

    def judgment_generate(_rubric: str, payload: Mapping[str, Any], _timeout: float):
        return {
            "request_id": payload["request_id"],
            "input_revision_digest": compute_judgment_input_digest(payload),
            "judgment_status": "INFERENCE_PRESENT",
            "inference_types": ["CAUSAL"],
            "basis_spans": ["therefore the campaign caused the increase"],
            "rationale": "The conclusion asserts causality.",
            "uncertainty_reason": "",
            "confidence": "HIGH",
            "premise_refs": [], "claim_refs": ["C1"], "evidence_ids": [], "provenance_ids": [],
        }

    def search(_query: str, *, count: int):
        return [evidence]

    def assess(_claim, item, _timeout):
        return relation(item, span="The campaign caused the increase.")

    def respond(_system_prompt: str, payload: Mapping[str, Any], _timeout: float):
        captured["assessment"] = payload["sara_assessment_envelopes"][0]
        return {"response": "SARA found support in the linked source.",
                "used_assessment_claim_ids": ["C1"], "new_claim_candidates": []}

    result = SARA_v3Runtime(
        judgment_generate=judgment_generate, judgment_model_id="test-model",
        judgment_model_revision="test-rev", search_provider=type("Search", (), {"search": staticmethod(search)})(),
        relation_assessor=assess, mcp_source=FullTextFetcher(evidence), response_generate=respond, response_model_id="test-model",
        response_model_revision="test-rev", trusted_source_domains={"official.example"},
    ).process_turn(_dialogue_request())

    assert result["schema_version"] == "sara.dialogue-result.v3"
    assert captured["assessment"]["claim_id"] == "C1"
    assert captured["assessment"]["verification_status"] == "VERIFIED"
    assert captured["assessment"]["workflow_status"] == "PROPOSED"
    assert captured["assessment"]["provenance"]["commit_status"] == "NOT_COMMITTED"
    assert result["external_llm_response"]["execution_status"] == "SUCCEEDED"
    assert result["assessment_envelopes"][0]["verification_status"] == "VERIFIED"
    assert result["truthfulness_status"] == "UNASSESSED"
