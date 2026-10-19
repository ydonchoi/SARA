from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from promotion_gate import (
    REQUIRED_BENCHMARK_SUITES,
    REQUIRED_CI_SUITES,
    REQUIRED_READINESS_FIELDS,
    evaluate_canonical_promotion,
)


def case(case_id="C-001", decisions=("PASS", "PASS"), suite="logical_audit"):
    resolved_label = decisions[0]
    return {
        "case_id": case_id,
        "suite": suite,
        "label_status": "INDEPENDENTLY_ADJUDICATED",
        "reference_label": resolved_label,
        "adjudications": [
            {
                "reviewer_id": "reviewer-A",
                "independent_review": True,
                "decision": decisions[0],
                "rationale": "Reviewed against the source record and protocol.",
            },
            {
                "reviewer_id": "reviewer-B",
                "independent_review": True,
                "decision": decisions[1],
                "rationale": "Independently reviewed against the same protocol.",
            },
        ],
        "disagreement_resolution": (
            {
                "status": "RESOLVED",
                "resolver_id": "resolver-C",
                "decision": resolved_label,
                "rationale": "Recorded resolution after comparing both justifications.",
            }
            if decisions[0] != decisions[1] else None
        ),
    }


def complete_evidence():
    head = "test-head-sha"
    suites = sorted(REQUIRED_BENCHMARK_SUITES)
    benchmark_cases = [
        case(
            f"C-{index + 1:03d}",
            ("PASS", "REQUIRES_REVIEW") if index == 1 else ("PASS", "PASS"),
            suites[index % len(suites)],
        )
        for index in range(18)
    ]
    return {
        "head_sha": head,
        "ci": {
            "head_sha": head,
            "conclusion": "success",
            "suites": {suite: "success" for suite in REQUIRED_CI_SUITES},
        },
        "readiness": {field: "VERIFIED" for field in REQUIRED_READINESS_FIELDS},
        "benchmark": {
            "dataset_status": "INDEPENDENTLY_ADJUDICATED",
            "cases": benchmark_cases,
            "comparison_status": "PASS",
            "comparison_runs": {
                "v2.3_baseline": {"run_id": "run-v23", "result_artifact_id": "artifact-v23"},
                "v2.4_no_evaluator": {"run_id": "run-v24-control", "result_artifact_id": "artifact-v24-control"},
                "v2.4_selective_evaluator": {"run_id": "run-v24-selective", "result_artifact_id": "artifact-v24-selective"},
            },
            "metric_decisions": [
                {"metric": "false_positive_rate", "status": "PASS", "observed_value": 0.05, "threshold": 0.10, "direction": "MAXIMUM", "protocol_revision": "P1", "artifact_ref": "artifact-fp"},
                {"metric": "missed_issue_rate", "status": "PASS", "observed_value": 0.10, "threshold": 0.15, "direction": "MAXIMUM", "protocol_revision": "P1", "artifact_ref": "artifact-missed"},
                {"metric": "stale_reuse_incidents", "status": "PASS", "observed_value": 0, "threshold": 0, "direction": "MAXIMUM", "protocol_revision": "P1", "artifact_ref": "artifact-stale"},
                {"metric": "provenance_completeness", "status": "PASS", "observed_value": 0.99, "threshold": 0.95, "direction": "MINIMUM", "protocol_revision": "P1", "artifact_ref": "artifact-provenance"},
            ],
        },
        "documentation": {
            "root_current_version": "v2.5",
            "v2_5_release_status": "ACTIVE_CANONICAL",
        },
        "open_blockers": [],
    }


def test_full_evidence_is_approved_but_gate_does_not_modify_canonical_state():
    result = evaluate_canonical_promotion(complete_evidence())
    assert result["status"] == "PROMOTION_APPROVED"
    assert result["blockers"] == []
    assert result["canonical_state_changed"] is False
    assert result["is_evidence"] is False


