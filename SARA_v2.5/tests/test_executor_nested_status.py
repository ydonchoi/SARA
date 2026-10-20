"""Regression tests for verifier status nested in dialogue-runtime output."""
from __future__ import annotations

import sys
from pathlib import Path

V25_DIR = str(Path(__file__).resolve().parents[1])
if V25_DIR not in sys.path:
    sys.path.insert(0, V25_DIR)

import executor  # noqa: E402


class RuntimeStub:
    def __init__(self, output):
        self.output = output

    def process_turn(self, request, *, timeout_seconds):
        return {
            "pipeline_status": "ROUTE_EXECUTED",
            "route_execution": {
                "execution_status": "SUCCEEDED",
                "output": self.output,
            },
        }


def _result(statuses):
    results = [
        {
            "claim_id": f"C-{index}",
            "execution_status": "SUCCEEDED",
            "output": {"status": "SUCCEEDED", "verification_status": status},
        }
        for index, status in enumerate(statuses, start=1)
    ]
    return executor.execute_request(
        RuntimeStub({
            "status": "ROUTE_EXECUTED",
            "verification_results": results,
        }),
        {"request_id": "nested-status-regression"},
        1.0,
    )


def test_nested_unverified_status_is_not_reported_as_route_completed():
    result = _result(["UNVERIFIED"])
    assert result["verification_status"] == "UNVERIFIED"
    assert result["status"] == "COMPLETED_UNVERIFIED"
    assert result["claim_truth_assessed"] is False


def test_nested_verified_status_is_propagated_without_claiming_truthfulness():
    result = _result(["VERIFIED"])
    assert result["verification_status"] == "VERIFIED"
    assert result["status"] == "ROUTE_COMPLETED"
    assert result["claim_truth_assessed"] is False


def test_mixed_nested_verification_statuses_are_explicitly_unverified():
    result = _result(["VERIFIED", "UNVERIFIED"])
    assert result["verification_status"] == "MIXED"
    assert result["status"] == "COMPLETED_UNVERIFIED"
    assert result["claim_truth_assessed"] is False


def test_conflicting_top_level_and_nested_statuses_fail_closed():
    runtime = RuntimeStub({
        "status": "ROUTE_EXECUTED",
        "verification_status": "VERIFIED",
        "verification_results": [
            {
                "claim_id": "C-1",
                "execution_status": "SUCCEEDED",
                "output": {"status": "SUCCEEDED", "verification_status": "UNVERIFIED"},
            }
        ],
    })
    result = executor.execute_request(runtime, {"request_id": "conflicting-status"}, 1.0)
    assert result["verification_status"] == "MIXED"
    assert result["status"] == "COMPLETED_UNVERIFIED"
    assert result["claim_truth_assessed"] is False


def test_malformed_nested_result_cannot_preserve_top_level_verified_status():
    runtime = RuntimeStub({
        "status": "ROUTE_EXECUTED",
        "verification_status": "VERIFIED",
        "verification_results": [None],
    })
    result = executor.execute_request(runtime, {"request_id": "malformed-nested-status"}, 1.0)
    assert result["verification_status"] == "MIXED"
    assert result["status"] == "COMPLETED_UNVERIFIED"
    assert result["claim_truth_assessed"] is False


def test_contradicted_or_unknown_nested_status_does_not_look_successful():
    for verifier_status in ("CONTRADICTED", "VERIFED_TYPO"):
        result = _result([verifier_status])
        assert result["verification_status"] == verifier_status
        assert result["status"] == "COMPLETED_UNVERIFIED"
        assert result["claim_truth_assessed"] is False


def test_missing_nested_verification_status_fails_closed():
    runtime = RuntimeStub({
        "status": "ROUTE_EXECUTED",
        "verification_results": [
            {
                "claim_id": "C-1",
                "execution_status": "SUCCEEDED",
                "output": {"status": "SUCCEEDED"},
            }
        ],
    })
    result = executor.execute_request(runtime, {"request_id": "missing-status"}, 1.0)
    assert result["verification_status"] == "UNSPECIFIED"
    assert result["status"] == "COMPLETED_UNVERIFIED"
    assert result["claim_truth_assessed"] is False
