import json
from pathlib import Path


FIXTURE = Path(__file__).resolve().parents[1] / "benchmark" / "preflight_cases.json"


def load_fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_preflight_seed_set_is_explicitly_draft_not_gold():
    data = load_fixture()
    assert data["status"] == "DRAFT_NOT_INDEPENDENTLY_ADJUDICATED"
    assert all(case["label_status"] == "DRAFT" for case in data["cases"])


def test_preflight_case_ids_are_unique_and_outcomes_are_explicit():
    data = load_fixture()
    cases = data["cases"]
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert all(
        any(key in case for key in (
            "expected_action",
            "expected_review_state",
            "expected_conflict_status",
        ))
        for case in cases
    )


def test_preflight_covers_logical_audit_identity_and_evidence_conflict():
    data = load_fixture()
    suites = {case["suite"] for case in data["cases"]}
    assert suites == {"logical_audit", "claim_identity", "evidence_conflict"}


def test_claim_identity_cases_bind_verification_contract_revision():
    data = load_fixture()
    cases = [case for case in data["cases"] if case["suite"] == "claim_identity"]
    assert cases
    assert all(case.get("current_contract_revision") for case in cases)
    assert all(
        case.get("prior_binding", {}).get("verification_contract_revision")
        for case in cases
    )
    contract_drift = next(case for case in cases if case["case_id"] == "CV-002")
    assert contract_drift["current_contract_revision"] != (
        contract_drift["prior_binding"]["verification_contract_revision"]
    )
    assert contract_drift["expected_review_state"] == "REQUIRES_REVERIFICATION"
    assert contract_drift["expected_reuse_allowed"] is False


def test_conflict_cases_never_promote_claim_truth_status():
    data = load_fixture()
    conflict_cases = [
        case for case in data["cases"] if case["suite"] == "evidence_conflict"
    ]
    assert len(conflict_cases) >= 3
    assert all(
        case["expected_claim_verification_status"] == "UNASSESSED"
        for case in conflict_cases
    )
