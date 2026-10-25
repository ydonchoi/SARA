"""Provider-neutral JSON generation over common LLM HTTP APIs.

Supports OpenAI Responses-compatible chat completions, Anthropic Messages, and
Gemini generateContent. It uses only the Python standard library and never
logs prompts, outputs, credentials, or provider error bodies.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from math import isfinite
import os
import socket
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

JSONMapping = Mapping[str, Any]
JSONSender = Callable[[str, Mapping[str, str], bytes, float], bytes]


class LLMProviderError(RuntimeError):
    """Sanitized provider/configuration/output error; contains no response body."""


def _validate_json_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    """Validate the JSON Schema subset used by SARA independent of provider enforcement."""
    if not isinstance(schema, Mapping):
        raise LLMProviderError("LLM_OUTPUT_SCHEMA_INVALID")
    expected = schema.get("type")
    valid = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
        "boolean": lambda v: isinstance(v, bool),
        "null": lambda v: v is None,
    }
    expected_types = expected if isinstance(expected, list) else [expected]
    if expected is not None and not any(kind in valid and valid[kind](value) for kind in expected_types):
        raise LLMProviderError("LLM_OUTPUT_SCHEMA_TYPE_MISMATCH")
    if "enum" in schema and value not in schema["enum"]:
        raise LLMProviderError("LLM_OUTPUT_SCHEMA_ENUM_MISMATCH")
    if isinstance(value, dict):
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        if not isinstance(required, list) or not isinstance(properties, Mapping):
            raise LLMProviderError("LLM_OUTPUT_SCHEMA_INVALID")
        if any(key not in value for key in required):
            raise LLMProviderError("LLM_OUTPUT_SCHEMA_REQUIRED_FIELD_MISSING")
        if schema.get("additionalProperties") is False and any(key not in properties for key in value):
            raise LLMProviderError("LLM_OUTPUT_SCHEMA_ADDITIONAL_FIELD")
        for key, item in value.items():
            if key in properties:
                _validate_json_schema(item, properties[key], f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            _validate_json_schema(item, schema["items"], f"{path}[{index}]")


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class LLMProviderConfig:
    provider: str
    model: str
    api_key: str = ""
    base_url: str | None = None
    anthropic_version: str = "2023-06-01"
    json_schema_mode: bool | None = None

    @classmethod
    def from_environment(cls, prefix: str = "SARA_LLM") -> "LLMProviderConfig":
        provider = os.environ.get(f"{prefix}_PROVIDER", "").strip().lower()
        model = os.environ.get(f"{prefix}_MODEL", "").strip()
        api_key = os.environ.get(f"{prefix}_API_KEY", "")
        base_url = os.environ.get(f"{prefix}_BASE_URL", "").strip() or None
        schema_mode_value = os.environ.get(f"{prefix}_JSON_SCHEMA", "").strip().lower()
        if schema_mode_value and schema_mode_value not in {"true", "false"}:
            raise LLMProviderError(f"{prefix}_JSON_SCHEMA_MUST_BE_TRUE_OR_FALSE")
        json_schema_mode = schema_mode_value != "false" if schema_mode_value else provider != "kimi"
        if not provider:
            raise LLMProviderError(f"{prefix}_PROVIDER_REQUIRED")
        if not model:
            raise LLMProviderError(f"{prefix}_MODEL_REQUIRED")
        if provider not in {"openai", "openai_compatible", "anthropic", "gemini", "kimi"}:
            raise LLMProviderError("UNSUPPORTED_LLM_PROVIDER")
        return cls(provider=provider, model=model, api_key=api_key, base_url=base_url,
                   json_schema_mode=json_schema_mode)


def _validate_config(config: LLMProviderConfig) -> tuple[str, str]:
    if config.provider not in {"openai", "openai_compatible", "anthropic", "gemini", "kimi"}:
        raise LLMProviderError("UNSUPPORTED_LLM_PROVIDER")
    if not isinstance(config.model, str) or not config.model.strip():
        raise LLMProviderError("LLM_MODEL_REQUIRED")
    defaults = {
        "openai": "https://api.openai.com/v1",
        "openai_compatible": "http://localhost:1234/v1",
        "anthropic": "https://api.anthropic.com",
        "gemini": "https://generativelanguage.googleapis.com",
        "kimi": "https://api.moonshot.ai/v1",
    }
    base_url = (config.base_url or defaults[config.provider]).rstrip("/")
    parsed = urlparse(base_url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise LLMProviderError("LLM_BASE_URL_INVALID")
    local_hosts = {"localhost", "127.0.0.1", "::1"}
    if parsed.scheme != "https" and parsed.hostname not in local_hosts:
        raise LLMProviderError("LLM_BASE_URL_HTTPS_REQUIRED")
    key_required = config.provider != "openai_compatible" or parsed.hostname not in local_hosts
    if key_required and (not isinstance(config.api_key, str) or not config.api_key.strip()):
        raise LLMProviderError("LLM_API_KEY_REQUIRED")
    return base_url, parsed.hostname or ""


def _http_send(url: str, headers: Mapping[str, str], body: bytes, timeout: float) -> bytes:
    request = Request(url, data=body, headers=dict(headers), method="POST")
    hostname = urlparse(url).hostname
    handlers = [_NoRedirectHandler()]
    if hostname in {"localhost", "127.0.0.1", "::1"}:
        handlers.insert(0, ProxyHandler({}))
    opener = build_opener(*handlers)
    try:
        with opener.open(request, timeout=timeout) as response:
            return response.read()
    except HTTPError as exc:
        raise LLMProviderError(f"LLM_PROVIDER_HTTP_ERROR_{exc.code}") from None
    except (socket.timeout, TimeoutError) as exc:
        raise TimeoutError("LLM_PROVIDER_TIMEOUT") from exc
    except URLError as exc:
        if isinstance(exc.reason, (socket.timeout, TimeoutError)):
            raise TimeoutError("LLM_PROVIDER_TIMEOUT") from exc
        raise LLMProviderError("LLM_PROVIDER_NETWORK_ERROR") from None
    except OSError:
        raise LLMProviderError("LLM_PROVIDER_NETWORK_ERROR") from None


class LLMProviderAdapter:
    """Send a JSON-constrained task to a configured general LLM API."""

    def __init__(
        self,
        config: LLMProviderConfig,
        *,
        sender: JSONSender | None = None,
    ) -> None:
        self.config = config
        self.base_url, _ = _validate_config(config)
        self._sender = sender or _http_send

    def generate_json(
        self,
        *,
        system_prompt: str,
        user_payload: JSONMapping,
        output_schema: JSONMapping,
        timeout_seconds: float,
    ) -> dict[str, Any]:
        if not isinstance(system_prompt, str) or not system_prompt.strip():
            raise LLMProviderError("LLM_SYSTEM_PROMPT_REQUIRED")
        if not isinstance(user_payload, Mapping) or not isinstance(output_schema, Mapping):
            raise LLMProviderError("LLM_JSON_INPUT_AND_SCHEMA_REQUIRED")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise LLMProviderError("LLM_TIMEOUT_MUST_BE_POSITIVE")

        url, headers, body = self._build_request(
            system_prompt, user_payload, output_schema
        )
        raw = self._sender(url, headers, body, float(timeout_seconds))
        return self._parse_response(raw, output_schema=output_schema)

    def _build_request(
        self,
        system_prompt: str,
        user_payload: JSONMapping,
        output_schema: JSONMapping,
    ) -> tuple[str, dict[str, str], bytes]:
        provider = self.config.provider
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        user_text = json.dumps(user_payload, ensure_ascii=False, sort_keys=True)

        if provider in {"openai", "openai_compatible", "kimi"}:
            url = f"{self.base_url}/chat/completions"
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"
            use_json_schema = self.config.json_schema_mode if self.config.json_schema_mode is not None else provider != "kimi"
            response_format = (
                {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "sara_structured_output",
                        "strict": True,
                        "schema": dict(output_schema),
                    },
                }
                if use_json_schema else {"type": "json_object"}
            )
            schema_prompt = system_prompt
            if not use_json_schema:
                schema_prompt += (
                    "\n\nReturn exactly one JSON object conforming to this JSON Schema:\n"
                    + json.dumps(dict(output_schema), ensure_ascii=False, sort_keys=True)
                )
            body = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": schema_prompt},
                    {"role": "user", "content": user_text},
                ],
                "response_format": response_format,
            }
        elif provider == "anthropic":
            url = f"{self.base_url}/v1/messages"
            headers.update({
                "x-api-key": self.config.api_key,
                "anthropic-version": self.config.anthropic_version,
            })
            body = {
                "model": self.config.model,
                "max_tokens": 2048,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_text}],
                "output_config": {
                    "format": {
                        "type": "json_schema",
                        "schema": dict(output_schema),
                    }
                },
            }
        else:
            model = quote(self.config.model.removeprefix("models/"), safe="-._")
            url = f"{self.base_url}/v1beta/models/{model}:generateContent"
            headers["x-goog-api-key"] = self.config.api_key
            body = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"role": "user", "parts": [{"text": user_text}]}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": dict(output_schema),
                },
            }
        try:
            encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        except (TypeError, ValueError) as exc:
            raise LLMProviderError("LLM_REQUEST_NOT_JSON_SERIALIZABLE") from exc
        return url, headers, encoded

    def _parse_response(self, raw: bytes, *, output_schema: JSONMapping) -> dict[str, Any]:
        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, AttributeError) as exc:
            raise LLMProviderError("LLM_PROVIDER_RESPONSE_INVALID_JSON") from exc
        if not isinstance(response, Mapping):
            raise LLMProviderError("LLM_PROVIDER_RESPONSE_MUST_BE_OBJECT")

        provider = self.config.provider
        if provider in {"openai", "openai_compatible", "kimi"}:
            choices = response.get("choices")
            if not isinstance(choices, list) or not choices or not isinstance(choices[0], Mapping):
                raise LLMProviderError("LLM_PROVIDER_RESPONSE_CONTENT_MISSING")
            message = choices[0].get("message")
            if not isinstance(message, Mapping):
                raise LLMProviderError("LLM_PROVIDER_RESPONSE_CONTENT_MISSING")
            if message.get("refusal"):
                raise LLMProviderError("LLM_PROVIDER_REFUSED")
            content = message.get("content")
        elif provider == "anthropic":
            if response.get("stop_reason") == "refusal":
                raise LLMProviderError("LLM_PROVIDER_REFUSED")
            blocks = response.get("content")
            content = "".join(
                block.get("text", "")
                for block in blocks
                if isinstance(block, Mapping) and block.get("type") == "text"
            ) if isinstance(blocks, list) else None
        else:
            candidates = response.get("candidates")
            if not isinstance(candidates, list) or not candidates or not isinstance(candidates[0], Mapping):
                raise LLMProviderError("LLM_PROVIDER_RESPONSE_CONTENT_MISSING")
            candidate = candidates[0]
            if candidate.get("finishReason") in {"SAFETY", "RECITATION", "BLOCKLIST"}:
                raise LLMProviderError("LLM_PROVIDER_REFUSED_OR_BLOCKED")
            content_block = candidate.get("content")
            parts = content_block.get("parts") if isinstance(content_block, Mapping) else None
            content = "".join(
                part.get("text", "") for part in parts
                if isinstance(part, Mapping) and isinstance(part.get("text"), str)
            ) if isinstance(parts, list) else None

        if not isinstance(content, str) or not content.strip():
            raise LLMProviderError("LLM_PROVIDER_RESPONSE_CONTENT_MISSING")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMProviderError("LLM_PROVIDER_OUTPUT_INVALID_JSON") from exc
        if not isinstance(parsed, dict):
            raise LLMProviderError("LLM_PROVIDER_OUTPUT_MUST_BE_OBJECT")
        _validate_json_schema(parsed, output_schema)
        return parsed


JUDGMENT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "request_id": {"type": "string"},
        "input_revision_digest": {"type": "string"},
        "judgment_status": {"type": "string", "enum": [
            "INFERENCE_PRESENT", "NO_INFERENCE_DETECTED", "AMBIGUOUS"
        ]},
        "inference_types": {"type": "array", "items": {"type": "string", "enum": [
            "DEDUCTIVE", "INDUCTIVE", "ABDUCTIVE", "CAUSAL", "ANALOGICAL",
            "GENERALIZATION", "INTERPRETIVE", "PREDICTIVE", "NORMATIVE", "OTHER", "NONE"
        ]}},
        "basis_spans": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
        "uncertainty_reason": {"type": "string"},
        "confidence": {"type": "string", "enum": ["HIGH", "MEDIUM", "LOW"]},
        "premise_refs": {"type": "array", "items": {"type": "string"}},
        "claim_refs": {"type": "array", "items": {"type": "string"}},
        "evidence_ids": {"type": "array", "items": {"type": "string"}},
        "provenance_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "request_id", "input_revision_digest", "judgment_status", "inference_types",
        "basis_spans", "rationale", "uncertainty_reason", "confidence",
        "premise_refs", "claim_refs", "evidence_ids", "provenance_ids",
    ],
    "additionalProperties": False,
}


def generate_judgment(
    rubric: str,
    payload: JSONMapping,
    timeout_seconds: float,
) -> dict[str, Any]:
    """CLI-compatible judgment callable configured through SARA_LLM_* env vars."""
    client = LLMProviderAdapter(LLMProviderConfig.from_environment())
    return client.generate_json(
        system_prompt=rubric,
        user_payload=payload,
        output_schema=JUDGMENT_OUTPUT_SCHEMA,
        timeout_seconds=timeout_seconds,
    )


def unconfigured_verification_provider(_payload: JSONMapping) -> dict[str, Any]:
    """Fail-closed placeholder when no source-verification provider is supplied."""
    return {
        "status": "FAILED",
        "verification_status": "UNVERIFIED",
        "findings": ["SOURCE_VERIFICATION_PROVIDER_NOT_CONFIGURED"],
        "failure": {"code": "SOURCE_VERIFICATION_PROVIDER_NOT_CONFIGURED"},
    }
