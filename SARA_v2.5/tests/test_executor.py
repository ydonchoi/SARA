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


def test_no_route_required_is_a_completed_execution_not_a_verification():
    class RuntimeStub:
        def process_turn(self, request, *, timeout_seconds):
            return {
                "pipeline_status": "NO_ROUTE_REQUIRED",
                "route_execution": {"execution_status": "NOT_REQUIRED", "output": None},
                "claim_truth_assessed": False,
            }

    result = executor.execute_request(RuntimeStub(), {"request_id": "r3"}, 1.0)
    assert result["status"] == "SUCCEEDED"
    assert result["execution_completed"] is True
    assert result["claim_truth_assessed"] is False



@pytest.mark.parametrize("timeout", ["nan", "inf", "-inf", "0", "-1"])
def test_cli_rejects_non_finite_or_non_positive_timeout(timeout, monkeypatch):
    with pytest.raises(SystemExit) as exc:
        executor.main(["--provider", "unused_provider", "--timeout-seconds", timeout])
    assert exc.value.code == 2
