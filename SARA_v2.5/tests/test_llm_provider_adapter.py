import json
import io
from pathlib import Path
import sys

import pytest

V25_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = V25_ROOT.parent
sys.path.insert(0, str(V25_ROOT))
sys.path.insert(0, str(REPO_ROOT))

from internal_judgment_model import (
    SARAInternalJudgmentModel,
    compute_judgment_input_digest,
)
from llm_provider_adapter import (
    JUDGMENT_OUTPUT_SCHEMA,
    LLMProviderAdapter,
    LLMProviderConfig,
    LLMProviderError,
)
import dialogue_runner


def config(provider, base_url=None):
    return LLMProviderConfig(
        provider=provider,
        model="test-model",
        api_key="test-secret",
        base_url=base_url,
    )


def response_bytes(content, provider="openai"):
    if provider in {"openai", "openai_compatible"}:
        body = {"choices": [{"message": {"content": json.dumps(content)}}]}
    elif provider == "anthropic":
        body = {"content": [{"type": "text", "text": json.dumps(content)}]}
    else:
        body = {"candidates": [{"finishReason": "STOP", "content": {
            "parts": [{"text": json.dumps(content)}]
        }}]}
    return json.dumps(body).encode("utf-8")


@pytest.mark.parametrize("provider,expected_url", [
    ("openai", "https://api.openai.com/v1/chat/completions"),
    ("openai_compatible", "http://localhost:1234/v1/chat/completions"),
])
def test_openai_compatible_request_uses_json_schema_and_parses_content(provider, expected_url):
    calls = {}

    def sender(url, headers, body, timeout):
        calls.update(url=url, headers=headers, body=json.loads(body), timeout=timeout)
        return response_bytes({"ok": True}, provider)

    result = LLMProviderAdapter(config(provider), sender=sender).generate_json(
        system_prompt="Return a JSON object.", user_payload={"x": 1},
        output_schema={"type": "object", "required": ["ok"]},
        timeout_seconds=2.5,
    )

    assert result == {"ok": True}
    assert calls["url"] == expected_url
    assert calls["headers"]["Authorization"] == "Bearer test-secret"
    assert calls["body"]["response_format"]["type"] == "json_schema"
    assert calls["body"]["response_format"]["json_schema"]["strict"] is True
    assert calls["timeout"] == 2.5


def test_anthropic_messages_request_uses_output_config_and_versioned_headers():
    calls = {}

    def sender(url, headers, body, timeout):
        calls.update(url=url, headers=headers, body=json.loads(body))
        return response_bytes({"ok": True}, "anthropic")

    result = LLMProviderAdapter(config("anthropic"), sender=sender).generate_json(
        system_prompt="Return JSON.", user_payload={"claim": "x"},
        output_schema={"type": "object"}, timeout_seconds=4,
    )

    assert result == {"ok": True}
    assert calls["url"] == "https://api.anthropic.com/v1/messages"
    assert calls["headers"]["x-api-key"] == "test-secret"
    assert calls["headers"]["anthropic-version"] == "2023-06-01"
    assert calls["body"]["output_config"]["format"]["type"] == "json_schema"


def test_gemini_generate_content_request_uses_json_mode_and_model_path():
    calls = {}

    def sender(url, headers, body, timeout):
        calls.update(url=url, headers=headers, body=json.loads(body))
        return response_bytes({"ok": True}, "gemini")

    result = LLMProviderAdapter(
        config("gemini", "https://generativelanguage.googleapis.com"),
        sender=sender,
    ).generate_json(
        system_prompt="Return JSON.", user_payload={"claim": "x"},
        output_schema={"type": "object"}, timeout_seconds=4,
    )

    assert result == {"ok": True}
    assert calls["url"].endswith("/v1beta/models/test-model:generateContent")
    assert calls["headers"]["x-goog-api-key"] == "test-secret"
    assert calls["body"]["generationConfig"]["responseMimeType"] == "application/json"
    assert calls["body"]["systemInstruction"]["parts"][0]["text"] == "Return JSON."


