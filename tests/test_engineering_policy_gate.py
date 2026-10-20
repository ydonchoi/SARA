import importlib.util
from pathlib import Path

MODULE_PATH = Path(__file__).parents[1] / "tools" / "engineering_policy_gate.py"
SPEC = importlib.util.spec_from_file_location("sara_engineering_policy_gate", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_source_change_without_tests_is_blocked():
    findings = MODULE.evaluate_change(["sara_runtime.py"], "+new line")
    assert findings[0]["severity"] == "BLOCK"
    assert findings[0]["code"] == "SOURCE_CHANGE_WITHOUT_TEST_CHANGE"


def test_source_change_with_tests_has_no_missing_test_blocker():
    findings = MODULE.evaluate_change(
        ["sara_runtime.py", "tests/test_runtime.py"], "+new line"
    )
    assert not any(item["code"] == "SOURCE_CHANGE_WITHOUT_TEST_CHANGE" for item in findings)


def test_removing_assertions_and_adding_skips_is_blocked():
    diff = "-    assert result.status == 'SUCCEEDED'\n+    pytest.skip('temporary')"
    findings = MODULE.evaluate_change(["tests/test_runtime.py"], diff)
    assert any(item["code"] == "POSSIBLE_TEST_WEAKENING" for item in findings)


def test_docs_only_change_is_reviewable_not_blocked():
    findings = MODULE.evaluate_change(["docs/guide.md"], "+documentation")
    assert findings[0]["severity"] == "REVIEW"
