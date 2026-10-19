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


def test_distinct_repetitions_for_same_case_condition_model_are_accepted():
    first = row("R1")
    first["repetition_id"] = "1"
    second = row("R1", observed={"rule_applied": False, "evidence_traceable": True})
    second["repetition_id"] = "2"
    result = score_records([first, second])
    group = result["groups"][0]
    assert group["cases"] == 1
    assert group["run_records"] == 2
    assert group["repetitions"] == 2
    assert group["criteria"]["rule_applied"] == {"n": 2, "correct": 1, "accuracy": 0.5}


def test_same_repetition_for_same_case_condition_model_is_rejected():
    first = row("R1")
    second = row("R1")
    first["repetition_id"] = "repeat-a"
    second["repetition_id"] = "repeat-a"
    with pytest.raises(BenchmarkRecordError, match="DUPLICATE_CASE_CONDITION_MODEL_REPETITION"):
        score_records([first, second])


def test_repetition_id_must_be_nonempty_string():
    record = row("R1")
    record["repetition_id"] = ""
    with pytest.raises(BenchmarkRecordError, match="REPETITION_ID_REQUIRED"):
        score_records([record])


def test_paired_coverage_reports_shared_and_unpaired_cases():
    result = score_records([
        row("R1", condition="A"),
        row("R2", condition="A"),
        row("R1", condition="B"),
        row("R1", condition="C"),
        row("R3", condition="C"),
    ])
    coverage = result["paired_coverage"][0]
    assert coverage["model_id"] == "model-x"
    assert coverage["conditions_present"] == ["A", "B", "C"]
    assert coverage["missing_conditions"] == ["D"]
    assert coverage["shared_case_count_across_present_conditions"] == 1
    assert coverage["case_union_count"] == 3
    assert coverage["complete_four_condition_case_pairing"] is False
    assert coverage["unpaired_case_ids_by_condition"] == {
        "A": ["R2"],
        "C": ["R3"],
    }


def test_paired_coverage_marks_complete_four_condition_case_set():
    records = [
        row(case, condition=condition)
        for condition in ("A", "B", "C", "D")
        for case in ("R1", "R2")
    ]
    result = score_records(records)
    coverage = result["paired_coverage"][0]
    assert coverage["missing_conditions"] == []
    assert coverage["shared_case_count_across_present_conditions"] == 2
    assert coverage["case_union_count"] == 2
    assert coverage["complete_four_condition_case_pairing"] is True


def test_paired_coverage_detects_misaligned_repetition_ids():
    records = []
    for condition, repetitions in {
        "A": ("1", "2"),
        "B": ("1", "3"),
        "C": ("1", "2"),
        "D": ("1", "2"),
    }.items():
        for repetition in repetitions:
            record = row("R1", condition=condition)
            record["repetition_id"] = repetition
            records.append(record)
    coverage = score_records(records)["paired_coverage"][0]
    assert coverage["complete_four_condition_case_pairing"] is True
    assert coverage["shared_case_repetition_count_across_present_conditions"] == 1
    assert coverage["case_repetition_union_count"] == 3
    assert coverage["complete_four_condition_run_pairing"] is False
    assert coverage["unpaired_case_repetitions_by_condition"] == {
        "A": [{"case_id": "R1", "repetition_id": "2"}],
        "B": [{"case_id": "R1", "repetition_id": "3"}],
        "C": [{"case_id": "R1", "repetition_id": "2"}],
        "D": [{"case_id": "R1", "repetition_id": "2"}],
    }


def test_paired_coverage_accepts_fully_aligned_repetitions():
    records = []
    for condition in ("A", "B", "C", "D"):
        for repetition in ("1", "2"):
            record = row("R1", condition=condition)
            record["repetition_id"] = repetition
            records.append(record)
    coverage = score_records(records)["paired_coverage"][0]
    assert coverage["complete_four_condition_case_pairing"] is True
    assert coverage["complete_four_condition_run_pairing"] is True
    assert coverage["shared_case_repetition_count_across_present_conditions"] == 2
    assert coverage["case_repetition_union_count"] == 2
