"""Orchestrate SARA's internal inference judgment and verification route.

The callbacks are integration contracts for the host SARA runtime. Tests use
controlled doubles; production deployment must bind real SARA callbacks and
verify that this path is called from the live dialogue loop.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from inference_trigger import decide_sara_activation
from internal_judgment_model import (
    SARAInternalJudgmentModel,
    compute_judgment_input_digest,
)

VerificationCallable = Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]
PrecheckCallable = Callable[[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]


class InferencePipelineError(ValueError):
    """Raised when the orchestration contract is not configured correctly."""


class SARAInferencePipeline:
    """Run judgment, activation policy, then the appropriate SARA callback."""

    def __init__(
        self,
        judgment_model: SARAInternalJudgmentModel,
        *,
        run_selective_verification: VerificationCallable,
        run_precheck: PrecheckCallable,
        pipeline_revision: str = "sara-inference-pipeline-v0.2",
    ) -> None:
        if not isinstance(judgment_model, SARAInternalJudgmentModel):
            raise InferencePipelineError("SARA_INTERNAL_JUDGMENT_MODEL_REQUIRED")
        if not callable(run_selective_verification):
            raise InferencePipelineError("SARA_SELECTIVE_VERIFICATION_CALLBACK_REQUIRED")
        if not callable(run_precheck):
            raise InferencePipelineError("SARA_PRECHECK_CALLBACK_REQUIRED")
        if not isinstance(pipeline_revision, str) or not pipeline_revision.strip():
            raise InferencePipelineError("SARA_INFERENCE_PIPELINE_REVISION_REQUIRED")
        self._judgment_model = judgment_model
        self._run_selective_verification = run_selective_verification
        self._run_precheck = run_precheck
        self.pipeline_revision = pipeline_revision

    def process(
        self, request: Mapping[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        """Execute inference judgment and route its decision; never assert truth."""
        digest = compute_judgment_input_digest(request)
        judgment = self._judgment_model.judge(
            request, timeout_seconds=timeout_seconds
        )
        decision = decide_sara_activation(
            judgment, expected_input_revision_digest=digest
        )

        execution: dict[str, Any] = {
            "route": decision["activation_action"],
            "execution_status": "NOT_REQUIRED",
            "output": None,
            "error_code": None,
        }
        callback = None
        if decision["activation_action"] == "SARA_SELECTIVE_VERIFICATION":
            callback = self._run_selective_verification
        elif decision["activation_action"] == "SARA_PRECHECK_REVIEW":
            callback = self._run_precheck

        if callback is not None:
            try:
                output = callback(request, judgment, decision)
                if not isinstance(output, Mapping):
                    execution["execution_status"] = "INVALID_OUTPUT"
                    execution["error_code"] = "SARA_ROUTE_OUTPUT_MUST_BE_MAPPING"
                else:
                    execution["execution_status"] = "SUCCEEDED"
                    execution["output"] = dict(output)
            except Exception as exc:
                # Store exception type only; do not expose potentially sensitive
                # exception messages or recast failure as a verification verdict.
                execution["execution_status"] = "FAILED"
                execution["error_code"] = type(exc).__name__

        return {
            "pipeline_revision": self.pipeline_revision,
            "request_id": request.get("request_id"),
            "input_revision_digest": digest,
            "judgment": judgment,
            "activation_decision": decision,
            "route_execution": execution,
            "pipeline_status": (
                "ROUTE_EXECUTED"
                if execution["execution_status"] == "SUCCEEDED"
                else "ROUTE_NOT_COMPLETED"
                if execution["execution_status"] in {"FAILED", "INVALID_OUTPUT"}
                else "NO_ROUTE_REQUIRED"
            ),
            "is_evidence": False,
            "claim_truth_assessed": False,
            "verification_result_is_callback_owned": True,
        }
