import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "SARA_v2.3" / "verification_need.py"
SPEC = importlib.util.spec_from_file_location("sara_verification_need", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_explicit_verification_request_routes_to_external_check():
    result = MODULE.assess_verification_need("이 주장의 출처를 검증해 줘.")
    assert result["decision"] == "VERIFY"
    assert result["verification_required"] is True
    assert "EXPLICIT_VERIFICATION_REQUEST" in result["reason_codes"]


def test_time_sensitive_claim_routes_to_external_check():
    result = MODULE.assess_verification_need("현재 한국 기준금리는 얼마인가?")
    assert result["decision"] == "VERIFY"
    assert "TIME_SENSITIVE_CLAIM" in result["reason_codes"]


def test_high_stakes_claim_routes_to_external_check():
    result = MODULE.assess_verification_need("이 약의 복용량은 하루 3회이다.")
    assert result["verification_required"] is True
    assert "HIGH_STAKES_DOMAIN" in result["reason_codes"]


def test_generic_assertion_is_review_not_verified():
    result = MODULE.assess_verification_need("이 정책은 교육 효과를 높인다.")
    assert result["decision"] == "REVIEW"
    assert result["verification_required"] is False
    assert result["external_check_recommended"] is False


def test_opinion_or_greeting_does_not_trigger_external_check():
    result = MODULE.assess_verification_need("오늘은 기분이 좋다.")
    assert result["decision"] == "NO_AUTOMATIC_CHECK"
    assert result["verification_required"] is False


def test_empty_claim_rejected():
    try:
        MODULE.assess_verification_need(" ")
    except ValueError as exc:
        assert str(exc) == "CLAIM_TEXT_REQUIRED"
    else:
        raise AssertionError("empty claim must be rejected")
