"""Executable JSONL host for SARA v2.5's callable dialogue runtime.

This is a host-neutral execution adapter, not a deployed ChatGPT integration.
A provider module must explicitly supply real model-generation and claim-
verification callables. No provider, model, credentials, or network transport is
fabricated by this module.

Provider contract:
    MODEL_ID: str
    MODEL_REVISION: str
    generate(system_prompt, payload, timeout_seconds) -> Mapping
    verify_claim(request) -> Mapping
Optional:
    precheck(request, judgment, decision) -> Mapping
    event_sink(event) -> Any

Run:
    python SARA_v2.5/executor.py --provider package.module
Input is one JSON request per line on stdin; output is one JSON result per line.
"""
from __future__ import annotations

import argparse
import importlib
import json
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

# The v2.5 modules currently use same-directory absolute imports.
_V25_DIR = str(Path(__file__).resolve().parent)
if _V25_DIR not in sys.path:
    sys.path.insert(0, _V25_DIR)

from dialogue_runtime import DialogueRuntimeError, SARADialogueRuntime  # noqa: E402


class ExecutorConfigurationError(ValueError):
    """Raised when a provider module does not satisfy the explicit contract."""


def build_runtime(provider_module: str) -> SARADialogueRuntime:
    """Load explicit host callables and construct the dialogue runtime."""
    if not isinstance(provider_module, str) or not provider_module.strip():
        raise ExecutorConfigurationError("SARA_PROVIDER_MODULE_REQUIRED")
    try:
        provider = importlib.import_module(provider_module)
    except Exception as exc:
        raise ExecutorConfigurationError(
            f"SARA_PROVIDER_IMPORT_FAILED:{type(exc).__name__}"
        ) from exc

    model_id = getattr(provider, "MODEL_ID", None)
    model_revision = getattr(provider, "MODEL_REVISION", None)
    generate = getattr(provider, "generate", None)
    verify_claim = getattr(provider, "verify_claim", None)
    if not isinstance(model_id, str) or not model_id.strip():
        raise ExecutorConfigurationError("SARA_PROVIDER_MODEL_ID_REQUIRED")
    if not isinstance(model_revision, str) or not model_revision.strip():
        raise ExecutorConfigurationError("SARA_PROVIDER_MODEL_REVISION_REQUIRED")
    if not callable(generate):
        raise ExecutorConfigurationError("SARA_PROVIDER_GENERATE_CALLABLE_REQUIRED")
    if not callable(verify_claim):
        raise ExecutorConfigurationError("SARA_PROVIDER_VERIFY_CLAIM_CALLABLE_REQUIRED")

    precheck = getattr(provider, "precheck", None)
    event_sink = getattr(provider, "event_sink", None)
    if precheck is not None and not callable(precheck):
        raise ExecutorConfigurationError("SARA_PROVIDER_PRECHECK_MUST_BE_CALLABLE")
    if event_sink is not None and not callable(event_sink):
        raise ExecutorConfigurationError("SARA_PROVIDER_EVENT_SINK_MUST_BE_CALLABLE")

    return SARADialogueRuntime(
        generate=generate,
        verify_claim=verify_claim,
        model_id=model_id,
        model_revision=model_revision,
        precheck=precheck,
        event_sink=event_sink,
        adapter_revision="sara-v25-executor-cli-v0.2",
    )


def _aggregate_verification_status(route_output: Any) -> str | None:
    """Read provider statuses from either the route envelope or per-claim results.

    The dialogue runtime nests actual verifier responses under
    verification_results[*].output. Ignoring that structure can make an
    UNVERIFIED result look like an ordinary completed route.
    """
    if not isinstance(route_output, Mapping):
        return None

    top_level = route_output.get("verification_status")
    results = route_output.get("verification_results")
    if not isinstance(results, list) or not results:
        return top_level if isinstance(top_level, str) and top_level.strip() else None

    statuses: list[str] = []
    if isinstance(top_level, str) and top_level.strip():
        statuses.append(top_level)
    for item in results:
        if not isinstance(item, Mapping):
            continue
        if item.get("execution_status") != "SUCCEEDED":
            statuses.append("UNVERIFIED")
            continue
        output = item.get("output")
        status = output.get("verification_status") if isinstance(output, Mapping) else None
        if not isinstance(status, str) or not status.strip():
            statuses.append("UNSPECIFIED")
        else:
            statuses.append(status)

    if not statuses:
        return None
    unique = set(statuses)
    return statuses[0] if len(unique) == 1 else "MIXED"


