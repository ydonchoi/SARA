"""Callable SARA runtime with v2.4 epistemic and structured logical-audit boundaries.

Provider execution continues through the existing v2.3 execution contract, while
this entrypoint now runs the v2.4 epistemic adapter before provider invocation
and the v2.4 structural graph checker when an explicit argument graph is supplied.
It requires an injected provider rather than inventing an HTTP/SDK transport.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

ROOT = Path(__file__).resolve().parent / "SARA_v2.3"
V24_ROOT = Path(__file__).resolve().parent / "SARA_v2.4"
sys.path.insert(0, str(ROOT))
if str(V24_ROOT) not in sys.path:
    sys.path.insert(0, str(V24_ROOT))

from execution import (  # noqa: E402
    SARAExecutionRequest,
    SARAExecutionResponse,
    SARAExecutor,
)
from production_verification_backend import ProductionVerificationBackend  # noqa: E402
from co_thoughts_sara_adapter import CoThoughtsSARAAdapter  # noqa: E402
from logical_audit import (  # noqa: E402
    ArgumentEdge,
    ArgumentNode,
    validate_argument_graph,
)


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



@dataclass(frozen=True)
class SARAIntegratedExecutionResponse(SARAExecutionResponse):
    """Backward-compatible execution envelope with an additive v2.4 assessment."""

    sara_v24_assessment: dict[str, Any] | None = None


def _run_v24_assessment(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Run v2.4 epistemic checks and, when supplied, structured logical audit.

    The logical-audit checker does not parse free-form prose. If no explicit
    argument graph is supplied, that component remains NOT_RUN rather than
    implying that semantic reasoning has been evaluated.
    """
    claim = payload.get("claim") or {}
    premises = payload.get("premises") or []
    evidence = payload.get("evidence") or []
    provenance_ids = payload.get("provenance_ids") or []
    if not isinstance(claim, Mapping):
        raise ValueError("V24_CLAIM_MUST_BE_OBJECT")
    if not isinstance(premises, (list, tuple)) or any(
        not isinstance(item, Mapping) for item in premises
    ):
        raise ValueError("V24_PREMISES_MUST_BE_OBJECT_LIST")
    if not isinstance(evidence, (list, tuple)) or any(
        not isinstance(item, Mapping) for item in evidence
    ):
        raise ValueError("V24_EVIDENCE_MUST_BE_OBJECT_LIST")
    if not isinstance(provenance_ids, (list, tuple)) or any(
        not isinstance(item, str) or not item.strip() for item in provenance_ids
    ):
        raise ValueError("V24_PROVENANCE_IDS_MUST_BE_STRING_LIST")

    epistemic = CoThoughtsSARAAdapter().evaluate({
        "claim": dict(claim),
        "premises": [dict(item) for item in premises],
        "evidence": [dict(item) for item in evidence],
        "provenance_ids": list(provenance_ids),
    })
    graph = payload.get("argument_graph")
    if graph is None:
        logical_audit = {
            "audit_status": "NOT_RUN",
            "reason_code": "STRUCTURED_ARGUMENT_GRAPH_NOT_SUPPLIED",
            "semantic_audit_status": "NOT_PERFORMED",
            "is_evidence": False,
            "source": "SARA_LOGICAL_AUDIT",
        }
    elif not isinstance(graph, Mapping) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        logical_audit = {
            "audit_status": "INVALID_INPUT",
            "reason_code": "ARGUMENT_GRAPH_NODES_AND_EDGES_REQUIRED",
            "semantic_audit_status": "NOT_PERFORMED",
            "is_evidence": False,
            "source": "SARA_LOGICAL_AUDIT",
        }
    else:
        try:
            nodes = []
            for item in graph["nodes"]:
                if not isinstance(item, Mapping):
                    raise ValueError("ARGUMENT_GRAPH_NODE_MUST_BE_OBJECT")
                nodes.append(ArgumentNode(
                    node_id=item.get("node_id", ""),
                    node_type=item.get("node_type", ""),
                    text=item.get("text", ""),
                ))
            edges = []
            for item in graph["edges"]:
                if not isinstance(item, Mapping):
                    raise ValueError("ARGUMENT_GRAPH_EDGE_MUST_BE_OBJECT")
                edges.append(ArgumentEdge(
                    edge_id=item.get("edge_id", ""),
                    source_id=item.get("source_id", ""),
                    target_id=item.get("target_id", ""),
                    relation=item.get("relation", ""),
                    inference_type=item.get("inference_type", "UNKNOWN"),
                ))
            logical_audit = validate_argument_graph(nodes=nodes, edges=edges)
            logical_audit["audit_status"] = "STRUCTURE_CHECKED"
        except (TypeError, ValueError) as exc:
            logical_audit = {
                "audit_status": "INVALID_INPUT",
                "reason_code": str(exc) or type(exc).__name__,
                "semantic_audit_status": "NOT_PERFORMED",
                "is_evidence": False,
                "source": "SARA_LOGICAL_AUDIT",
            }

    return {
        "adapter_revision": CoThoughtsSARAAdapter.revision,
        "epistemic_assessment": epistemic,
        "logical_audit": logical_audit,
        "truthfulness_status": "UNASSESSED",
        "is_evidence": False,
    }


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
    # Execute the canonical v2.4 epistemic boundary before delegating to the
    # external verifier. A source-attribution contract violation is rejected
    # before the provider can return a seemingly supported result.
    v24_assessment = _run_v24_assessment(payload)
    backend = ProductionVerificationBackend(provider)
    executor = SARAExecutor(ProductionBackendAdapter(backend), request.adapter_revision)
    response = executor.verify_claim(request)
    return SARAIntegratedExecutionResponse(
        **asdict(response),
        sara_v24_assessment=v24_assessment,
    )



def process_dialogue_turn(
    payload: Mapping[str, Any],
    *,
    judgment_generate: Callable[[str, Mapping[str, Any], float], Mapping[str, Any]],
    verification_provider: Callable[[Mapping[str, Any]], Mapping[str, Any]],
    model_id: str,
    model_revision: str,
    adapter_revision: str = "sara-dialogue-runtime-v0.1",
    precheck: Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] | None = None,
    event_sink: Callable[[Mapping[str, Any]], Any] | None = None,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Run the SARA-internal JEV-style judgment/trigger path from a dialogue turn.

    This is the callable integration point for a host dialogue runtime. It
    requires explicit SARA model-generation and verification-provider callables;
    it does not silently configure an external JEV service or model SDK.
    """
    if not callable(verification_provider):
        raise ValueError("SARA_VERIFICATION_PROVIDER_REQUIRED")
    v25_root = Path(__file__).resolve().parent / "SARA_v2.5"
    if str(v25_root) not in sys.path:
        sys.path.insert(0, str(v25_root))
    from dialogue_runtime import SARADialogueRuntime

    def verify_claim_via_sara(request: Mapping[str, Any]) -> Mapping[str, Any]:
        response = execute_request(request, verification_provider)
        return asdict(response)

    runtime = SARADialogueRuntime(
        generate=judgment_generate,
        verify_claim=verify_claim_via_sara,
        model_id=model_id,
        model_revision=model_revision,
        adapter_revision=adapter_revision,
        precheck=precheck,
        event_sink=event_sink,
    )
    return runtime.process_turn(payload, timeout_seconds=timeout_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run SARA verification with v2.4 boundary checks and the injected provider facade.")
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