def test_generic_llm_adapter_output_passes_sara_judgment_contract():
    request = {
        "request_id": "R1", "conversation_id": "C1", "turn_id": "T1",
        "content": "A direct statement.", "claim_candidates": [],
    }

    def sender(_url, _headers, body, _timeout):
        input_payload = json.loads(json.loads(body)["messages"][1]["content"])
        output = {
            "request_id": input_payload["request_id"],
            "input_revision_digest": input_payload["input_revision_digest"],
            "judgment_status": "NO_INFERENCE_DETECTED",
            "inference_types": [], "basis_spans": [],
            "rationale": "The turn makes no derived claim.",
            "uncertainty_reason": "", "confidence": "HIGH",
            "premise_refs": [], "claim_refs": [], "evidence_ids": [],
            "provenance_ids": [],
        }
        return response_bytes(output)

    adapter = LLMProviderAdapter(config("openai"), sender=sender)
    model = SARAInternalJudgmentModel(
        lambda rubric, payload, timeout: adapter.generate_json(
            system_prompt=rubric, user_payload=payload,
            output_schema=JUDGMENT_OUTPUT_SCHEMA, timeout_seconds=timeout,
        ),
        model_id="test-model", model_revision="provider-adapter-test",
    )
    result = model.judge(request, timeout_seconds=2)

    assert result["execution_status"] == "SUCCEEDED"
    assert result["input_revision_digest"] == compute_judgment_input_digest(request)
    assert result["is_evidence"] is False
    assert result["claim_truth_assessed"] is False


def test_provider_refusal_and_malformed_json_fail_as_provider_errors():
    refused = {"choices": [{"message": {"refusal": "refused", "content": None}}]}
    adapter = LLMProviderAdapter(config("openai"), sender=lambda *_: json.dumps(refused).encode())
    with pytest.raises(LLMProviderError, match="LLM_PROVIDER_REFUSED"):
        adapter.generate_json(
            system_prompt="x", user_payload={}, output_schema={}, timeout_seconds=1
        )


def test_transport_timeout_is_preserved_for_sara_timeout_handling():
    def timeout_sender(*_args):
        raise TimeoutError("LLM_PROVIDER_TIMEOUT")

    adapter = LLMProviderAdapter(config("openai"), sender=timeout_sender)
    with pytest.raises(TimeoutError, match="LLM_PROVIDER_TIMEOUT"):
        adapter.generate_json(
            system_prompt="x", user_payload={}, output_schema={}, timeout_seconds=0.1
        )

    malformed = {"choices": [{"message": {"content": "not json"}}]}
    adapter = LLMProviderAdapter(config("openai"), sender=lambda *_: json.dumps(malformed).encode())
    with pytest.raises(LLMProviderError, match="LLM_PROVIDER_OUTPUT_INVALID_JSON"):
        adapter.generate_json(
            system_prompt="x", user_payload={}, output_schema={}, timeout_seconds=1
        )


def test_api_key_and_transport_security_are_validated_before_send():
    with pytest.raises(LLMProviderError, match="LLM_API_KEY_REQUIRED"):
        LLMProviderAdapter(LLMProviderConfig(provider="anthropic", model="m"))
    with pytest.raises(LLMProviderError, match="LLM_BASE_URL_HTTPS_REQUIRED"):
        LLMProviderAdapter(config("openai_compatible", "http://example.com/v1"))
    with pytest.raises(LLMProviderError, match="LLM_BASE_URL_INVALID"):
        LLMProviderAdapter(config("openai_compatible", "https://user:pass@example.com/v1"))


def test_builtin_cli_runs_configured_adapter_into_sara_runtime(monkeypatch, capsys):
    import llm_provider_adapter

    captured = {}

    class FakeHTTPAdapter:
        def __init__(self, provider_config):
            captured["config"] = provider_config

        def generate_json(self, *, system_prompt, user_payload, output_schema, timeout_seconds):
            captured["schema"] = output_schema
            captured["timeout_seconds"] = timeout_seconds
            return {
                "request_id": user_payload["request_id"],
                "input_revision_digest": user_payload["input_revision_digest"],
                "judgment_status": "NO_INFERENCE_DETECTED",
                "inference_types": [], "basis_spans": [],
                "rationale": "The text contains no derived claim.",
                "uncertainty_reason": "", "confidence": "HIGH",
                "premise_refs": [], "claim_refs": [], "evidence_ids": [],
                "provenance_ids": [],
            }

    monkeypatch.setattr(llm_provider_adapter, "LLMProviderAdapter", FakeHTTPAdapter)
    monkeypatch.setenv("SARA_LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("SARA_LLM_MODEL", "local-test-model")
    monkeypatch.delenv("SARA_LLM_API_KEY", raising=False)
    monkeypatch.setenv("SARA_LLM_BASE_URL", "http://localhost:1234/v1")
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({
        "request_id": "CLI-1", "conversation_id": "CONV-1", "turn_id": "TURN-1",
        "content": "A direct statement.", "claim_candidates": [],
    })))
    assert dialogue_runner.main(["--model-revision", "local-adapter-smoke"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["judgment"]["execution_status"] == "SUCCEEDED", result
    assert result["judgment"]["model_id"] == "local-test-model"
    assert result["pipeline_status"] == "NO_ROUTE_REQUIRED"
    assert captured["config"].provider == "openai_compatible"
    assert captured["config"].model == "local-test-model"
    assert captured["schema"] == JUDGMENT_OUTPUT_SCHEMA
    assert captured["timeout_seconds"] > 0