def execute_request(runtime: SARADialogueRuntime, request: Any, timeout_seconds: float) -> dict[str, Any]:
    """Execute one JSON request without conflating route completion with verification."""
    if not isinstance(request, Mapping):
        return {
            "status": "FAILED",
            "error_code": "SARA_REQUEST_MUST_BE_JSON_OBJECT",
            "execution_completed": False,
        }
    try:
        result = runtime.process_turn(request, timeout_seconds=timeout_seconds)
        pipeline_status = result.get("pipeline_status")
        route_execution = result.get("route_execution", {})
        route_output = route_execution.get("output")
        route_output_status = (
            route_output.get("status") if isinstance(route_output, Mapping) else None
        )
        verification_status = _aggregate_verification_status(route_output)

        # "ROUTE_EXECUTED" only means a callback returned. In particular,
        # PROPOSED, NEEDS_REVIEW, and UNVERIFIED must not be surfaced as success.
        if pipeline_status == "NO_ROUTE_REQUIRED":
            status = "NO_ROUTE_REQUIRED"
        elif route_execution.get("execution_status") != "SUCCEEDED":
            status = "FAILED"
        elif route_output_status in {
            "PARTIALLY_FAILED", "FAILED", "INVALID_OUTPUT",
        }:
            status = "PARTIAL_OR_FAILED"
        elif route_output_status in {
            "PROPOSED", "NEEDS_REVIEW", "REVIEW_QUEUED",
        } or verification_status in {
            "UNVERIFIED", "NOT_VERIFIED", "PENDING", "UNSPECIFIED",
            "MIXED", "PARTIALLY_VERIFIED", "INFERRED", "UNASSESSED",
        }:
            status = "COMPLETED_UNVERIFIED"
        elif pipeline_status == "ROUTE_EXECUTED":
            status = "ROUTE_COMPLETED"
        else:
            status = "PARTIAL_OR_FAILED"

        result["status"] = status
        result["execution_completed"] = pipeline_status in {
            "NO_ROUTE_REQUIRED", "ROUTE_EXECUTED",
        } and route_execution.get("execution_status") in {
            "NOT_REQUIRED", "SUCCEEDED",
        }
        # These fields are explicit so consumers cannot mistake route completion
        # for a truth verdict or evidence-grade verification.
        result["route_callback_completed"] = (
            pipeline_status == "ROUTE_EXECUTED"
            and route_execution.get("execution_status") == "SUCCEEDED"
        )
        result["verification_status"] = verification_status or (
            "NOT_RUN" if pipeline_status == "NO_ROUTE_REQUIRED" else "UNSPECIFIED"
        )
        result["claim_truth_assessed"] = False
        return result
    except (DialogueRuntimeError, ValueError, TypeError) as exc:
        return {
            "request_id": request.get("request_id"),
            "conversation_id": request.get("conversation_id"),
            "turn_id": request.get("turn_id"),
            "status": "FAILED",
            "error_code": str(exc) if str(exc).isupper() and len(str(exc)) < 160 else type(exc).__name__,
            "execution_completed": False,
            "route_callback_completed": False,
            "verification_status": "NOT_RUN",
            "claim_truth_assessed": False,
        }
    except Exception as exc:
        # Do not echo provider exception messages, which may contain sensitive data.
        return {
            "request_id": request.get("request_id"),
            "conversation_id": request.get("conversation_id"),
            "turn_id": request.get("turn_id"),
            "status": "FAILED",
            "error_code": f"SARA_UNEXPECTED_{type(exc).__name__}",
            "execution_completed": False,
            "route_callback_completed": False,
            "verification_status": "NOT_RUN",
            "claim_truth_assessed": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SARA v2.5 JSONL dialogue executor")
    parser.add_argument(
        "--provider",
        required=True,
        help="Python module implementing the documented SARA provider contract",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=15.0,
        help="Positive timeout passed to the judgment model (default: 15)",
    )
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout_seconds) or args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be a finite positive number")

    try:
        runtime = build_runtime(args.provider)
    except ExecutorConfigurationError as exc:
        print(json.dumps({
            "status": "BLOCKED",
            "execution_completed": False,
            "error_code": str(exc),
        }, ensure_ascii=False), file=sys.stderr)
        return 2

    for line_number, line in enumerate(sys.stdin, start=1):
        if not line.strip():
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({
                "status": "FAILED",
                "line": line_number,
                "execution_completed": False,
                "error_code": "SARA_INPUT_INVALID_JSON",
            }, ensure_ascii=False))
            continue
        result = execute_request(runtime, request, args.timeout_seconds)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
