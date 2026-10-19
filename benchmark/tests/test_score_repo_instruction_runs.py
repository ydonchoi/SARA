from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from score_repo_instruction_runs import BenchmarkRecordError, score_records, read_jsonl


def row(case, condition="C", model="model-x", expected=None, observed=None, metrics=None):
    return {
        "case_id": case,
        "condition": condition,
        "model_id": model,
        "expected": expected or {"rule_applied": True, "evidence_traceable": True},
        "observed": observed or {"rule_applied": True, "evidence_traceable": True},
        "metrics": metrics or {"latency_ms": 100, "tool_calls": 2, "cost_usd": 0.01},
    }


def test_score_records_aggregates_criterion_accuracy_and_operational_metrics():
    result = score_records([
        row("R1", observed={"rule_applied": True, "evidence_traceable": True}),
        row("R2", observed={"rule_applied": False, "evidence_traceable": True},
            metrics={"latency_ms": 300, "tool_calls": 4, "cost_usd": 0.03}),
    ])
    group = result["groups"][0]
    assert group["condition"] == "C"
    assert group["cases"] == 2
    assert group["criteria"]["rule_applied"] == {"n": 2, "correct": 1, "accuracy": 0.5}
    assert group["criteria"]["evidence_traceable"]["accuracy"] == 1.0
    assert group["operational_metrics"]["latency_ms"]["mean"] == 200
    assert group["operational_metrics"]["latency_ms"]["median"] == 200
    assert result["record_count"] == 2
    assert "do not establish label independence" in result["interpretation_limit"]


def test_score_records_separates_conditions_and_models():
    result = score_records([
        row("R1", condition="A", model="model-a"),
        row("R1", condition="D", model="model-a"),
        row("R1", condition="D", model="model-b"),
    ])
    assert len(result["groups"]) == 3


def test_duplicate_case_condition_model_is_rejected():
    with pytest.raises(BenchmarkRecordError, match="DUPLICATE_CASE_CONDITION_MODEL"):
        score_records([row("R1"), row("R1")])


def test_expected_and_observed_criterion_mismatch_is_rejected():
    with pytest.raises(BenchmarkRecordError, match="EXPECTED_OBSERVED_CRITERIA_MISMATCH"):
        score_records([row("R1", observed={"rule_applied": True})])


def test_negative_or_nonfinite_operational_metrics_are_rejected():
    with pytest.raises(BenchmarkRecordError, match="METRIC_MUST_BE_FINITE_NONNEGATIVE"):
        score_records([row("R1", metrics={"latency_ms": -1})])
    with pytest.raises(BenchmarkRecordError, match="METRIC_MUST_BE_FINITE_NONNEGATIVE"):
        score_records([row("R2", metrics={"cost_usd": float("nan")})])


def test_read_jsonl_reports_malformed_line_number(tmp_path):
    path = tmp_path / "runs.jsonl"
    path.write_text('{"case_id": "R1"\n', encoding="utf-8")
    with pytest.raises(BenchmarkRecordError, match="INVALID_JSONL_LINE:1"):
        read_jsonl(path)


def test_malformed_condition_type_is_rejected():
    malformed = row("R1")
    malformed["condition"] = ["D"]
    with pytest.raises(BenchmarkRecordError, match="CONDITION_MUST_BE_A_B_C_OR_D"):
        score_records([malformed])


@pytest.mark.parametrize(
    "field,value,error",
    [
        ("expected", {"rule_applied": ["yes"], "evidence_traceable": True}, "EXPECTED_LABEL_MUST_BE_SCALAR"),
        ("observed", {"rule_applied": {"nested": True}, "evidence_traceable": True},
         "OBSERVED_LABEL_MUST_BE_SCALAR"),
        ("expected", {"rule_applied": float("nan"), "evidence_traceable": True}, "EXPECTED_LABEL_MUST_BE_FINITE"),
        ("observed", {"rule_applied": float("inf"), "evidence_traceable": True},
         "OBSERVED_LABEL_MUST_BE_FINITE"),
    ],
)
def test_label_values_must_match_schema_scalar_types(field, value, error):
    record = row("R1")
    record[field] = value
    with pytest.raises(BenchmarkRecordError, match=error):
        score_records([record])


def test_label_criterion_names_must_be_nonempty_strings():
    record = row("R1")
    record["expected"] = {"": True}
    record["observed"] = {"": True}
    with pytest.raises(BenchmarkRecordError, match="EXPECTED_CRITERION_NAME_REQUIRED"):
        score_records([record])
