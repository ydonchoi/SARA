"""Contract tests for the explicit SARA v2.5 executor boundary."""
from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest

V25_DIR = str(Path(__file__).resolve().parents[1])
if V25_DIR not in sys.path:
    sys.path.insert(0, V25_DIR)

import executor  # noqa: E402
from internal_judgment_model import compute_judgment_input_digest  # noqa: E402


def test_provider_requires_explicit_model_and_verifier(monkeypatch):
    provider = ModuleType("test_sara_provider")
    provider.MODEL_ID = "test-model"
    provider.MODEL_REVISION = "test-rev"
    provider.generate = lambda prompt, payload, timeout: {}
    monkeypatch.setitem(sys.modules, "test_sara_provider", provider)

    with pytest.raises(executor.ExecutorConfigurationError, match="VERIFY_CLAIM_CALLABLE_REQUIRED"):
        executor.build_runtime("test_sara_provider")


def test_provider_import_failure_is_blocked():
    with pytest.raises(executor.ExecutorConfigurationError, match="PROVIDER_IMPORT_FAILED"):
        executor.build_runtime("module_that_does_not_exist_for_sara_test")


def test_non_object_request_fails_closed():
    class RuntimeStub:
        def process_turn(self, request, *, timeout_seconds):
            raise AssertionError("runtime must not be called for non-object input")

    result = executor.execute_request(RuntimeStub(), ["not", "an", "object"], 1.0)
    assert result["status"] == "FAILED"
    assert result["execution_completed"] is False
    assert result["error_code"] == "SARA_REQUEST_MUST_BE_JSON_OBJECT"


def test_runtime_exception_does_not_become_success():
    class RuntimeStub:
        def process_turn(self, request, *, timeout_seconds):
            raise ValueError("DIALOGUE_TURN_CONTENT_REQUIRED")

    result = executor.execute_request(
        RuntimeStub(),
        {"request_id": "r1", "conversation_id": "c1", "turn_id": "t1"},
        1.0,
    )
    assert result["status"] == "FAILED"
    assert result["execution_completed"] is False
    assert result["error_code"] == "DIALOGUE_TURN_CONTENT_REQUIRED"
    assert result["verification_status"] == "NOT_RUN"
    assert result["claim_truth_assessed"] is False


def test_partial_verifier_failure_is_not_reported_as_success():
    class RuntimeStub:
        def process_turn(self, request, *, timeout_seconds):
            return {
                "pipeline_status": "ROUTE_EXECUTED",
                "route_execution": {
                    "execution_status": "SUCCEEDED",
                    "output": {"status": "PARTIALLY_FAILED"},
                },
            }

    result = executor.execute_request(RuntimeStub(), {"request_id": "r2"}, 1.0)
    assert result["status"] == "PARTIAL_OR_FAILED"
    assert result["execution_completed"] is True
    assert result["route_callback_completed"] is True
    assert result["verification_status"] == "UNSPECIFIED"
    assert result["claim_truth_assessed"] is False


def test_no_route_required_is_not_misrepresented_as_verification_success():
    class RuntimeStub:
        def process_turn(self, request, *, timeout_seconds):
            return {
                "pipeline_status": "NO_ROUTE_REQUIRED",
                "route_execution": {"execution_status": "NOT_REQUIRED", "output": None},
                "claim_truth_assessed": False,
            }

    result = executor.execute_request(RuntimeStub(), {"request_id": "r3"}, 1.0)
    assert result["status"] == "NO_ROUTE_REQUIRED"
    assert result["execution_completed"] is True
    assert result["route_callback_completed"] is False
    assert result["verification_status"] == "NOT_RUN"
    assert result["claim_truth_assessed"] is False


