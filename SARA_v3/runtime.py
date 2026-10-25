"""Unified v3 dialogue and provider orchestration runtime."""
from __future__ import annotations

import importlib
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable, Mapping

from .mcp_adapter import MCPSourceAdapter
from .provenance import ProvenanceEventLedger
from .verification import llm_relation_assessor, trusted_domains_from_environment, verify_claim_from_sources
from .web_search import web_search_from_environment

_ROOT = Path(__file__).resolve().parents[1]
_V25 = _ROOT / "SARA_v2.5"
for _path in (_ROOT, _V25):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))
from dialogue_runtime import SARADialogueRuntime  # noqa: E402

RESPONSE_SYSTEM_PROMPT = """Answer the user's turn using the attached SARA assessment
envelopes as SARA's authoritative verification result for their bound claim
revisions. Preserve the exact
verification_status, workflow_status, scope, evidence references, and
uncertainty. PROPOSED means the result awaits durable human-review commit; it
does not make the SARA assessment optional or authorize changing its status.
UNVERIFIED means do not present the claim as verified. Do not promote a
status, invent evidence, or treat an assessment as new evidence. If you add
factual claims outside the supplied assessments, list them as
new_claim_candidates for later SARA review. Return JSON only."""

RESPONSE_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object", "properties": {
        "response": {"type": "string"},
        "used_assessment_claim_ids": {"type": "array", "items": {"type": "string"}},
        "new_claim_candidates": {"type": "array", "items": {
            "type": "object", "properties": {"id": {"type": "string"}, "text": {"type": "string"}},
            "required": ["id", "text"], "additionalProperties": False,
        }},
    }, "required": ["response", "used_assessment_claim_ids", "new_claim_candidates"],
    "additionalProperties": False,
}


class SARA_v3Runtime:
    """Compose v2.5 JEV and v2.4 epistemic checks with v3 source assessment."""
    def __init__(self, *, judgment_generate: Callable[[str, Mapping[str, Any], float], Mapping[str, Any]],
                 judgment_model_id: str, judgment_model_revision: str,
                 search_provider: Any | None,
                 relation_assessor: Callable[[Mapping[str, Any], Mapping[str, Any], float], Mapping[str, Any]] | None,
                 mcp_source: MCPSourceAdapter | None = None,
                 response_generate: Callable[[str, Mapping[str, Any], float], Mapping[str, Any]] | None = None,
                 response_model_id: str = "", response_model_revision: str = "",
                 trusted_source_domains: set[str] | None = None,
                 provenance_ledger: ProvenanceEventLedger | None = None,
                 timeout_seconds: float = 15.0) -> None:
        self.search_provider = search_provider
        self.relation_assessor = relation_assessor
        self.mcp_source = mcp_source
        self.response_generate = response_generate
        self.response_model_id = response_model_id
        self.response_model_revision = response_model_revision
        self.trusted_source_domains = set(trusted_source_domains or set())
        self.provenance_ledger = provenance_ledger or ProvenanceEventLedger()
        self.timeout_seconds = timeout_seconds

        def verify_claim(request: Mapping[str, Any]) -> Mapping[str, Any]:
            return verify_claim_from_sources(
                request, search_provider=self.search_provider, mcp_source=self.mcp_source,
                relation_assessor=self.relation_assessor, timeout_seconds=self.timeout_seconds,
                trusted_source_domains=self.trusted_source_domains,
                ledger=self.provenance_ledger,
            )

        self._dialogue = SARADialogueRuntime(
            generate=judgment_generate, verify_claim=verify_claim,
            model_id=judgment_model_id, model_revision=judgment_model_revision,
            adapter_revision="sara-v3-runtime-0.1",
        )

    def process_turn(self, payload: Mapping[str, Any], *, timeout_seconds: float | None = None) -> dict[str, Any]:
        timeout = self.timeout_seconds if timeout_seconds is None else timeout_seconds
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("V3_TIMEOUT_MUST_BE_POSITIVE_FINITE")
        result = self._dialogue.process_turn(payload, timeout_seconds=float(timeout))
        assessments: list[dict[str, Any]] = []
        route = result.get("route_execution", {})
        route_output = route.get("output") if isinstance(route, Mapping) else None
        vr = route_output.get("verification_results", []) if isinstance(route_output, Mapping) else []
        for item in vr:
            output = item.get("output") if isinstance(item, Mapping) else None
            assessment = output.get("assessment") if isinstance(output, Mapping) else None
            if isinstance(assessment, Mapping) and assessment.get("schema_version") == "sara.assessment.v3":
                assessments.append(dict(assessment))

        response_result = None
        if self.response_generate is not None:
            request = {"turn": dict(payload), "sara_assessment_envelopes": assessments,
                       "response_contract": RESPONSE_OUTPUT_SCHEMA}
            try:
                generated = self.response_generate(RESPONSE_SYSTEM_PROMPT, request, float(timeout))
                if not isinstance(generated, Mapping):
                    raise ValueError("V3_RESPONSE_MUST_BE_MAPPING")
                _validate_response(generated, assessments)
                response_result = {
                    "execution_status": "SUCCEEDED", "output": dict(generated),
                    "model_id": self.response_model_id,
                    "model_revision": self.response_model_revision,
                    "is_evidence": False,
                }
            except Exception as exc:
                response_result = {"execution_status": "FAILED", "error_code": _safe_error_code(exc),
                                   "output": None, "is_evidence": False}
        return {
            "schema_version": "sara.dialogue-result.v3", "runtime_revision": "sara-v3-runtime-0.1",
            "judgment": result.get("judgment"), "activation_decision": result.get("activation_decision"),
            "route_execution": result.get("route_execution"),
            "verification_status": _aggregate_status(assessments),
            "assessment_envelopes": assessments, "external_llm_response": response_result,
            "response_generation_status": response_result.get("execution_status") if response_result else "NOT_REQUESTED",
            "truthfulness_status": "UNASSESSED", "claim_truth_assessed": False, "is_evidence": False,
        }


