"""Callable SARA v2.5 dialogue-turn integration for JEV-style inference judgment.

This module connects the internal judgment contract to SARA's existing claim
verification facade through explicit callables. It does not configure a model
SDK, claim a live deployment is installed, or treat a judgment as evidence.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from math import isfinite
from typing import Any

from inference_pipeline import SARAInferencePipeline
from internal_judgment_model import SARAInternalJudgmentModel
from external_evidence import ExternalEvidenceError, collect_external_evidence

VerifyClaimCallable = Callable[[Mapping[str, Any]], Mapping[str, Any]]
PrecheckCallable = Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]
EventSinkCallable = Callable[[Mapping[str, Any]], Any]
ExternalSearchCallable = Callable[[Mapping[str, Any], float], list[Mapping[str, Any]]]


class DialogueRuntimeError(ValueError):
    """Raised when the dialogue-turn request or runtime is misconfigured."""


class SARADialogueRuntime:
    """Judge a dialogue turn, trigger SARA, verify selected claims, and report state.

    The host must inject its actual SARA model-generation callable and claim
    verification facade. Candidate claims are explicit inputs: this component
    will not invent a verification target when the judgment returns no bound
    candidate ID. Missing/ambiguous targets go to precheck instead.
    """

    def __init__(
        self,
        *,
        generate: Callable[[str, Mapping[str, Any], float], Mapping[str, Any]],
        verify_claim: VerifyClaimCallable,
        model_id: str,
        model_revision: str,
        adapter_revision: str = "sara-dialogue-runtime-v0.2",
        precheck: PrecheckCallable | None = None,
        event_sink: EventSinkCallable | None = None,
        search_external_sources: ExternalSearchCallable | None = None,
        external_search_timeout_seconds: float = 8.0,
    ) -> None:
        if not callable(verify_claim):
            raise DialogueRuntimeError("SARA_VERIFY_CLAIM_CALLABLE_REQUIRED")
        if not isinstance(adapter_revision, str) or not adapter_revision.strip():
            raise DialogueRuntimeError("SARA_DIALOGUE_ADAPTER_REVISION_REQUIRED")
        if isinstance(external_search_timeout_seconds, bool) or not isinstance(external_search_timeout_seconds, (int, float)) or not isfinite(external_search_timeout_seconds) or external_search_timeout_seconds <= 0:
            raise DialogueRuntimeError("SARA_EXTERNAL_SEARCH_TIMEOUT_MUST_BE_POSITIVE")
        if search_external_sources is not None and not callable(search_external_sources):
            raise DialogueRuntimeError("SARA_EXTERNAL_SEARCH_CALLABLE_INVALID")
        self._verify_claim = verify_claim
        self._precheck = precheck or self._default_precheck
        self._event_sink = event_sink
        self._search_external_sources = search_external_sources
        self._external_search_timeout_seconds = float(external_search_timeout_seconds)
        self.adapter_revision = adapter_revision
        judgment_model = SARAInternalJudgmentModel(
            generate, model_id=model_id, model_revision=model_revision
        )
        self._pipeline = SARAInferencePipeline(
            judgment_model,
            run_selective_verification=self._verify_selected_claims,
            run_precheck=self._run_precheck,
            pipeline_revision="sara-dialogue-inference-pipeline-v0.2",
        )

    @staticmethod
    def _default_precheck(
        request: Mapping[str, Any],
        judgment: Mapping[str, Any],
        decision: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        """Fail safely into an explicit review queue when no host queue is wired."""
        return {
            "status": "NEEDS_REVIEW",
            "reason_code": decision.get("reason_code", "PRECHECK_REQUIRED"),
            "request_id": request.get("request_id"),
            "input_revision_digest": judgment.get("input_revision_digest"),
            "automatic_verification_not_started": True,
        }

    def process_turn(
        self, request: Mapping[str, Any], *, timeout_seconds: float = 15.0
    ) -> dict[str, Any]:
        """Process one dialogue turn and return judgment, routing, and verifier output."""
        if not isinstance(request, Mapping):
            raise DialogueRuntimeError("DIALOGUE_TURN_REQUEST_MUST_BE_MAPPING")
        required = ("request_id", "conversation_id", "turn_id", "content")
        normalized = dict(request)
        for field in required:
            value = normalized.get(field)
            if not isinstance(value, str) or not value.strip():
                raise DialogueRuntimeError(f"DIALOGUE_TURN_{field.upper()}_REQUIRED")

        candidates = normalized.get("claim_candidates", [])
        if not isinstance(candidates, list):
            raise DialogueRuntimeError("DIALOGUE_TURN_CLAIM_CANDIDATES_MUST_BE_LIST")
        candidate_by_id: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            if not isinstance(candidate, Mapping):
                raise DialogueRuntimeError("DIALOGUE_TURN_CLAIM_CANDIDATE_MUST_BE_MAPPING")
            candidate_id, text = candidate.get("id"), candidate.get("text")
            if not isinstance(candidate_id, str) or not candidate_id.strip():
                raise DialogueRuntimeError("DIALOGUE_TURN_CLAIM_CANDIDATE_ID_REQUIRED")
            if not isinstance(text, str) or not text.strip():
                raise DialogueRuntimeError("DIALOGUE_TURN_CLAIM_CANDIDATE_TEXT_REQUIRED")
            if candidate_id in candidate_by_id:
                raise DialogueRuntimeError("DIALOGUE_TURN_DUPLICATE_CLAIM_CANDIDATE_ID")
            candidate_by_id[candidate_id] = dict(candidate)

        # Claim IDs and their text participate in the judgment input digest.
        # Therefore a modified candidate cannot reuse a judgment for prior text.
        catalog = normalized.get("reference_catalog", {})
        if not isinstance(catalog, Mapping):
            raise DialogueRuntimeError("DIALOGUE_TURN_REFERENCE_CATALOG_INVALID")
        catalog = dict(catalog)
        known_claim_refs = catalog.get("claim_refs", [])
        if (
            not isinstance(known_claim_refs, list)
            or any(not isinstance(value, str) or not value.strip() for value in known_claim_refs)
        ):
            raise DialogueRuntimeError("DIALOGUE_TURN_CLAIM_REFERENCE_LIST_INVALID")
        catalog["claim_refs"] = list(dict.fromkeys(
            [*known_claim_refs, *candidate_by_id.keys()]
        ))
        normalized["reference_catalog"] = catalog
        normalized["claim_candidates"] = list(candidate_by_id.values())

        result = self._pipeline.process(normalized, timeout_seconds=timeout_seconds)
        route_output = result.get("route_execution", {}).get("output")
        verification_results = (
            route_output.get("verification_results", [])
            if isinstance(route_output, Mapping) else []
        )
        result.update({
            "runtime_revision": self.adapter_revision,
            "conversation_id": normalized["conversation_id"],
            "turn_id": normalized["turn_id"],
            "verification_provider_invoked": any(
                isinstance(item, Mapping) and item.get("execution_status") == "SUCCEEDED"
                for item in verification_results
            ),
            "external_search_invoked": any(
                isinstance(item, Mapping) and item.get("external_search_status") in {"COLLECTED", "NO_RESULTS"}
                for item in verification_results
            ),
            "external_search_provider_configured": self._search_external_sources is not None,
            "verification_status_is_not_truthfulness": True,
            "audit_record_status": "NOT_CONFIGURED",
        })
        # Event sinks are optional and caller-managed. Failure is visible; it is
        # never silently reported as a durable audit record.
        if self._event_sink is not None:
            event = {
                "event_type": "SARA_DIALOGUE_TURN_PROCESSED",
                "request_id": normalized["request_id"],
                "conversation_id": normalized["conversation_id"],
                "turn_id": normalized["turn_id"],
                "input_revision_digest": result.get("input_revision_digest"),
                "judgment_status": result.get("judgment", {}).get("judgment_status"),
                "activation_decision": result.get("activation_decision", {}).get("activation_action"),
                "route_execution_status": result.get("route_execution", {}).get("execution_status"),
                "runtime_revision": self.adapter_revision,
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "is_evidence": False,
            }
            try:
                self._event_sink(event)
                result["audit_record_status"] = "RECORDED_BY_CONFIGURED_EVENT_SINK"
            except Exception as exc:
                result["audit_record_status"] = "FAILED"
                result["audit_record_error_type"] = type(exc).__name__
        return result

    def _run_precheck(
        self,
        request: Mapping[str, Any],
        judgment: Mapping[str, Any],
        decision: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        result = self._precheck(request, judgment, decision)
        if not isinstance(result, Mapping):
            raise DialogueRuntimeError("SARA_PRECHECK_OUTPUT_MUST_BE_MAPPING")
        return dict(result)

    def _verify_selected_claims(
        self,
        request: Mapping[str, Any],
        judgment: Mapping[str, Any],
        decision: Mapping[str, Any],
    ) -> Mapping[str, Any]:
        candidate_by_id = {
            item["id"]: item for item in request.get("claim_candidates", [])
            if isinstance(item, Mapping) and isinstance(item.get("id"), str)
        }
        selected_ids = judgment.get("claim_refs", [])
        if not isinstance(selected_ids, list) or not selected_ids:
            return self._run_precheck(
                request, judgment,
                {**dict(decision), "reason_code": "VERIFICATION_HAS_NO_BOUND_CLAIM_CANDIDATE"},
            )
        if any(candidate_id not in candidate_by_id for candidate_id in selected_ids):
            return self._run_precheck(
                request, judgment,
                {**dict(decision), "reason_code": "INFERENCE_CLAIM_CANDIDATE_BINDING_MISMATCH"},
            )

        evidence = request.get("evidence", [])
        if not isinstance(evidence, list) or any(not isinstance(item, Mapping) for item in evidence):
            return self._run_precheck(
                request, judgment,
                {**dict(decision), "reason_code": "INFERENCE_EVIDENCE_INPUT_INVALID"},
            )
        results = []
        for claim_id in selected_ids:
            candidate = candidate_by_id[claim_id]
            claim = dict(candidate)
            claim["inference_level"] = (
                "INFERENCE" if judgment.get("judgment_status") == "INFERENCE_PRESENT"
                else "ASSERTED_OR_ATTRIBUTED_CLAIM"
            )
            claim["verification_need"] = judgment.get("verification_need")
            claim["external_check_need"] = judgment.get("external_check_need")
            claim["inference_basis"] = list(judgment.get("basis_spans", []))
            verify_request = {
                "request_id": f"{request['request_id']}:{claim_id}",
                "capability": "verify_claim",
                "claim": claim,
                "evidence": [dict(item) for item in evidence],
                # A structured graph supplied with a candidate is passed to
                # v2.4's deterministic checker; free-form text is not parsed
                # into a graph by assumption.
                "argument_graph": candidate.get("argument_graph"),
                "provenance_ids": list(request.get("provenance_ids", [])),
                "adapter_revision": str(request.get("adapter_revision", self.adapter_revision)),
                "requested_at": str(request.get("requested_at") or datetime.now(timezone.utc).isoformat()),
                "environment": dict(request.get("environment") or {}),
                "review_context": {
                    "source": "SARA_INTERNAL_JEV_STYLE_JUDGMENT",
                    "judgment_input_digest": judgment.get("input_revision_digest"),
                    "trigger_policy_revision": decision.get("policy_revision"),
                    "inference_types": list(judgment.get("inference_types", [])),
                    "inference_basis_spans": list(judgment.get("basis_spans", [])),
                    "verification_need": judgment.get("verification_need"),
                    "external_check_need": judgment.get("external_check_need"),
                },
            }
            if judgment.get("external_check_need") == "REQUIRED":
                if self._search_external_sources is None:
                    results.append({
                        "claim_id": claim_id,
                        "execution_status": "BLOCKED",
                        "external_search_status": "NOT_CONFIGURED",
                        "verification_status": "UNVERIFIED",
                        "error_code": "EXTERNAL_SEARCH_PROVIDER_NOT_CONFIGURED",
                    })
                    continue
                try:
                    external = collect_external_evidence(
                        self._search_external_sources,
                        claim=claim,
                        context={
                            "conversation_id": request.get("conversation_id"),
                            "turn_id": request.get("turn_id"),
                            "input_revision_digest": judgment.get("input_revision_digest"),
                            "dialogue_context": request.get("context", {}),
                        },
                        timeout_seconds=self._external_search_timeout_seconds,
                        max_results=5,
                    )
                except ExternalEvidenceError as exc:
                    results.append({
                        "claim_id": claim_id,
                        "execution_status": "FAILED",
                        "external_search_status": "FAILED",
                        "verification_status": "UNVERIFIED",
                        "error_code": str(exc),
                    })
                    continue
                if external["status"] == "NO_RESULTS":
                    results.append({
                        "claim_id": claim_id,
                        "execution_status": "NO_EVIDENCE",
                        "external_search_status": "NO_RESULTS",
                        "verification_status": "UNVERIFIED",
                        "external_evidence_count": 0,
                        "error_code": "NO_EXTERNAL_EVIDENCE_FOUND",
                    })
                    continue
                verify_request["evidence"] = [
                    *verify_request["evidence"],
                    *external["results"],
                ]
                verify_request["review_context"]["external_search"] = {
                    "status": external["status"],
                    "result_count": external["result_count"],
                    "external_evidence_ids": [item["id"] for item in external["results"]],
                    "source_candidates_are_not_verified": True,
                }
            try:
                raw = self._verify_claim(verify_request)
                if not isinstance(raw, Mapping):
                    results.append({
                        "claim_id": claim_id,
                        "execution_status": "INVALID_OUTPUT",
                        "error_code": "SARA_VERIFY_CLAIM_OUTPUT_MUST_BE_MAPPING",
                    })
                    continue
                results.append({
                    "claim_id": claim_id,
                    "execution_status": "SUCCEEDED",
                    "output": dict(raw),
                    "external_search_status": (
                        "COLLECTED" if judgment.get("external_check_need") == "REQUIRED"
                        and self._search_external_sources is not None else "NOT_REQUIRED"
                    ),
                    "external_evidence_count": len(verify_request.get("evidence", [])) - len(evidence),
                    "output_is_research_evidence": False,
                })
            except Exception as exc:
                results.append({
                    "claim_id": claim_id,
                    "execution_status": "FAILED",
                    "error_code": type(exc).__name__,
                })
        failed = any(item["execution_status"] != "SUCCEEDED" for item in results)
        return {
            "status": "PARTIALLY_FAILED" if failed else "ROUTE_EXECUTED",
            "verification_results": results,
            "verification_results_are_proposals_or_verifier_outputs": True,
            "claim_truth_assessed": False,
            "is_evidence": False,
        }
