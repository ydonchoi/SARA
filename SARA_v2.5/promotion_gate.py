"""SARA v2.5 canonical-promotion acceptance gate.

The gate verifies supplied promotion evidence; it does not obtain CI results or
independently adjudicate benchmark labels. Missing evidence is a blocker, not a
pass. Promotion is approved only when every explicit criterion is satisfied.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

REQUIRED_CI_SUITES = {
    "external_execution_contracts",
    "content_access",
    "review_resolution_provenance",
    "v24_epistemic_logical_audit",
    "v25_claim_identity_conflict",
    "v25_evaluator_boundary",
    "v25_evaluator_runner",
    "v25_selective_reverification",
    "v25_reverification_runner",
    "v25_provenance_ledger",
    "v25_verification_commit_gate",
    "v25_promotion_gate",
    "v25_preflight_coverage",
    "v25_preflight_json",
}
REQUIRED_BENCHMARK_SUITES = {
    "logical_audit",
    "claim_identity",
    "evidence_conflict",
    "evaluator_boundary",
    "evaluator_runner",
    "selective_reverification",
    "reverification_runner",
}
MINIMUM_ADJUDICATED_CASES = 18
REQUIRED_READINESS_FIELDS = {
    "external_evaluator_integration_status",
    "reverification_runtime_status",
    "provenance_storage_replay_status",
    "human_review_commit_gate_status",
    "schema_consistency_status",
    "documentation_consistency_status",
}
VERIFIED = "VERIFIED"


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def evaluate_canonical_promotion(evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Return PROMOTION_APPROVED only when all independently supplied gates pass."""
    blockers: list[dict[str, str]] = []
    if not isinstance(evidence, Mapping):
        return {
            "status": "PROMOTION_BLOCKED",
            "blockers": [{"code": "PROMOTION_EVIDENCE_MUST_BE_MAPPING"}],
            "is_evidence": False,
            "source": "SARA_CANONICAL_PROMOTION_GATE",
        }

    head_sha = evidence.get("head_sha")
    ci = evidence.get("ci")
    if not _is_nonempty_string(head_sha):
        blockers.append({"code": "CURRENT_HEAD_SHA_REQUIRED"})
    if not isinstance(ci, Mapping):
        blockers.append({"code": "CI_EVIDENCE_REQUIRED"})
    else:
        if not _is_nonempty_string(ci.get("head_sha")) or ci.get("head_sha") != head_sha:
            blockers.append({"code": "CI_HEAD_MISMATCH"})
        if ci.get("conclusion") != "success":
            blockers.append({"code": "CI_NOT_SUCCESSFUL"})
        suites = ci.get("suites")
        if not isinstance(suites, Mapping):
            blockers.append({"code": "CI_SUITE_RESULTS_REQUIRED"})
        else:
            for suite in sorted(REQUIRED_CI_SUITES):
                if suites.get(suite) != "success":
                    blockers.append({
                        "code": "REQUIRED_CI_SUITE_NOT_SUCCESSFUL",
                        "detail": f"{suite}:{suites.get(suite, 'MISSING')}",
                    })

    readiness = evidence.get("readiness")
    if not isinstance(readiness, Mapping):
        blockers.append({"code": "READINESS_EVIDENCE_REQUIRED"})
    else:
        for field in sorted(REQUIRED_READINESS_FIELDS):
            if readiness.get(field) != VERIFIED:
                blockers.append({
                    "code": "READINESS_GATE_NOT_VERIFIED",
                    "detail": f"{field}:{readiness.get(field, 'MISSING')}",
                })

    benchmark = evidence.get("benchmark")
    if not isinstance(benchmark, Mapping):
        blockers.append({"code": "BENCHMARK_EVIDENCE_REQUIRED"})
    else:
        if benchmark.get("dataset_status") != "INDEPENDENTLY_ADJUDICATED":
            blockers.append({"code": "BENCHMARK_NOT_INDEPENDENTLY_ADJUDICATED"})
        cases = benchmark.get("cases")
        if not isinstance(cases, list) or not cases:
            blockers.append({"code": "ADJUDICATED_BENCHMARK_CASES_REQUIRED"})
        else:
            if len(cases) < MINIMUM_ADJUDICATED_CASES:
                blockers.append({
                    "code": "BENCHMARK_CASE_COUNT_BELOW_MINIMUM",
                    "detail": f"{len(cases)}<{MINIMUM_ADJUDICATED_CASES}",
                })
            seen_case_ids = set()
            covered_suites = set()
            for index, case in enumerate(cases):
                where = str(case.get("case_id", f"index:{index}")) if isinstance(case, Mapping) else f"index:{index}"
                if not isinstance(case, Mapping):
                    blockers.append({"code": "BENCHMARK_CASE_MUST_BE_MAPPING", "detail": where})
                    continue
                suite = case.get("suite")
                if not _is_nonempty_string(suite):
                    blockers.append({"code": "BENCHMARK_CASE_SUITE_REQUIRED", "detail": where})
                elif suite not in REQUIRED_BENCHMARK_SUITES:
                    blockers.append({
                        "code": "BENCHMARK_CASE_SUITE_UNKNOWN",
                        "detail": f"{where}:{suite}",
                    })
                else:
                    covered_suites.add(suite)
                case_id = case.get("case_id")
                if not _is_nonempty_string(case_id):
                    blockers.append({"code": "BENCHMARK_CASE_ID_REQUIRED", "detail": where})
                elif case_id in seen_case_ids:
                    blockers.append({"code": "DUPLICATE_BENCHMARK_CASE_ID", "detail": case_id})
                else:
                    seen_case_ids.add(case_id)
                if case.get("label_status") != "INDEPENDENTLY_ADJUDICATED":
                    blockers.append({"code": "BENCHMARK_CASE_LABEL_NOT_ADJUDICATED", "detail": where})
                adjudications = case.get("adjudications")
                if not isinstance(adjudications, list):
                    blockers.append({"code": "CASE_ADJUDICATION_RECORDS_REQUIRED", "detail": where})
                    continue
                distinct_reviewers = set()
                decisions = set()
                valid_records = 0
                for record in adjudications:
                    if not isinstance(record, Mapping):
                        continue
                    reviewer = record.get("reviewer_id")
                    decision = record.get("decision")
                    rationale = record.get("rationale")
                    if (
                        _is_nonempty_string(reviewer)
                        and _is_nonempty_string(decision)
                        and _is_nonempty_string(rationale)
                        and record.get("independent_review") is True
                    ):
                        valid_records += 1
                        distinct_reviewers.add(reviewer)
                        decisions.add(decision)
                if len(distinct_reviewers) < 2 or valid_records < 2:
                    blockers.append({
                        "code": "TWO_INDEPENDENT_ADJUDICATIONS_REQUIRED",
                        "detail": where,
                    })
                if len(decisions) > 1:
                    resolution = case.get("disagreement_resolution")
                    if not isinstance(resolution, Mapping) or (
                        resolution.get("status") != "RESOLVED"
                        or not _is_nonempty_string(resolution.get("resolver_id"))
                        or not _is_nonempty_string(resolution.get("rationale"))
                    ):
                        blockers.append({
                            "code": "ADJUDICATOR_DISAGREEMENT_UNRESOLVED",
                            "detail": where,
                        })
            missing_suites = REQUIRED_BENCHMARK_SUITES - covered_suites
            if missing_suites:
                blockers.append({
                    "code": "BENCHMARK_SUITE_COVERAGE_INCOMPLETE",
                    "detail": ",".join(sorted(missing_suites)),
                })
        if benchmark.get("comparison_status") != "PASS":
            blockers.append({"code": "BASELINE_COMPARISON_NOT_PASSED"})
        metric_decisions = benchmark.get("metric_decisions")
        if not isinstance(metric_decisions, list) or not metric_decisions:
            blockers.append({"code": "BENCHMARK_METRIC_DECISIONS_REQUIRED"})
        elif any(
            not isinstance(item, Mapping) or item.get("status") != "PASS"
            for item in metric_decisions
        ):
            blockers.append({"code": "BENCHMARK_METRIC_ACCEPTANCE_NOT_PASSED"})

    documentation = evidence.get("documentation")
    if not isinstance(documentation, Mapping):
        blockers.append({"code": "DOCUMENTATION_VERSION_EVIDENCE_REQUIRED"})
    else:
        if documentation.get("root_current_version") != "v2.5":
            blockers.append({"code": "ROOT_CANONICAL_VERSION_NOT_V2_5"})
        if documentation.get("v2_5_release_status") != "ACTIVE_CANONICAL":
            blockers.append({"code": "V2_5_RELEASE_STATUS_NOT_CANONICAL"})

    unresolved = evidence.get("open_blockers")
    if unresolved is None:
        blockers.append({"code": "OPEN_BLOCKERS_REQUIRED"})
    elif not isinstance(unresolved, list):
        blockers.append({"code": "OPEN_BLOCKERS_MUST_BE_LIST"})
    else:
        for item in unresolved:
            if _is_nonempty_string(item):
                blockers.append({"code": "UNRESOLVED_BLOCKER", "detail": item})
            else:
                blockers.append({"code": "INVALID_BLOCKER_RECORD"})

    status = "PROMOTION_APPROVED" if not blockers else "PROMOTION_BLOCKED"
    return {
        "status": status,
        "candidate_version": "v2.5",
        "head_sha": head_sha if _is_nonempty_string(head_sha) else None,
        "blockers": blockers,
        "blocker_count": len(blockers),
        "canonical_state_changed": False,
        "is_evidence": False,
        "source": "SARA_CANONICAL_PROMOTION_GATE",
    }
