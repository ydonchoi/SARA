"""Minimal independently callable SARA v2.3 runtime entrypoint.

The runtime exposes the already-validated execution contract as a CLI.
It deliberately requires an injected provider callable instead of inventing
an HTTP/SDK transport or a verification algorithm.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parent / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from execution import (  # noqa: E402
    SARAExecutionRequest,
    SARAExecutionResponse,
    SARAExecutor,
)
from production_verification_backend import ProductionVerificationBackend  # noqa: E402


class ProductionBackendAdapter:
    """Adapt the production backend's mapping result to SARA's execution contract."""

    def __init__(self, backend: ProductionVerificationBackend):
        self.backend = backend

    def verify(self, request: SARAExecutionRequest) -> SARAExecutionResponse:
        raw = self.backend(
            {
                "request_id": request.request_id,
                "claim": request.claim,
                "evidence": request.evidence,
                "adapter_revision": request.adapter_revision,
                "requested_at": request.requested_at,
                "environment": request.environment,
                "review_context": request.review_context,
            }
        )
        verification = raw.get("verification") or {}
        return SARAExecutionResponse(
            request_id=raw.get("request_id", request.request_id),
            claim_id=raw.get("claim_id", request.claim.get("id", "")),
            provider_id=raw.get("provider_id", "SARA"),
            adapter_revision=raw.get("adapter_revision", request.adapter_revision),
            status=raw.get("status", "FAILED"),
            external_result_id=raw.get("external_result_id"),
            external_result_provenance_ids=tuple(
                raw.get("external_result_provenance_ids", ())
            ),
            verification_status=verification.get(
                "verification_status", "UNVERIFIED"
            ),
            verification_layer=verification.get(
                "verification_layer", "research_verification"
            ),
            findings=tuple(verification.get("findings", ())),
            uncertainty=verification.get("uncertainty", ""),
            structural_validity=verification.get(
                "structural_validity", "UNASSESSED"
            ),
            truthfulness_status=verification.get(
                "truthfulness_status", "UNASSESSED"
            ),
            reproduction_status=raw.get("reproduction_status"),
            external_citation_verification=raw.get(
                "external_citation_verification"
            ),
            timestamp=raw.get("timestamp", ""),
            environment=raw.get("environment", {}),
            failure=raw.get("failure"),
        )


def load_provider(spec: str) -> Callable[[Mapping[str, Any]], Mapping[str, Any]]:
    """Load a provider callable from MODULE:ATTRIBUTE."""
    if ":" not in spec:
        raise ValueError("PROVIDER_SPEC_MUST_BE_MODULE_COLON_ATTRIBUTE")
    module_name, attribute_name = spec.split(":", 1)
    module = importlib.import_module(module_name)
    provider = getattr(module, attribute_name, None)
    if not callable(provider):
        raise ValueError("PROVIDER_ATTRIBUTE_NOT_CALLABLE")
    return provider


def execute_request(
    payload: Mapping[str, Any],
    provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> SARAExecutionResponse:
    """Execute one request through the production backend and SARA facade."""
    request = SARAExecutionRequest(
        request_id=str(payload.get("request_id", "")),
        capability=str(payload.get("capability", "")),
        claim=dict(payload.get("claim") or {}),
        evidence=tuple(payload.get("evidence") or ()),
        provenance_ids=tuple(payload.get("provenance_ids") or ()),
        adapter_revision=str(payload.get("adapter_revision", "")),
        requested_at=str(payload.get("requested_at", "")),
        environment=dict(payload.get("environment") or {}),
        review_context=payload.get("review_context"),
    )
    backend = ProductionVerificationBackend(provider)
    executor = SARAExecutor(ProductionBackendAdapter(backend), request.adapter_revision)
    return executor.verify_claim(request)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run one SARA v2.3 verification request.")
    parser.add_argument("--provider", required=True, help="Provider callable as MODULE:ATTRIBUTE")
    parser.add_argument(
        "--request",
        default="-",
        help="JSON request file; '-' reads JSON from stdin.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = sys.stdin.read() if args.request == "-" else Path(args.request).read_text(
            encoding="utf-8"
        )
        payload = json.loads(raw)
        result = execute_request(payload, load_provider(args.provider))
        print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "verification_status": "UNVERIFIED",
                    "truthfulness_status": "UNASSESSED",
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