def test_actual_draft_preflight_fixture_blocks_promotion_even_when_other_gates_pass():
    evidence = complete_evidence()
    fixture = json.loads(
        (Path(__file__).resolve().parents[1] / "benchmark" / "preflight_cases.json")
        .read_text(encoding="utf-8")
    )
    evidence["benchmark"]["dataset_status"] = fixture["status"]
    evidence["benchmark"]["cases"] = fixture["cases"]
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        blocker["code"] == "BENCHMARK_NOT_INDEPENDENTLY_ADJUDICATED"
        for blocker in result["blockers"]
    )


def test_ci_head_mismatch_blocks_promotion():
    evidence = complete_evidence()
    evidence["ci"]["head_sha"] = "older-head"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "CI_HEAD_MISMATCH" for item in result["blockers"])


def test_missing_required_ci_suite_blocks_promotion():
    evidence = complete_evidence()
    del evidence["ci"]["suites"]["v25_provenance_ledger"]
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        item.get("detail", "").startswith("v25_provenance_ledger:")
        for item in result["blockers"]
    )


def test_unverified_runtime_readiness_blocks_promotion():
    evidence = complete_evidence()
    evidence["readiness"]["external_evaluator_integration_status"] = "NOT_CONFIGURED"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        item.get("detail", "").startswith("external_evaluator_integration_status:")
        for item in result["blockers"]
    )


def test_one_independent_adjudicator_is_not_enough():
    evidence = complete_evidence()
    evidence["benchmark"]["cases"][0]["adjudications"].pop()
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        item["code"] == "TWO_INDEPENDENT_ADJUDICATIONS_REQUIRED"
        for item in result["blockers"]
    )


def test_disagreement_requires_an_explicit_resolution_record():
    evidence = complete_evidence()
    evidence["benchmark"]["cases"][1]["disagreement_resolution"] = None
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        item["code"] == "ADJUDICATOR_DISAGREEMENT_UNRESOLVED"
        for item in result["blockers"]
    )


def test_benchmark_must_meet_minimum_case_count_and_required_suite_coverage():
    evidence = complete_evidence()
    evidence["benchmark"]["cases"] = evidence["benchmark"]["cases"][:10]
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "BENCHMARK_CASE_COUNT_BELOW_MINIMUM" for item in result["blockers"])

    evidence = complete_evidence()
    evidence["benchmark"]["cases"][0]["suite"] = "unregistered_suite"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "BENCHMARK_CASE_SUITE_UNKNOWN" for item in result["blockers"])


def test_unpassed_metrics_and_missing_open_blocker_declaration_fail_closed():
    evidence = complete_evidence()
    evidence["benchmark"]["metric_decisions"][0]["status"] = "UNASSESSED"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "BENCHMARK_METRIC_ACCEPTANCE_NOT_PASSED" for item in result["blockers"])

    evidence = complete_evidence()
    del evidence["open_blockers"]
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "OPEN_BLOCKERS_REQUIRED" for item in result["blockers"])


def test_reference_label_must_match_independent_adjudication():
    evidence = complete_evidence()
    evidence["benchmark"]["cases"][0]["reference_label"] = "UNVERIFIED"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "BENCHMARK_REFERENCE_LABEL_MISMATCH" for item in result["blockers"])


def test_metric_pass_must_be_supported_by_observed_value_and_predeclared_threshold():
    evidence = complete_evidence()
    evidence["benchmark"]["metric_decisions"][0]["observed_value"] = 0.25
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "BENCHMARK_METRIC_THRESHOLD_NOT_MET" for item in result["blockers"])


def test_comparison_claim_requires_run_ids_and_result_artifacts():
    evidence = complete_evidence()
    del evidence["benchmark"]["comparison_runs"]["v2.4_selective_evaluator"]
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        item.get("detail") == "v2.4_selective_evaluator"
        and item["code"] == "BASELINE_COMPARISON_RUN_EVIDENCE_REQUIRED"
        for item in result["blockers"]
    )


def test_root_canonical_version_must_not_be_promoted_implicitly():
    evidence = complete_evidence()
    evidence["documentation"]["root_current_version"] = "v2.4"
    evidence["documentation"]["v2_5_release_status"] = "PROTOTYPE"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "ROOT_CANONICAL_VERSION_NOT_V2_5" for item in result["blockers"])