@pytest.mark.parametrize(
    ("output", "expected_status", "expected_verification_status"),
    [
        ({"status": "NEEDS_REVIEW"}, "COMPLETED_UNVERIFIED", "UNSPECIFIED"),
        ({"status": "REVIEW_QUEUED"}, "COMPLETED_UNVERIFIED", "UNSPECIFIED"),
        ({"status": "PROPOSED"}, "COMPLETED_UNVERIFIED", "UNSPECIFIED"),
        (
            {"status": "SUCCEEDED", "verification_status": "UNVERIFIED"},
            "COMPLETED_UNVERIFIED",
            "UNVERIFIED",
        ),
        (
            {"status": "SUCCEEDED", "verification_status": "VERIFIED"},
            "ROUTE_COMPLETED",
            "VERIFIED",
        ),
    ],
)
def test_route_completion_is_separated_from_verification_outcome(
    output, expected_status, expected_verification_status
):
    class RuntimeStub:
        def process_turn(self, request, *, timeout_seconds):
            return {
                "pipeline_status": "ROUTE_EXECUTED",
                "route_execution": {
                    "execution_status": "SUCCEEDED",
                    "output": output,
                },
                "claim_truth_assessed": False,
            }

    result = executor.execute_request(RuntimeStub(), {"request_id": "r4"}, 1.0)
    assert result["status"] == expected_status
    assert result["execution_completed"] is True
    assert result["route_callback_completed"] is True
    assert result["verification_status"] == expected_verification_status
    assert result["claim_truth_assessed"] is False


def _runtime_request():
    return {
        "request_id": "REQ-EXEC-1",
        "conversation_id": "CONV-EXEC-1",
        "turn_id": "TURN-EXEC-1",
        "content": "Sales rose after the campaign, therefore the campaign caused the increase.",
        "context": {"role": "assistant"},
        "claim_candidates": [{"id": "C-1", "text": "The campaign caused the increase."}],
        "evidence": [],
    }


def _judgment_generator(status="INFERENCE_PRESENT"):
    def generate(_rubric, payload, timeout_seconds):
        assert timeout_seconds > 0
        detected = status == "INFERENCE_PRESENT"
        return {
            "request_id": payload["request_id"],
            "input_revision_digest": compute_judgment_input_digest(payload),
            "judgment_status": status,
            "inference_types": ["CAUSAL"] if detected else [],
            "basis_spans": ["therefore the campaign caused the increase"] if detected else [],
            "rationale": "Deterministic test double; not a semantic evaluation.",
            "uncertainty_reason": "",
            "confidence": "HIGH",
            "premise_refs": [],
            "claim_refs": ["C-1"] if detected else [],
            "evidence_ids": [],
            "provenance_ids": [],
        }
    return generate


def test_executor_integrates_with_real_dialogue_runtime_and_preserves_partial_failure():
    provider = ModuleType("test_sara_executor_integration_provider")
    provider.MODEL_ID = "deterministic-test-model"
    provider.MODEL_REVISION = "unit-test-double"
    provider.generate = _judgment_generator()
    provider.verify_claim = lambda _request: {
        "status": "FAILED",
        "failure": {"code": "TEST_UPSTREAM_FAILURE"},
        "verification_status": "UNVERIFIED",
    }
    # build_runtime imports by name, so register this deterministic provider first.
    sys.modules[provider.__name__] = provider
    runtime = executor.build_runtime(provider.__name__)

    result = executor.execute_request(runtime, _runtime_request(), 1.0)

    assert result["pipeline_status"] == "ROUTE_EXECUTED"
    assert result["route_callback_completed"] is True
    assert result["status"] == "PARTIAL_OR_FAILED"
    assert result["verification_status"] == "UNVERIFIED"
    assert result["claim_truth_assessed"] is False


def test_executor_integrates_no_route_without_claiming_verification():
    provider = ModuleType("test_sara_executor_no_route_provider")
    provider.MODEL_ID = "deterministic-test-model"
    provider.MODEL_REVISION = "unit-test-double"
    provider.generate = _judgment_generator("NO_INFERENCE_DETECTED")
    provider.verify_claim = lambda _request: pytest.fail("verifier must not run")
    sys.modules[provider.__name__] = provider
    runtime = executor.build_runtime(provider.__name__)

    result = executor.execute_request(runtime, _runtime_request(), 1.0)

    assert result["status"] == "NO_ROUTE_REQUIRED"
    assert result["verification_status"] == "NOT_RUN"
    assert result["route_callback_completed"] is False
    assert result["claim_truth_assessed"] is False


@pytest.mark.parametrize("timeout", ["nan", "inf", "-inf", "0", "-1"])
def test_cli_rejects_non_finite_or_non_positive_timeout(timeout, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        executor.main(["--provider", "unused_provider", "--timeout-seconds", timeout])
    assert exc.value.code == 2
