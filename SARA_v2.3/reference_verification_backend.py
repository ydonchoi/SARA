"""Deterministic reference verification backend for SARA v2.3.

This backend is intentionally limited to a caller-supplied reference corpus.
It verifies structural/content relationships against immutable reference
records; it does not perform live external research and never establishes
truthfulness.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Mapping

from SARA_v2.3.execution import (
    SARAExecutionRequest,
    SARAExecutionResponse,
    VerificationBackend,
)


@dataclass(frozen=True)
class ReferenceSource:
    source_id: str
    uri: str
    content: str
    source_level: int
    bibliographic_verified: bool = False


class ReferenceVerificationBackend(VerificationBackend):
    """Verify claims against a controlled, immutable reference corpus."""

    provider_id = "SARA"

    def __init__(self, sources: Mapping[str, ReferenceSource]):
        self._sources = dict(sources)

    def verify(self, request: SARAExecutionRequest) -> SARAExecutionResponse:
        claim = request.claim
        claim_id = claim["id"]
        evidence = {item["id"]: item for item in request.evidence}
        claim_evidence_ids = tuple(claim.get("evidence_ids") or ())

        checks: list[str] = []
        eligible = True
        citation_verified = True
        matched = False

        for evidence_id in claim_evidence_ids:
            item = evidence[evidence_id]
            source_id = item.get("source")
            source = self._sources.get(source_id)
            if source is None:
                eligible = False
                checks.append(f"{evidence_id}:SOURCE_UNAVAILABLE")
                continue

            if item.get("usable_as_verification_evidence", True) is False:
                eligible = False
                checks.append(f"{evidence_id}:EVIDENCE_INELIGIBLE")
                continue

            if claim_id not in (item.get("supports_claims") or ()):
                eligible = False
                checks.append(f"{evidence_id}:CLAIM_BINDING_MISSING")
                continue

            if claim["text"] not in source.content:
                eligible = False
                checks.append(f"{evidence_id}:CLAIM_CONTENT_NOT_FOUND")
                continue

            if source.bibliographic_verified:
                checks.append(f"{evidence_id}:BIBLIOGRAPHIC_VERIFIED")
            else:
                citation_verified = False
                checks.append(f"{evidence_id}:BIBLIOGRAPHIC_UNVERIFIED")

            strength = item.get("evidence_strength")
            if strength not in {"strong", "moderate", "weak"}:
                eligible = False
                checks.append(f"{evidence_id}:EVIDENCE_STRENGTH_INVALID")
                continue

            matched = True
            checks.append(f"{evidence_id}:CONTENT_AND_CLAIM_FIT_VERIFIED")

        if not claim_evidence_ids:
            eligible = False
            checks.append("NO_CLAIM_EVIDENCE")

        if eligible and matched:
            verification_status = "VERIFIED"
        elif matched:
            verification_status = "PARTIALLY VERIFIED"
        else:
            verification_status = "UNVERIFIED"

        source_fingerprint = sha256(
            "|".join(
                f"{s.source_id}:{sha256(s.content.encode('utf-8')).hexdigest()}"
                for s in sorted(self._sources.values(), key=lambda x: x.source_id)
            ).encode("utf-8")
        ).hexdigest()
        result_fingerprint = sha256(
            f"{request.request_id}|{claim_id}|{claim['text']}|{source_fingerprint}".encode("utf-8")
        ).hexdigest()

        return SARAExecutionResponse(
            request_id=request.request_id,
            claim_id=claim_id,
            provider_id=self.provider_id,
            adapter_revision=request.adapter_revision,
            status="SUCCEEDED",
            external_result_id=f"REF-{result_fingerprint[:16]}",
            external_result_provenance_ids=(f"REF-PROV-{source_fingerprint[:16]}",),
            verification_status=verification_status,
            verification_layer="research_verification",
            findings=tuple(checks),
            uncertainty=(
                "Controlled reference corpus only; live external research was not performed."
                if verification_status == "VERIFIED"
                else "Reference verification did not establish full claim-evidence support."
            ),
            structural_validity="VALID",
            truthfulness_status="UNASSESSED",
            reproduction_status=None,
            external_citation_verification={
                "status": "VERIFIED" if citation_verified and matched else "NOT_COMPLETED",
                "note": "Bibliographic verification is scoped to the supplied reference corpus.",
            },
            timestamp=request.requested_at,
            environment={"backend": "reference", "live_external_research": False},
        )
