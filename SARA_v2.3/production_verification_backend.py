"""Minimal production-oriented SARA verification backend.

This backend owns the SARA execution boundary and delegates source-level
verification to an injected external provider callable. It is deliberately
provider-neutral: a provider may perform live source resolution, while SARA
retains verification/provenance semantics and never upgrades truthfulness
implicitly.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any, Callable, Mapping


class ProductionVerificationBackend:
    """SARA backend for a real external verification provider."""

    provider_id = "SARA"

    def __init__(self, provider: Callable[[Mapping[str, Any]], Mapping[str, Any]]):
        self._provider = provider

    def __call__(self, request: Mapping[str, Any]) -> dict[str, Any]:
        claim = request["claim"]
        evidence = list(request.get("evidence", []))
        provider_result = dict(self._provider({
            "request_id": request["request_id"],
            "claim": claim,
            "evidence": evidence,
            "adapter_revision": request.get("adapter_revision", ""),
            "requested_at": request["requested_at"],
            "environment": request.get("environment", {}),
        }))

        status = provider_result.get("status", "FAILED")
        if status != "SUCCEEDED":
            return {
                "request_id": request["request_id"],
                "claim_id": claim["id"],
                "provider_id": self.provider_id,
                "status": status,
                "external_result_id": provider_result.get("external_result_id"),
                "external_result_provenance_ids": provider_result.get(
                    "external_result_provenance_ids", []
                ),
                "verification": {
                    "verification_status": "UNVERIFIED",
                    "verification_layer": "research_verification",
                    "findings": provider_result.get("findings", ()),
                    "uncertainty": "External provider did not complete successfully.",
                    "structural_validity": "VALID",
                    "truthfulness_status": "UNASSESSED",
                },
                "external_citation_verification": {"status": "NOT_COMPLETED"},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "environment": {
                    "backend": "production",
                    "live_external_research": True,
                },
                "failure": provider_result.get("failure"),
            }

        verification_status = provider_result.get("verification_status", "UNVERIFIED")
        result_id = provider_result.get("external_result_id")
        provenance_ids = tuple(provider_result.get("external_result_provenance_ids", ()))

        if not provenance_ids:
            fingerprint = sha256(
                f"{request['request_id']}|{claim['id']}|{result_id}".encode()
            ).hexdigest()
            provenance_ids = (f"SARA-PROV-{fingerprint[:16]}",)

        return {
            "request_id": request["request_id"],
            "claim_id": claim["id"],
            "provider_id": self.provider_id,
            "adapter_revision": request.get("adapter_revision", ""),
            "status": "SUCCEEDED",
            "external_result_id": result_id,
            "external_result_provenance_ids": list(provenance_ids),
            "verification": {
                "verification_status": verification_status,
                "verification_layer": "research_verification",
                "findings": tuple(provider_result.get("findings", ())),
                "uncertainty": provider_result.get(
                    "uncertainty",
                    "Provider-scoped verification only; truthfulness was not established.",
                ),
                "structural_validity": "VALID",
                "truthfulness_status": "UNASSESSED",
            },
            "reproduction_status": provider_result.get("reproduction_status"),
            "external_citation_verification": provider_result.get(
                "external_citation_verification",
                {"status": "NOT_COMPLETED"},
            ),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": {
                "backend": "production",
                "live_external_research": True,
            },
        }
