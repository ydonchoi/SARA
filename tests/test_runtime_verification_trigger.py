import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "sara_runtime.py"
SPEC = importlib.util.spec_from_file_location("sara_runtime_auto", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _request(text):
    return {
        "request_id": "AUTO-1",
        "capability": "verify_claim",
        "claim": {
            "id": "CLAIM-AUTO-1",
            "text": text,
            "inference_level": "FACT",
        },
        "evidence": [],
        "provenance_ids": ["INPUT-AUTO-1"],
        "adapter_revision": "auto-test",
        "requested_at": "2026-10-20T00:00:00Z",
        "environment": {"test": True},
    }


def test_auto_mode_skips_provider_for_non_verification_chat():
    def provider(_request):
        raise AssertionError("provider must not be called")

    result = MODULE.execute_auto_request(_request("오늘은 기분이 좋다."), provider)
    assert result["status"] == "SKIPPED"
    assert result["provider_called"] is False
    assert result["verification_status"] == "UNVERIFIED"
    assert result["truthfulness_status"] == "UNASSESSED"


def test_auto_mode_calls_provider_for_time_sensitive_claim():
    calls = []

    def provider(request):
        calls.append(request)
        return {
            "status": "SUCCEEDED",
            "external_result_id": "AUTO-RESULT-1",
            "external_result_provenance_ids": ["AUTO-PROV-1"],
            "verification_status": "UNVERIFIED",
            "findings": ["provider did not establish truth"],
        }

    result = MODULE.execute_auto_request(
        _request("현재 기준금리는 2.5%다."), provider
    )
    assert result["status"] == "SUCCEEDED"
    assert result["provider_called"] is True
    assert len(calls) == 1
    assert result["verification_need"]["decision"] == "VERIFY"
    assert result["truthfulness_status"] == "UNASSESSED"


def test_auto_mode_requires_provider_when_triage_requires_verification():
    try:
        MODULE.execute_auto_request(_request("현재 기준금리는 얼마인가?"))
    except ValueError as exc:
        assert str(exc) == "PROVIDER_REQUIRED_FOR_VERIFICATION"
    else:
        raise AssertionError("verification without a provider must fail explicitly")
