"""External-source retrieval boundary for SARA v2.5.

The search provider is injected by the host. Retrieved records are evidence
candidates only: retrieval never marks a claim verified. The provider must
enforce its timeout at the transport boundary.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from hashlib import sha256
from math import isfinite
from typing import Any
from urllib.parse import urlsplit

SearchCallable = Callable[[Mapping[str, Any], float], list[Mapping[str, Any]]]


class ExternalEvidenceError(ValueError):
    """Raised when external retrieval is unavailable or returns malformed data."""


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


def _is_http_url(value: str) -> bool:
    """Accept absolute HTTP(S) URLs with a host; reject credential-bearing URLs."""
    try:
        parsed = urlsplit(value)
        return (
            parsed.scheme.lower() in {"http", "https"}
            and bool(parsed.hostname)
            and parsed.username is None
            and parsed.password is None
        )
    except ValueError:
        return False


def collect_external_evidence(
    search: SearchCallable,
    *,
    claim: Mapping[str, Any],
    context: Mapping[str, Any],
    timeout_seconds: float,
    max_results: int = 5,
) -> dict[str, Any]:
    """Retrieve and normalize source candidates for one bound claim.

    This function never assigns a verification verdict. An empty search result
    is explicit and must not be treated as evidence that the claim is false.
    """
    if not callable(search):
        raise ExternalEvidenceError("EXTERNAL_SEARCH_PROVIDER_REQUIRED")
    if not isinstance(claim, Mapping) or not isinstance(claim.get("id"), str) or not claim["id"].strip():
        raise ExternalEvidenceError("EXTERNAL_SEARCH_CLAIM_ID_REQUIRED")
    if not isinstance(claim.get("text"), str) or not claim["text"].strip():
        raise ExternalEvidenceError("EXTERNAL_SEARCH_CLAIM_TEXT_REQUIRED")
    if not isinstance(context, Mapping):
        raise ExternalEvidenceError("EXTERNAL_SEARCH_CONTEXT_MUST_BE_MAPPING")
    if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or not isfinite(timeout_seconds) or timeout_seconds <= 0:
        raise ExternalEvidenceError("EXTERNAL_SEARCH_TIMEOUT_MUST_BE_POSITIVE")
    if isinstance(max_results, bool) or not isinstance(max_results, int) or max_results < 1 or max_results > 20:
        raise ExternalEvidenceError("EXTERNAL_SEARCH_MAX_RESULTS_OUT_OF_RANGE")

    scope = claim.get("scope") or {}
    if not isinstance(scope, Mapping):
        raise ExternalEvidenceError("EXTERNAL_SEARCH_CLAIM_SCOPE_MUST_BE_MAPPING")

    request = {
        "purpose": "VERIFY_EXTERNAL_CLAIM",
        "claim_id": claim["id"],
        "claim_text": claim["text"],
        "scope": dict(scope),
        "context": dict(context),
        "max_results": max_results,
        "required_result_fields": ["url", "title_or_source", "text_or_snippet"],
        "claim_truth_assessed": False,
        "is_evidence": False,
    }
    try:
        raw = search(request, float(timeout_seconds))
    except TimeoutError as exc:
        raise ExternalEvidenceError("EXTERNAL_SEARCH_TIMEOUT") from exc
    except Exception as exc:
        raise ExternalEvidenceError("EXTERNAL_SEARCH_FAILED") from exc

    if not isinstance(raw, list):
        raise ExternalEvidenceError("EXTERNAL_SEARCH_RESULTS_MUST_BE_LIST")

    normalized = []
    seen = set()
    for item in raw[:max_results]:
        if not isinstance(item, Mapping):
            raise ExternalEvidenceError("EXTERNAL_SEARCH_RESULT_MUST_BE_MAPPING")
        url = item.get("url") or item.get("source_url")
        source = item.get("source") or item.get("title") or url
        text = item.get("text") or item.get("snippet") or item.get("content")
        if not isinstance(url, str) or not url.strip():
            raise ExternalEvidenceError("EXTERNAL_SEARCH_RESULT_URL_REQUIRED")
        url = url.strip()
        if not _is_http_url(url):
            raise ExternalEvidenceError("EXTERNAL_SEARCH_RESULT_URL_MUST_BE_HTTP")
        if not isinstance(source, str) or not source.strip():
            raise ExternalEvidenceError("EXTERNAL_SEARCH_RESULT_SOURCE_REQUIRED")
        if not isinstance(text, str) or not text.strip():
            raise ExternalEvidenceError("EXTERNAL_SEARCH_RESULT_TEXT_REQUIRED")
        canonical = f"{url}\n{text.strip()}"
        fingerprint = _digest(canonical)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        normalized.append({
            "id": str(item.get("id") or f"EXT-EVIDENCE-{fingerprint[:16]}"),
            "source": source.strip(),
            "url": url,
            "text": text.strip(),
            "retrieved_at": str(item.get("retrieved_at") or datetime.now(timezone.utc).isoformat()),
            "provenance_id": str(item.get("provenance_id") or f"EXT-SOURCE-{fingerprint[:16]}"),
            "evidence_kind": "EXTERNAL_SOURCE_CANDIDATE",
            "verification_status": "UNASSESSED",
            "is_evidence": False,
        })

    return {
        "status": "COLLECTED" if normalized else "NO_RESULTS",
        "claim_id": claim["id"],
        "results": normalized,
        "result_count": len(normalized),
        "duplicates_removed": max(0, min(len(raw), max_results) - len(normalized)),
        "source_candidates_are_not_verified": True,
        "claim_truth_assessed": False,
        "is_evidence": False,
    }