def _validate_response(raw: Mapping[str, Any], assessments: list[Mapping[str, Any]]) -> None:
    if not isinstance(raw.get("response"), str):
        raise ValueError("V3_RESPONSE_TEXT_REQUIRED")
    refs = raw.get("used_assessment_claim_ids")
    known = {str(item.get("claim_id")) for item in assessments}
    if (not isinstance(refs, list) or any(not isinstance(item, str) or item not in known for item in refs)
            or len(refs) != len(set(refs)) or set(refs) != known):
        raise ValueError("V3_RESPONSE_ASSESSMENT_REFS_INVALID")
    claims = raw.get("new_claim_candidates")
    if not isinstance(claims, list):
        raise ValueError("V3_RESPONSE_NEW_CLAIMS_INVALID")
    ids: set[str] = set()
    for claim in claims:
        if not isinstance(claim, Mapping) or not isinstance(claim.get("id"), str) or not isinstance(claim.get("text"), str):
            raise ValueError("V3_RESPONSE_NEW_CLAIM_INVALID")
        if not claim["id"].strip() or not claim["text"].strip() or claim["id"] in ids:
            raise ValueError("V3_RESPONSE_NEW_CLAIM_ID_INVALID")
        ids.add(claim["id"])


def _aggregate_status(assessments: list[Mapping[str, Any]]) -> str:
    if not assessments:
        return "NOT_ASSESSED"
    statuses = {item.get("verification_status") for item in assessments}
    if statuses == {"VERIFIED"}:
        return "VERIFIED"
    if statuses == {"CONTRADICTED"}:
        return "CONTRADICTED"
    if statuses & {"VERIFIED", "PARTIALLY_VERIFIED", "CONTRADICTED"}:
        return "PARTIALLY_VERIFIED"
    return "UNVERIFIED"


def _safe_error_code(exc: Exception) -> str:
    value = str(exc).strip()
    if (type(exc).__name__ == "LLMProviderError" and value and len(value) <= 96
            and value.upper() == value and re.fullmatch(r"[A-Z0-9_]+", value)):
        return value
    return type(exc).__name__.upper()


def _load_callable(spec: str) -> Callable[..., Any]:
    if ":" not in spec:
        raise ValueError("PROVIDER_SPEC_MUST_BE_MODULE_COLON_ATTRIBUTE")
    module_name, attr_name = spec.split(":", 1)
    value = getattr(importlib.import_module(module_name), attr_name, None)
    if not callable(value):
        raise ValueError("PROVIDER_ATTRIBUTE_NOT_CALLABLE")
    return value


