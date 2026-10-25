"""Validated evidence and assessment contracts for SARA v3."""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.parse import urlparse

_V25_ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.5"
if str(_V25_ROOT) not in sys.path:
    sys.path.insert(0, str(_V25_ROOT))
from claim_identity import compute_content_digest  # noqa: E402

ACCESS_LEVELS = {"SEARCH_SNIPPET", "METADATA", "ABSTRACT", "FULL_TEXT", "UNAVAILABLE"}
EVIDENCE_RELATIONS = {"SUPPORTS", "CHALLENGES", "MIXED", "IRRELEVANT", "INSUFFICIENT"}


class V3ContractError(ValueError):
    """Raised when provider or evaluator output violates the v3 contract."""


def _required_string(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise V3ContractError(error)
    return value.strip()


def normalize_evidence(item: Mapping[str, Any], *, fallback_id: str) -> dict[str, Any]:
    """Normalize a retrieved source; reject provider-asserted claim statuses."""
    if not isinstance(item, Mapping):
        raise V3ContractError("EVIDENCE_MUST_BE_MAPPING")
    if "verification_status" in item or "claim_status" in item:
        raise V3ContractError("SOURCE_PROVIDER_MUST_NOT_SET_VERIFICATION_STATUS")
    evidence_id = _required_string(item.get("evidence_id") or fallback_id, "EVIDENCE_ID_REQUIRED")
    url = _required_string(item.get("url"), "EVIDENCE_URL_REQUIRED")
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
    except ValueError as exc:
        raise V3ContractError("EVIDENCE_URL_INVALID") from exc
    if parsed.scheme != "https" or not hostname or parsed.username or parsed.password:
        raise V3ContractError("EVIDENCE_URL_MUST_BE_PUBLIC_HTTPS")
    title = _required_string(item.get("title") or hostname, "EVIDENCE_TITLE_REQUIRED")
    access_level = item.get("access_level", "SEARCH_SNIPPET")
    if not isinstance(access_level, str) or access_level not in ACCESS_LEVELS:
        raise V3ContractError("EVIDENCE_ACCESS_LEVEL_INVALID")
    content, snippet = item.get("content", ""), item.get("snippet", "")
    if not isinstance(content, str) or not isinstance(snippet, str):
        raise V3ContractError("EVIDENCE_TEXT_FIELDS_MUST_BE_STRINGS")
    if access_level == "FULL_TEXT" and not content.strip():
        raise V3ContractError("FULL_TEXT_EVIDENCE_REQUIRES_CONTENT")
    if access_level == "SEARCH_SNIPPET" and not snippet.strip():
        raise V3ContractError("SEARCH_SNIPPET_REQUIRES_SNIPPET")
    retrieved_at = item.get("retrieved_at") or datetime.now(timezone.utc).isoformat()
    _required_string(retrieved_at, "EVIDENCE_RETRIEVAL_TIME_REQUIRED")
    source_type = item.get("source_type", "WEB")
    if not isinstance(source_type, str) or not source_type.strip():
        raise V3ContractError("EVIDENCE_SOURCE_TYPE_INVALID")
    return {
        "evidence_id": evidence_id, "url": url, "domain": hostname.lower(),
        "title": title, "publisher": str(item.get("publisher", "UNKNOWN")),
        "published_at": item.get("published_at"), "retrieved_at": retrieved_at,
        "access_level": access_level, "source_type": source_type,
        "content": content[:100_000], "snippet": snippet[:8_000],
        "content_digest": sha256(content.encode("utf-8")).hexdigest() if content else None,
        "source_independence_key": str(item.get("source_independence_key", hostname.lower())),
        "scope_key": str(item.get("scope_key", "UNSPECIFIED")),
        "provenance": dict(item.get("provenance") or {}) if isinstance(item.get("provenance") or {}, Mapping) else {},
        "is_evidence": True,
    }


def validate_relation_result(raw: Mapping[str, Any], *, evidence: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise V3ContractError("EVIDENCE_RELATION_RESULT_MUST_BE_MAPPING")
    if raw.get("evidence_id") != evidence["evidence_id"]:
        raise V3ContractError("EVIDENCE_RELATION_ID_MISMATCH")
    relation = raw.get("relation")
    if not isinstance(relation, str) or relation not in EVIDENCE_RELATIONS:
        raise V3ContractError("EVIDENCE_RELATION_INVALID")
    rationale = _required_string(raw.get("rationale"), "EVIDENCE_RELATION_RATIONALE_REQUIRED")
    spans = raw.get("support_spans", [])
    if not isinstance(spans, list) or any(not isinstance(s, str) or not s.strip() for s in spans):
        raise V3ContractError("EVIDENCE_RELATION_SPANS_INVALID")
    source_text = evidence["content"] if evidence["access_level"] == "FULL_TEXT" else evidence["snippet"]
    if any(span not in source_text for span in spans):
        raise V3ContractError("EVIDENCE_RELATION_SPAN_NOT_IN_SOURCE")
    if relation in {"SUPPORTS", "CHALLENGES", "MIXED"} and not spans:
        raise V3ContractError("EVIDENCE_RELATION_REQUIRES_SOURCE_SPAN")
    return {
        "evidence_id": evidence["evidence_id"], "relation": relation,
        "rationale": rationale, "support_spans": spans,
        "assessor_id": str(raw.get("assessor_id", "SARA_EVIDENCE_RELATION_MODEL")),
        "assessor_revision": str(raw.get("assessor_revision", "UNSPECIFIED")),
        "is_evidence": False,
    }


def _domain_trusted(domain: str, trusted: set[str]) -> bool:
    return any(domain == host or domain.endswith("." + host) for host in trusted)


def create_assessment_envelope(
    *, claim: Mapping[str, Any], evidence: list[Mapping[str, Any]],
    relations: list[Mapping[str, Any]], trusted_source_domains: set[str] | None = None,
    execution_status: str = "SUCCEEDED", findings: list[str] | None = None,
) -> dict[str, Any]:
    """Apply deterministic access/trust rules to validated relation proposals."""
    claim_id = _required_string(claim.get("id"), "CLAIM_ID_REQUIRED")
    claim_text = _required_string(claim.get("text"), "CLAIM_TEXT_REQUIRED")
    scope_value = claim.get("scope") or {}
    if not isinstance(scope_value, Mapping):
        raise V3ContractError("CLAIM_SCOPE_MUST_BE_MAPPING")
    scope = dict(scope_value)
    trusted = {host.lower().strip(".") for host in (trusted_source_domains or set())}
    by_id = {item["evidence_id"]: item for item in evidence}
    relation_by_id = {item["evidence_id"]: item for item in relations}
    if len(relation_by_id) != len(relations) or any(key not in by_id for key in relation_by_id):
        raise V3ContractError("EVIDENCE_RELATION_REFERENCES_INVALID")
    fulltext = [item for item in evidence if item["access_level"] == "FULL_TEXT"]
    supporting = [item for item in relations if item["relation"] == "SUPPORTS" and item["evidence_id"] in by_id and by_id[item["evidence_id"]]["access_level"] == "FULL_TEXT"]
    challenging = [item for item in relations if item["relation"] == "CHALLENGES" and item["evidence_id"] in by_id and by_id[item["evidence_id"]]["access_level"] == "FULL_TEXT"]
    mixed = [item for item in relations if item["relation"] == "MIXED"]
    trusted_support = [item for item in supporting if _domain_trusted(by_id[item["evidence_id"]]["domain"], trusted)]
    trusted_challenge = [item for item in challenging if _domain_trusted(by_id[item["evidence_id"]]["domain"], trusted)]
    if execution_status != "SUCCEEDED":
        status, result_findings = "UNVERIFIED", list(findings or []) + ["SOURCE_VERIFICATION_EXECUTION_FAILED"]
    elif not evidence:
        status, result_findings = "UNVERIFIED", list(findings or []) + ["NO_SOURCE_EVIDENCE_RETRIEVED"]
    elif not fulltext:
        status, result_findings = "UNVERIFIED", list(findings or []) + ["FULL_TEXT_NOT_ACCESSED"]
    elif (supporting and challenging) or mixed:
        status, result_findings = "PARTIALLY_VERIFIED", list(findings or []) + ["CONFLICTING_OR_MIXED_SOURCE_EVIDENCE"]
    elif trusted_challenge:
        status, result_findings = "CONTRADICTED", list(findings or []) + ["TRUSTED_FULL_TEXT_CHALLENGES_CLAIM"]
    elif trusted_support:
        status, result_findings = "VERIFIED", list(findings or []) + ["TRUSTED_FULL_TEXT_SUPPORTS_CLAIM"]
    elif supporting:
        status, result_findings = "PARTIALLY_VERIFIED", list(findings or []) + ["SUPPORTING_SOURCE_NOT_IN_TRUSTED_DOMAIN_POLICY"]
    else:
        status, result_findings = "UNVERIFIED", list(findings or []) + ["NO_VALIDATED_SUPPORT_RELATION"]
    evidence_digest = sha256(json.dumps(
        [{k: v for k, v in item.items() if k not in {"content", "snippet"}} for item in evidence],
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str,
    ).encode("utf-8")).hexdigest()
    claim_digest = compute_content_digest(claim_text, scope)
    return {
        "schema_version": "sara.assessment.v3", "claim_id": claim_id,
        "claim_revision_id": str(claim.get("revision_id", claim.get("revision", "R-" + claim_digest[:16]))),
        "claim_digest": claim_digest, "verification_status": status,
        "assessment_authority": "SARA_RESULT_FOR_BOUND_REVISION",
        "workflow_status": "PROPOSED", "execution_status": execution_status,
        "scope": scope, "evidence_refs": [item["evidence_id"] for item in evidence],
        "evidence_access_levels": {item["evidence_id"]: item["access_level"] for item in evidence},
        "evidence_relations": [dict(item) for item in relations],
        "evidence_digest": evidence_digest, "checked_at": datetime.now(timezone.utc).isoformat(),
        "verifier_revision": "sara-v3-source-assessment-v0.1",
        "verification_contract_revision": "sara.assessment.v3",
        "uncertainty": result_findings, "truthfulness_status": "UNASSESSED",
        "claim_truth_assessed": False, "is_evidence": False, "source": "SARA_V3_ASSESSMENT",
    }
