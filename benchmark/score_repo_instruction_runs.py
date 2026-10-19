#!/usr/bin/env python3
"""Score adjudicated repository-instruction benchmark runs from JSONL.

This utility compares observed labels to independently adjudicated expected
labels. It does not create gold labels, validate their quality, or execute LLMs.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Iterable

NUMERIC_METRICS = {
    "latency_ms", "tool_calls", "prompt_tokens", "completion_tokens", "cost_usd"
}
REQUIRED_FIELDS = {"case_id", "condition", "model_id", "expected", "observed"}
VALID_CONDITIONS = {"A", "B", "C", "D"}


class BenchmarkRecordError(ValueError):
    """Raised when a run record is malformed or ambiguous to score."""


def validate_record(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise BenchmarkRecordError("RUN_RECORD_MUST_BE_OBJECT")
    missing = REQUIRED_FIELDS - set(record)
    if missing:
        raise BenchmarkRecordError("RUN_RECORD_MISSING_FIELDS:" + ",".join(sorted(missing)))
    for field in ("case_id", "model_id"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise BenchmarkRecordError(f"{field.upper()}_REQUIRED")
    if record["condition"] not in VALID_CONDITIONS:
        raise BenchmarkRecordError("CONDITION_MUST_BE_A_B_C_OR_D")
    expected, observed = record["expected"], record["observed"]
    if not isinstance(expected, dict) or not expected:
        raise BenchmarkRecordError("EXPECTED_LABELS_MUST_BE_NONEMPTY_OBJECT")
    if not isinstance(observed, dict):
        raise BenchmarkRecordError("OBSERVED_LABELS_MUST_BE_OBJECT")
    if set(expected) != set(observed):
        raise BenchmarkRecordError("EXPECTED_OBSERVED_CRITERIA_MISMATCH")
    metrics = record.get("metrics", {})
    if not isinstance(metrics, dict):
        raise BenchmarkRecordError("METRICS_MUST_BE_OBJECT")
    unknown = set(metrics) - NUMERIC_METRICS
    if unknown:
        raise BenchmarkRecordError("UNKNOWN_OPERATIONAL_METRIC:" + ",".join(sorted(unknown)))
    for key, value in metrics.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise BenchmarkRecordError(f"METRIC_MUST_BE_NUMERIC:{key}")
        if not math.isfinite(float(value)) or value < 0:
            raise BenchmarkRecordError(f"METRIC_MUST_BE_FINITE_NONNEGATIVE:{key}")
        if key in {"tool_calls", "prompt_tokens", "completion_tokens"} and not isinstance(value, int):
            raise BenchmarkRecordError(f"METRIC_MUST_BE_INTEGER:{key}")
    return record


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    records = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BenchmarkRecordError(f"INVALID_JSONL_LINE:{line_number}") from exc
            try:
                records.append(validate_record(value))
            except BenchmarkRecordError as exc:
                raise BenchmarkRecordError(f"LINE_{line_number}:{exc}") from exc
    return records


def score_records(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    seen = set()
    for raw in records:
        record = validate_record(raw)
        key = (record["case_id"], record["condition"], record["model_id"])
        if key in seen:
            raise BenchmarkRecordError("DUPLICATE_CASE_CONDITION_MODEL")
        seen.add(key)
        groups[(record["condition"], record["model_id"])].append(record)

    summaries = []
    for (condition, model_id), items in sorted(groups.items()):
        criteria: dict[str, dict[str, int]] = defaultdict(lambda: {"n": 0, "correct": 0})
        operational: dict[str, list[float]] = defaultdict(list)
        for item in items:
            for criterion, expected in item["expected"].items():
                if expected is None:
                    continue
                criteria[criterion]["n"] += 1
                if item["observed"][criterion] == expected:
                    criteria[criterion]["correct"] += 1
            for metric, value in item.get("metrics", {}).items():
                if value is not None:
                    operational[metric].append(float(value))
        criterion_results = {
            name: {
                "n": values["n"],
                "correct": values["correct"],
                "accuracy": values["correct"] / values["n"] if values["n"] else None,
            }
            for name, values in sorted(criteria.items())
        }
        metric_results = {
            name: {
                "n": len(values),
                "mean": sum(values) / len(values) if values else None,
                "median": median(values) if values else None,
            }
            for name, values in sorted(operational.items())
        }
        summaries.append({
            "condition": condition,
            "model_id": model_id,
            "cases": len(items),
            "criteria": criterion_results,
            "operational_metrics": metric_results,
        })

    return {
        "schema_version": "repo-instruction-benchmark-score-v0.1",
        "record_count": len(seen),
        "groups": summaries,
        "interpretation_limit": (
            "Scores are label agreement against supplied expected labels. "
            "They do not establish label independence, benchmark validity, "
            "causal improvement, or general model quality."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_jsonl", help="Run records with expected and observed labels")
    parser.add_argument("--output", help="Optional output JSON path; defaults to stdout")
    args = parser.parse_args()
    result = score_records(read_jsonl(args.input_jsonl))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