def process_turn(payload: Mapping[str, Any], *, judgment_generate: Callable[..., Mapping[str, Any]],
                 judgment_model_id: str, judgment_model_revision: str, search_provider: Any | None,
                 relation_assessor: Callable[..., Mapping[str, Any]] | None,
                 mcp_source: MCPSourceAdapter | None = None, response_generate: Callable[..., Mapping[str, Any]] | None = None,
                 response_model_id: str = "", response_model_revision: str = "",
                 trusted_source_domains: set[str] | None = None,
                 provenance_ledger: ProvenanceEventLedger | None = None,
                 timeout_seconds: float = 15.0) -> dict[str, Any]:
    runtime = SARA_v3Runtime(
        judgment_generate=judgment_generate, judgment_model_id=judgment_model_id,
        judgment_model_revision=judgment_model_revision, search_provider=search_provider,
        relation_assessor=relation_assessor, mcp_source=mcp_source,
        response_generate=response_generate, response_model_id=response_model_id,
        response_model_revision=response_model_revision, trusted_source_domains=trusted_source_domains,
        provenance_ledger=provenance_ledger,
        timeout_seconds=timeout_seconds,
    )
    return runtime.process_turn(payload, timeout_seconds=timeout_seconds)


def process_turn_from_environment(payload: Mapping[str, Any], *, timeout_seconds: float = 15.0) -> dict[str, Any]:
    """Load judgment/response LLMs, default Brave search, and optional host MCP bridge."""
    from llm_provider_adapter import LLMProviderAdapter, LLMProviderConfig, JUDGMENT_OUTPUT_SCHEMA

    judgment_config = LLMProviderConfig.from_environment()
    judgment_adapter = LLMProviderAdapter(judgment_config)

    def judgment_generate(rubric, data, timeout):
        return judgment_adapter.generate_json(system_prompt=rubric, user_payload=data,
                                              output_schema=JUDGMENT_OUTPUT_SCHEMA, timeout_seconds=timeout)

    search = web_search_from_environment()
    revision = os.environ.get("SARA_LLM_MODEL_REVISION", "").strip() or f"{judgment_config.provider}:{judgment_config.model}"
    relation_config = LLMProviderConfig.from_environment(prefix="SARA_RELATION_LLM") if os.environ.get("SARA_RELATION_LLM_PROVIDER") else judgment_config
    relation_adapter = judgment_adapter if relation_config == judgment_config else LLMProviderAdapter(relation_config)
    relation_revision = os.environ.get("SARA_RELATION_LLM_MODEL_REVISION", "").strip() or f"{relation_config.provider}:{relation_config.model}"
    relation_assessor = llm_relation_assessor(llm_adapter=relation_adapter,
                                              model_id=relation_config.model, model_revision=relation_revision)
    mcp_source = None
    mcp_spec = os.environ.get("SARA_MCP_CALL_TOOL", "").strip()
    if mcp_spec:
        search_tool = os.environ.get("SARA_MCP_SEARCH_TOOL", "").strip() or None
        fetch_tool = os.environ.get("SARA_MCP_FETCH_TOOL", "").strip() or None
        domains = {d.strip().lower().lstrip(".") for d in os.environ.get("SARA_MCP_FETCH_ALLOWED_DOMAINS", "").split(",") if d.strip()}
        mcp_source = MCPSourceAdapter(_load_callable(mcp_spec), search_tool=search_tool,
                                      fetch_tool=fetch_tool,
                                      allowed_tools={v for v in (search_tool, fetch_tool) if v},
                                      fetch_allowed_domains=domains)

    response_config = LLMProviderConfig.from_environment(prefix="SARA_RESPONSE_LLM") if os.environ.get("SARA_RESPONSE_LLM_PROVIDER") else judgment_config
    response_adapter = judgment_adapter if response_config == judgment_config else LLMProviderAdapter(response_config)

    def response_generate(system_prompt, data, timeout):
        return response_adapter.generate_json(system_prompt=system_prompt, user_payload=data,
                                              output_schema=RESPONSE_OUTPUT_SCHEMA, timeout_seconds=timeout)

    response_revision = os.environ.get("SARA_RESPONSE_LLM_MODEL_REVISION", "").strip() or f"{response_config.provider}:{response_config.model}"
    return process_turn(
        payload, judgment_generate=judgment_generate, judgment_model_id=judgment_config.model,
        judgment_model_revision=revision, search_provider=search, relation_assessor=relation_assessor,
        mcp_source=mcp_source, response_generate=response_generate,
        response_model_id=response_config.model, response_model_revision=response_revision,
        trusted_source_domains=trusted_domains_from_environment(), timeout_seconds=timeout_seconds,
    )
