from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from promotion_gate import REQUIRED_CI_JOBS, REQUIRED_READINESS_FIELDS, evaluate_canonical_promotion


def case(case_id="C-001", decisions=("PASS", "PASS")):
    return {
        "case_id": case_id,
        "label_status": "INDEPENDENTLY_ADJUDICATED",
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
            {"status": "RESOLVED", "resolver_id": "resolver-C",
             "rationale": "Recorded resolution after comparing both justifications."}
            if decisions[0] != decisions[1] else None
        ),
    }


def complete_evidence():
    head = "test-head-sha"
    return {
        "head_sha": head,
        "ci": {
            "head_sha": head,
            "conclusion": "success",
            "jobs": {job: "success" for job in REQUIRED_CI_JOBS},
        },
        "readiness": {field: "VERIFIED" for field in REQUIRED_READINESS_FIELDS},
        "benchmark": {
            "dataset_status": "INDEPENDENTLY_ADJUDICATED",
            "cases": [case("C-001"), case("C-002", ("PASS", "REQUIRES_REVIEW"))],
            "comparison_status": "PASS",
            "metric_decisions": [
                {"metric": "false_positive_rate", "status": "PASS", "protocol_revision": "P1"},
                {"metric": "missed_issue_rate", "status": "PASS", "protocol_revision": "P1"},
                {"metric": "stale_reuse_incidents", "status": "PASS", "protocol_revision": "P1"},
                {"metric": "provenance_completeness", "status": "PASS", "protocol_revision": "P1"},
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
        (Path(__file__).resolve().parent / "benchmark" / "preflight_cases.json")
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


def test_missing_required_ci_job_blocks_promotion():
    evidence = complete_evidence()
    del evidence["ci"]["jobs"]["v2.5-provenance-ledger"]
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(
        item.get("detail", "").startswith("v2.5-provenance-ledger:")
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


def test_root_canonical_version_must_not_be_promoted_implicitly():
    evidence = complete_evidence()
    evidence["documentation"]["root_current_version"] = "v2.4"
    evidence["documentation"]["v2_5_release_status"] = "PROTOTYPE"
    result = evaluate_canonical_promotion(evidence)
    assert result["status"] == "PROMOTION_BLOCKED"
    assert any(item["code"] == "ROOT_CANONICAL_VERSION_NOT_V2_5" for item in result["blockers"])
