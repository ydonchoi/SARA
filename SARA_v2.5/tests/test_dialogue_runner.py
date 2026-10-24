from pathlib import Path
import sys

import pytest

V25_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = V25_ROOT.parent
sys.path.insert(0, str(V25_ROOT))
sys.path.insert(0, str(REPO_ROOT))

import dialogue_runner


def test_runner_dispatches_to_dialogue_runtime_with_explicit_providers(monkeypatch):
    calls = {}
    expected = {"pipeline_status": "ROUTE_SKIPPED"}

    def process(payload, **kwargs):
        calls["payload"] = payload
        calls.update(kwargs)
        return expected

    judgment = lambda *_args: {}
    verifier = lambda *_args: {}
    monkeypatch.setattr(dialogue_runner, "process_dialogue_turn", process)

    result = dialogue_runner.run_dialogue_request(
        {"request_id": "R1"}, judgment_generator=judgment,
        verification_provider=verifier, model_id="sara",
        model_revision="test-v1", timeout_seconds=3,
    )

    assert result is expected
    assert calls["payload"] == {"request_id": "R1"}
    assert calls["judgment_generate"] is judgment
    assert calls["verification_provider"] is verifier
    assert calls["model_id"] == "sara"
    assert calls["model_revision"] == "test-v1"
    assert calls["timeout_seconds"] == 3


@pytest.mark.parametrize("spec", ["", "missing_separator", ":callable", "module:"])
def test_callable_loader_rejects_malformed_specs(spec):
    with pytest.raises(ValueError, match="CALLABLE_SPEC_MUST_BE_MODULE_COLON_ATTRIBUTE"):
        dialogue_runner.load_callable(spec)


def test_request_runner_requires_both_provider_callables():
    with pytest.raises(ValueError, match="SARA_JUDGMENT_GENERATOR_REQUIRED"):
        dialogue_runner.run_dialogue_request(
            {}, judgment_generator=None,
            model_id="sara", model_revision="test-v1",
        )


def test_verifier_is_optional_but_defaults_to_explicit_unverified_result(monkeypatch):
    calls = {}

    def process(_payload, **kwargs):
        calls.update(kwargs)
        return {"pipeline_status": "ROUTE_SKIPPED"}

    monkeypatch.setattr(dialogue_runner, "process_dialogue_turn", process)
    dialogue_runner.run_dialogue_request(
        {}, judgment_generator=lambda *_: {}, model_id="sara",
        model_revision="test-v1",
    )

    fallback = calls["verification_provider"]({"claim": {"id": "C1"}})
    assert fallback["status"] == "FAILED"
    assert fallback["verification_status"] == "UNVERIFIED"
    assert fallback["findings"] == ["SOURCE_VERIFICATION_PROVIDER_NOT_CONFIGURED"]
