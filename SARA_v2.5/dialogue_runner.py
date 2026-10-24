"""Command-line runner for the SARA v2.5 dialogue-turn route.

Judgment may use a built-in generic LLM REST adapter or an injected callable.
Source verification remains a separate injected capability.
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path
from typing import Any, Callable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
V25_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(V25_ROOT) not in sys.path:
    sys.path.insert(0, str(V25_ROOT))

from sara_runtime import process_dialogue_turn  # noqa: E402


def load_callable(spec: str) -> Callable[..., Any]:
    """Load a callable specified as ``package.module:attribute``."""
    if not isinstance(spec, str) or ":" not in spec:
        raise ValueError("CALLABLE_SPEC_MUST_BE_MODULE_COLON_ATTRIBUTE")
    module_name, attribute_name = spec.split(":", 1)
    if not module_name.strip() or not attribute_name.strip():
        raise ValueError("CALLABLE_SPEC_MUST_BE_MODULE_COLON_ATTRIBUTE")
    module = importlib.import_module(module_name)
    value = getattr(module, attribute_name, None)
    if not callable(value):
        raise ValueError("PROVIDER_ATTRIBUTE_NOT_CALLABLE")
    return value


def run_dialogue_request(
    payload: Mapping[str, Any],
    *,
    judgment_generator: Callable[..., Mapping[str, Any]],
    verification_provider: Callable[..., Mapping[str, Any]] | None = None,
    model_id: str,
    model_revision: str,
    timeout_seconds: float = 15.0,
) -> dict[str, Any]:
    """Execute one dialogue turn through the existing callable runtime."""
    if not isinstance(payload, Mapping):
        raise ValueError("DIALOGUE_TURN_REQUEST_MUST_BE_OBJECT")
    if not callable(judgment_generator):
        raise ValueError("SARA_JUDGMENT_GENERATOR_REQUIRED")
    if verification_provider is None:
        from llm_provider_adapter import unconfigured_verification_provider
        verification_provider = unconfigured_verification_provider
    if not callable(verification_provider):
        raise ValueError("SARA_VERIFICATION_PROVIDER_INVALID")
    if not isinstance(model_id, str) or not model_id.strip():
        raise ValueError("SARA_MODEL_ID_REQUIRED")
    if not isinstance(model_revision, str) or not model_revision.strip():
        raise ValueError("SARA_MODEL_REVISION_REQUIRED")
    return process_dialogue_turn(
        payload,
        judgment_generate=judgment_generator,
        verification_provider=verification_provider,
        model_id=model_id,
        model_revision=model_revision,
        timeout_seconds=timeout_seconds,
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run one SARA v2.5 dialogue turn with injected providers."
    )
    parser.add_argument("--judgment-provider", default="builtin:llm", help="builtin:llm or MODULE:ATTRIBUTE callable (rubric, payload, timeout_seconds)")
    parser.add_argument("--verification-provider", help="Optional MODULE:ATTRIBUTE source-verification callable (payload); omitted means UNVERIFIED")
    parser.add_argument("--model-id", help="Optional for builtin:llm; if supplied it must match SARA_LLM_MODEL")
    parser.add_argument("--model-revision", help="Revision label recorded in the judgment provenance")
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    parser.add_argument("--request", default="-", help="JSON request file; '-' reads stdin")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        raw = sys.stdin.read() if args.request == "-" else Path(args.request).read_text(encoding="utf-8")
        payload = json.loads(raw)
        model_id = args.model_id
        model_revision = args.model_revision
        if args.judgment_provider == "builtin:llm":
            from llm_provider_adapter import (
                LLMProviderAdapter,
                LLMProviderConfig,
            )
            provider_config = LLMProviderConfig.from_environment()
            if model_id and model_id != provider_config.model:
                raise ValueError("CLI_MODEL_ID_DOES_NOT_MATCH_SARA_LLM_MODEL")
            model_id = provider_config.model
            model_revision = model_revision or f"{provider_config.provider}-json-api-v1"
            provider_adapter = LLMProviderAdapter(provider_config)

            def judgment_provider(rubric, payload, timeout_seconds):
                from llm_provider_adapter import JUDGMENT_OUTPUT_SCHEMA
                return provider_adapter.generate_json(
                    system_prompt=rubric,
                    user_payload=payload,
                    output_schema=JUDGMENT_OUTPUT_SCHEMA,
                    timeout_seconds=timeout_seconds,
                )
        else:
            judgment_provider = load_callable(args.judgment_provider)
        result = run_dialogue_request(
            payload,
            judgment_generator=judgment_provider,
            verification_provider=(
                load_callable(args.verification_provider)
                if args.verification_provider else None
            ),
            model_id=model_id,
            model_revision=model_revision,
            timeout_seconds=args.timeout_seconds,
        )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "FAILED",
            "error_type": type(exc).__name__,
            "error": str(exc),
            "automatic_truthfulness_upgrade": False,
        }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
