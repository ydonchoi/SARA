"""SARA v2.3 external execution facade.

The facade validates the external execution contract and delegates actual
research verification to an injected backend. It intentionally does not
invent a verification algorithm.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class SARAExecutionRequest:
    request_id: str
    capability: str
    claim: dict[str, Any]
    evidence: tuple[dict[str, Any], ...]
    provenance_ids: tuple[str, ...]
    adapter_revision: str
    requested_at: str
    environment: dict[str, Any]


@dataclass(frozen=True)
class SARAExecutionResponse:
    request_id: str
    claim_id: str
    provider_id: str
    adapter_revision: str
    status: str
    external_result_id: str | None
    external_result_provenance_ids: tuple[str, ...]
    verification_status: str
    verification_layer: str
    findings: tuple[str, ...]
    uncertainty: str
    structural_validity: str
    truthfulness_status: str
    reproduction_status: str | None
    external_citation_verification: dict[str, Any] | None
    timestamp: str
    environment: dict[str, Any]
    failure: dict[str, Any] | None = None


class VerificationBackend(Protocol):
    def verify(self, request: SARAExecutionRequest) -> SARAExecutionResponse:
        ...


class SARAExecutionError(ValueError):
    """Raised when an external execution request violates the contract."""


class SARAExecutor:
    """Callable SARA boundary; verification is delegated to an injected backend."""

    provider_id = "SARA"

    def __init__(self, backend: VerificationBackend, adapter_revision: str):
        self.backend = backend
        self.adapter_revision = adapter_revision

    def verify_claim(self, request: SARAExecutionRequest) -> SARAExecutionResponse:
        self._validate_request(request)
        response = self.backend.verify(request)
        self._validate_response(request, response)
        return response

    def _validate_request(self, request: SARAExecutionRequest) -> None:
        if not request.request_id:
            raise SARAExecutionError("request_id is required")
        if request.capability != "verify_claim":
            raise SARAExecutionError("unsupported capability")
        if not request.claim.get("id") or not request.claim.get("text"):
            raise SARAExecutionError("claim id and text are required")
        inference_level = request.claim.get("inference_level")
        if inference_level is not None and inference_level not in {"FACT", "INFERENCE", "HYPOTHESIS", "SPECULATION"}:
            raise SARAExecutionError("invalid inference level")
        if inference_level != "FACT" and inference_level is not None:
            if not request.claim.get("inference_basis"):
                raise SARAExecutionError("inference_basis is required for non-FACT claims")
        if not request.adapter_revision:
            raise SARAExecutionError("adapter_revision is required")

        blocked_evidence_types = {
            "simulated_reproduction",
            "cognitive_execution",
            "agent_execution",
        }
        evidence_ids = request.claim.get("evidence_ids")
        if evidence_ids is not None:
            if not isinstance(evidence_ids, (list, tuple)):
                raise SARAExecutionError("claim evidence_ids must be a list")
            available_evidence_ids = {
                evidence.get("id")
                for evidence in request.evidence
                if isinstance(evidence, dict) and evidence.get("id")
            }
            if any(evidence_id not in available_evidence_ids for evidence_id in evidence_ids):
                raise SARAExecutionError("claim references missing evidence")
        
        for evidence in request.evidence:
            if not isinstance(evidence, dict):
                raise SARAExecutionError("evidence must be an object")
            evidence_type = evidence.get("evidence_type")
            if evidence_type in blocked_evidence_types:
                raise SARAExecutionError(
                    "execution-derived evidence cannot be used for research verification"
                )
            if evidence.get("verification_layer", "research_verification") != "research_verification":
                raise SARAExecutionError("invalid evidence verification layer")
            supports_claims = evidence.get("supports_claims")
            if supports_claims is not None:
                if not isinstance(supports_claims, (list, tuple)):
                    raise SARAExecutionError("evidence supports_claims must be a list")
                if request.claim.get("id") not in supports_claims:
                    raise SARAExecutionError("evidence is not bound to the requested claim")

    def _validate_response(
        self, request: SARAExecutionRequest, response: SARAExecutionResponse
    ) -> None:
        if response.request_id != request.request_id:
            raise SARAExecutionError("request identity mismatch")
        if response.claim_id != request.claim.get("id"):
            raise SARAExecutionError("claim identity mismatch")
        if response.provider_id != self.provider_id:
            raise SARAExecutionError("provider identity mismatch")
        if response.verification_layer != "research_verification":
            raise SARAExecutionError("invalid verification layer")
        if response.status not in {"SUCCEEDED", "FAILED", "REJECTED"}:
            raise SARAExecutionError("invalid execution status")
        if response.verification_status not in {
            "VERIFIED",
            "PARTIALLY VERIFIED",
            "INFERRED",
            "HYPOTHESIZED",
            "UNVERIFIED",
            "CONTRADICTED",
        }:
            raise SARAExecutionError("invalid verification status")
        if response.truthfulness_status not in {"UNASSESSED", "ESTABLISHED"}:
            raise SARAExecutionError("invalid truthfulness status")
        citation = response.external_citation_verification
        if citation is not None:
            if not isinstance(citation, dict) or citation.get("status") not in {
                "VERIFIED",
                "PARTIALLY VERIFIED",
                "UNVERIFIED",
                "CONTRADICTED",
                "NOT_COMPLETED",
            }:
                raise SARAExecutionError("invalid external citation verification status")
        if response.truthfulness_status == "ESTABLISHED":
            if not isinstance(citation, dict) or citation.get("status") != "VERIFIED":
                raise SARAExecutionError(
                    "established truthfulness requires verified external citation verification"
                )
        if response.status == "SUCCEEDED" and not response.external_result_provenance_ids:
            raise SARAExecutionError(
                "successful consequential result requires external provenance"
            )
        if set(response.external_result_provenance_ids) & set(request.provenance_ids):
            raise SARAExecutionError(
                "request provenance cannot be reused as external result provenance"
            )
        if response.verification_status == "VERIFIED" and not response.external_result_provenance_ids:
            raise SARAExecutionError("verified result requires external provenance")
        if response.reproduction_status == "SIMULATED_REPRODUCTION" and response.verification_status == "VERIFIED":
            raise SARAExecutionError(
                "simulated reproduction cannot establish verification"
            )
