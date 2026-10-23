"""Live Crossref metadata provider for SARA's production runtime.

This provider verifies DOI registration and bibliographic metadata only.
It deliberately does not claim to verify the truth of a substantive claim:
Crossref metadata is not article full text or claim-level evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

CROSSREF_API = "https://api.crossref.org/works/"
DOI_PATTERN = re.compile(r"^10\.\d{4,9}/\S+$")


def _normalize_doi(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    doi = value.strip()
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/)", "", doi, flags=re.IGNORECASE)
    doi = re.sub(r"^doi:\s*", "", doi, flags=re.IGNORECASE)
    return doi.rstrip(".,;)")


def _find_bound_evidence(request: Mapping[str, Any]) -> dict[str, Any] | None:
    claim = request.get("claim") or {}
    claim_id = str(claim.get("id") or "")
    requested_ids = set(claim.get("evidence_ids") or ())
    for item in request.get("evidence") or ():
        if not isinstance(item, dict) or not item.get("id"):
            continue
        explicitly_bound = (
            claim_id in (item.get("supports_claims") or ())
            or item["id"] in requested_ids
        )
        doi = _normalize_doi(item.get("doi") or item.get("DOI"))
        if explicitly_bound and DOI_PATTERN.match(doi):
            return item
    return None


def verify(request: Mapping[str, Any]) -> Mapping[str, Any]:
    """Resolve a claim-bound DOI against Crossref and return bounded evidence."""
    claim = request.get("claim") or {}
    claim_id = str(claim.get("id") or "")
    evidence = _find_bound_evidence(request)
    if not claim_id or evidence is None:
        return {
            "status": "REJECTED",
            "failure": {"code": "BOUND_DOI_EVIDENCE_REQUIRED"},
            "findings": ["BOUND_DOI_EVIDENCE_REQUIRED"],
        }

    evidence_id = str(evidence["id"])
    doi = _normalize_doi(evidence.get("doi") or evidence.get("DOI"))
    endpoint = CROSSREF_API + quote(doi, safe="/")
    headers = {
        "Accept": "application/json",
        "User-Agent": "SARA-VerificationProvider/1.0"
        + (
            f" (mailto:{os.environ['CROSSREF_MAILTO']})"
            if os.environ.get("CROSSREF_MAILTO")
            else ""
        ),
    }
    try:
        req = Request(endpoint, headers=headers)
        with urlopen(req, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        code = "CROSSREF_DOI_NOT_FOUND" if exc.code == 404 else "CROSSREF_HTTP_ERROR"
        return {
            "status": "FAILED",
            "failure": {"code": code, "http_status": exc.code},
            "findings": [code],
        }
    except (URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "status": "FAILED",
            "failure": {
                "code": "CROSSREF_LOOKUP_FAILED",
                "error_type": type(exc).__name__,
            },
            "findings": ["CROSSREF_LOOKUP_FAILED"],
        }

    message = payload.get("message") or {}
    returned_doi = _normalize_doi(message.get("DOI"))
    if returned_doi.lower() != doi.lower():
        return {
            "status": "FAILED",
            "failure": {"code": "CROSSREF_DOI_IDENTITY_MISMATCH"},
            "findings": ["CROSSREF_DOI_IDENTITY_MISMATCH"],
        }

    metadata = {
        "DOI": returned_doi,
        "title": message.get("title", []),
        "author": message.get("author", []),
        "container-title": message.get("container-title", []),
        "published": (
            message.get("published")
            or message.get("published-print")
            or message.get("published-online")
        ),
        "publisher": message.get("publisher"),
        "type": message.get("type"),
        "URL": message.get("URL"),
    }
    fingerprint = hashlib.sha256(
        f"crossref|{returned_doi.lower()}|{request.get('request_id', '')}".encode(
            "utf-8"
        )
    ).hexdigest()
    metadata_text = json.dumps(metadata, ensure_ascii=False, sort_keys=True)
    return {
        "status": "SUCCEEDED",
        "external_result_id": f"crossref:{returned_doi}",
        "external_result_provenance_ids": [f"CROSSREF-PROV-{fingerprint[:20]}"],
        "verification_status": "UNVERIFIED",
        "findings": ["CROSSREF_DOI_RESOLVED", "BIBLIOGRAPHIC_METADATA_ONLY"],
        "uncertainty": (
            "Crossref confirms DOI registration and metadata only; "
            "substantive claim truth is not verified."
        ),
        "source_exists": True,
        "bibliographic_accuracy": "VERIFIED",
        "evidence_id": evidence_id,
        "supports_claim_ids": [claim_id],
        "content_scope": "BIBLIOGRAPHIC_METADATA",
        "content_access": {
            "status": "RETRIEVED",
            "content": metadata_text,
            "url": endpoint,
            "content_type": "application/json",
            "byte_length": len(metadata_text.encode("utf-8")),
            "findings": ["CROSSREF_METADATA_RETRIEVED"],
            "content_scope": "BIBLIOGRAPHIC_METADATA",
            "evidence_id": evidence_id,
        },
        "external_citation_verification": {
            "status": "VERIFIED",
            "provider": "Crossref REST API",
            "doi": returned_doi,
            "metadata_url": endpoint,
            "scope": "DOI registration and bibliographic metadata only",
        },
    }
