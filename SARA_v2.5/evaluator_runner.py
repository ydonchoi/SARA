"""SARA v2.5: callable evaluator adapter with fail-closed result handling.

The adapter invokes a supplied provider function. The provider function must
honour the passed timeout at its transport boundary; Python cannot forcibly
cancel an arbitrary running callable. Evaluator output remains decision support,
never research evidence or a claim-verification result.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from math import isfinite
from typing import Any

from evaluator_boundary import EvaluatorSignal, validate_evaluator_signal

ProviderCallable = Callable[[Mapping[str, Any], float], Mapping[str, Any]]


class EvaluatorInvocationError(ValueError):
    """Raised for an invalid invocation request, before the provider is called."""


class EvaluatorRunner:
    """Invoke a configured evaluator and normalize success/failure into one envelope."""

    def __init__(
        self,
        invoke: ProviderCallable,
        *,
        evaluator_id: str,
        evaluator_revision: str,
        rubric_revision: str,
        runner_revision: str = "sara-evaluator-runner-v0.1",
    ) -> None:
        if not callable(invoke):
            raise EvaluatorInvocationError("PROVIDER_CALLABLE_REQUIRED")
        for value, error in (
            (evaluator_id, "EVALUATOR_ID_REQUIRED"),
            (evaluator_revision, "EVALUATOR_REVISION_REQUIRED"),
            (rubric_revision, "EVALUATOR_RUBRIC_REVISION_REQUIRED"),
            (runner_revision, "EVALUATOR_RUNNER_REVISION_REQUIRED"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise EvaluatorInvocationError(error)
        self._invoke = invoke
        self.evaluator_id = evaluator_id
        self.evaluator_revision = evaluator_revision
        self.rubric_revision = rubric_revision
        self.runner_revision = runner_revision

    def run(
        self,
        request: Mapping[str, Any],
        *,
        timeout_seconds: float,
        known_node_ids: tuple[str, ...] = (),
        known_evidence_ids: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """Call the provider once and return a boundary-checked envelope."""
        if not isinstance(request, Mapping):
            raise EvaluatorInvocationError("EVALUATOR_REQUEST_MUST_BE_MAPPING")
        for key, error in (
            ("request_id", "EVALUATOR_REQUEST_ID_REQUIRED"),
            ("claim_id", "EVALUATOR_CLAIM_ID_REQUIRED"),
            ("claim_revision_id", "EVALUATOR_CLAIM_REVISION_ID_REQUIRED"),
            ("claim_text", "EVALUATOR_CLAIM_TEXT_REQUIRED"),
            ("input_revision_digest", "EVALUATOR_INPUT_DIGEST_REQUIRED"),
        ):
            value = request.get(key)
            if not isinstance(value, str) or not value.strip():
                raise EvaluatorInvocationError(error)
        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise EvaluatorInvocationError("INVALID_EVALUATOR_TIMEOUT")

        request_id = request["request_id"]
        claim_id = request["claim_id"]
        revision_id = request["claim_revision_id"]
        input_digest = request["input_revision_digest"]
        operational_provenance_id = f"EVALUATOR-RUN:{request_id}"
        provider_request = {
            "request_id": request_id,
            "claim_id": claim_id,
            "claim_revision_id": revision_id,
            "claim_text": request["claim_text"],
            "scope": request.get("scope", {}),
            "premises": request.get("premises", []),
            "evidence": request.get("evidence", []),
            "input_revision_digest": input_digest,
            "rubric_revision": self.rubric_revision,
            "timeout_seconds": float(timeout_seconds),
            "provenance_ids": list(request.get("provenance_ids") or []),
        }

        try:
            raw = self._invoke(provider_request, float(timeout_seconds))
        except TimeoutError:
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "TIMEOUT", "EVALUATOR_PROVIDER_TIMEOUT", operational_provenance_id,
            )
        except Exception as exc:
            # Do not propagate provider text or exception details into a claim finding.
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "FAILED", f"EVALUATOR_PROVIDER_EXCEPTION:{type(exc).__name__}",
                operational_provenance_id,
            )

        if not isinstance(raw, Mapping):
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "INVALID_OUTPUT", "EVALUATOR_OUTPUT_NOT_OBJECT", operational_provenance_id,
            )

        required_response_keys = (
            "claim_id", "claim_revision_id", "input_revision_digest", "signal_status"
        )
        missing = [key for key in required_response_keys if key not in raw]
        if missing:
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "INCOMPLETE", "EVALUATOR_OUTPUT_MISSING_REQUIRED_FIELDS",
                operational_provenance_id,
            )

        if (
            raw.get("claim_id") != claim_id
            or raw.get("claim_revision_id") != revision_id
            or raw.get("input_revision_digest") != input_digest
        ):
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "INVALID_OUTPUT", "EVALUATOR_OUTPUT_IDENTITY_MISMATCH",
                operational_provenance_id,
            )

        def tuple_field(name: str) -> tuple[str, ...] | None:
            value = raw.get(name, ())
            if not isinstance(value, (list, tuple)) or any(
                not isinstance(item, str) or not item.strip() for item in value
            ):
                return None
            return tuple(value)

        related_node_ids = tuple_field("related_node_ids")
        evidence_ids = tuple_field("evidence_ids")
        provider_provenance_ids = tuple_field("provenance_ids")
        if (
            related_node_ids is None
            or evidence_ids is None
            or provider_provenance_ids is None
            or not isinstance(raw.get("rationale", ""), str)
        ):
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "INVALID_OUTPUT", "EVALUATOR_OUTPUT_FIELD_TYPE_INVALID",
                operational_provenance_id,
            )

        provenance_ids = tuple(dict.fromkeys(
            provider_provenance_ids + (operational_provenance_id,)
        ))
        signal = EvaluatorSignal(
            signal_id=f"EV:{request_id}",
            evaluator_id=self.evaluator_id,
            evaluator_revision=self.evaluator_revision,
            rubric_revision=self.rubric_revision,
            input_revision_digest=input_digest,
            execution_status="SUCCEEDED",
            signal_status=raw["signal_status"],
            rationale=raw.get("rationale", ""),
            related_node_ids=related_node_ids,
            evidence_ids=evidence_ids,
            provenance_ids=provenance_ids,
        )
        try:
            validated = validate_evaluator_signal(
                signal,
                expected_input_revision_digest=input_digest,
                known_node_ids=known_node_ids,
                known_evidence_ids=known_evidence_ids,
            )
        except (TypeError, ValueError) as exc:
            return self._failure(
                request_id, claim_id, revision_id, input_digest,
                "INVALID_OUTPUT", f"EVALUATOR_BOUNDARY_REJECTED:{str(exc)}",
                operational_provenance_id,
            )

        return {
            "request_id": request_id,
            "claim_id": claim_id,
            "claim_revision_id": revision_id,
            "runner_revision": self.runner_revision,
            "execution_status": "SUCCEEDED",
            "failure_code": None,
            "signal": validated,
            "review_required": validated["review_required"],
            "commit_status": "NOT_COMMITTED",
            "is_evidence": False,
            "source": "SARA_EVALUATOR_RUNNER",
        }

    @staticmethod
    def _failure(
        request_id: str,
        claim_id: str,
        revision_id: str,
        input_digest: str,
        execution_status: str,
        failure_code: str,
        operational_provenance_id: str,
    ) -> dict[str, Any]:
        return {
            "request_id": request_id,
            "claim_id": claim_id,
            "claim_revision_id": revision_id,
            "input_revision_digest": input_digest,
            "execution_status": execution_status,
            "failure_code": failure_code,
            "signal": {
                "signal_id": f"EV:{request_id}",
                "evaluator_id": None,
                "execution_status": execution_status,
                "signal_status": "NOT_AVAILABLE",
                "provenance_ids": [operational_provenance_id],
                "review_required": True,
                "source": "SARA_EVALUATOR_SIGNAL",
                "is_evidence": False,
            },
            "review_required": True,
            "commit_status": "NOT_COMMITTED",
            "is_evidence": False,
            "source": "SARA_EVALUATOR_RUNNER",
        }
