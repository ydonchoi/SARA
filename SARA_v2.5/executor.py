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
    python -m SARA_v2.5.executor --provider package.module
Input is one JSON request per line on stdin; output is one JSON result per line.
"""
from __future__ import annotations

import argparse
import importlib
import json
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
        adapter_revision="sara-v25-executor-cli-v0.1",
    )


def execute_request(runtime: SARADialogueRuntime, request: Any, timeout_seconds: float) -> dict[str, Any]:
    """Execute one JSON request without converting exceptions into a success."""
    if not isinstance(request, Mapping):
        return {
            "status": "FAILED",
            "error_code": "SARA_REQUEST_MUST_BE_JSON_OBJECT",
            "execution_completed": False,
        }
    try:
        result = runtime.process_turn(request, timeout_seconds=timeout_seconds)
        result["status"] = (
            "SUCCEEDED"
            if result.get("pipeline_status") in {"ROUTE_EXECUTED", "NO_ROUTE_REQUIRED"}
            else "PARTIAL_OR_FAILED"
        )
        result["execution_completed"] = True
        return result
    except (DialogueRuntimeError, ValueError, TypeError) as exc:
        return {
            "request_id": request.get("request_id"),
            "conversation_id": request.get("conversation_id"),
            "turn_id": request.get("turn_id"),
            "status": "FAILED",
            "error_code": str(exc) if str(exc).isupper() and len(str(exc)) < 160 else type(exc).__name__,
            "execution_completed": False,
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
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")

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
