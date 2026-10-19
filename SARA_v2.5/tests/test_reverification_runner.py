from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_identity import compute_content_digest
from reverification_runner import (
    ReverificationExecutionError,
    SelectiveReverificationRunner,
    compute_evidence_digest,
)
from provenance_ledger import ProvenanceEventLedger



SCOPE = {
    "population": "adults",
    "setting": "one hospital",
    "time_range": "2020-2024",
    "modality": "observational",
    "outcome": "readmission",
    "causal_strength": "association",
}
EVIDENCE = [{"id": "E1", "provenance_id": "SOURCE-PROV-1", "text": "Source evidence"}]
EVIDENCE_DIGEST = compute_evidence_digest(EVIDENCE)


def revision(claim_id="C1", revision_id="R2", text="Claim text."):
    return {
        "claim_id": claim_id,
        "revision_id": revision_id,
        "text": text,
        "scope": dict(SCOPE),
        "content_digest": compute_content_digest(text, SCOPE),
    }


def plan(prior_status="VERIFIED", prior_known=True, claim_id="C1", revision_id="R2"):
    return {
        "plan_status": "PLANNED_NOT_EXECUTED",
        "impacted_claims": [{
            "claim_id": claim_id,
            "prior_verification_status": prior_status,
            "prior_status_known": prior_known,
            "review_state": "REQUIRES_REVERIFICATION",
            "trigger": "DEPENDENCY_CHANGED",
            "triggering_changed_node_ids": ["E1"],
            "execution_status": "PLANNED_NOT_EXECUTED",
        }],
    }


def prior_binding(claim_id="C1", status="VERIFIED"):
    return {
        "claim_id": claim_id,
        "revision_id": "R1",
        "content_digest": "OLD-CLAIM-DIGEST",
        "evidence_digest": "OLD-EVIDENCE-DIGEST",
        "verifier_revision": "verify-0",
        "verification_contract_revision": "contract-0",
        "verification_status": status,
    }


def valid_result(request, status="VERIFIED"):
    return {
        "claim_id": request["claim_id"],
        "revision_id": request["revision_id"],
        "content_digest": request["content_digest"],
        "evidence_digest": request["evidence_digest"],
        "verifier_revision": request["verifier_revision"],
        "verification_contract_revision": request["verification_contract_revision"],
        "verification_status": status,
        "external_result_id": "EXT-RESULT-1",
        "external_result_provenance_ids": ["EXTERNAL-RESULT-PROV-1"],
    }


def execute(verify, *, selected_plan=None, selected_revision=None,
            selected_evidence=None, selected_prior=None, selected_digest=None,
            ledger=None):
    selected_plan = selected_plan or plan()
    selected_revision = selected_revision or revision()
    selected_evidence = selected_evidence if selected_evidence is not None else EVIDENCE
    selected_prior = selected_prior if selected_prior is not None else prior_binding()
    selected_digest = selected_digest or compute_evidence_digest(selected_evidence)
    return SelectiveReverificationRunner(
        verify,
        verifier_revision="verify-1",
        verification_contract_revision="contract-1",
        ledger=ledger,
    ).execute(
        plan=selected_plan,
        claim_revisions={selected_revision["claim_id"]: selected_revision},
        evidence_by_claim={selected_revision["claim_id"]: selected_evidence},
        prior_bindings=(
            {selected_revision["claim_id"]: selected_prior}
            if selected_prior is not None else {}
        ),
        current_evidence_digests={selected_revision["claim_id"]: selected_digest},
        timeout_seconds=5,
    )


def test_successful_verification_is_a_proposal_not_an_automatic_status_change():
    def verify(request, timeout):
        assert timeout == 5
        return valid_result(request, "VERIFIED")

    result = execute(verify)
    item = result["results"][0]
    assert item["execution_status"] == "SUCCEEDED"
    assert item["proposed_verification_status"] == "VERIFIED"
    assert item["prior_verification_status"] == "VERIFIED"
    assert item["commit_status"] == "NOT_COMMITTED"
    assert result["committed_claim_statuses"] == {}
    assert item["truthfulness_status"] == "UNASSESSED"
    assert item["is_evidence"] is False
    assert result["executed_claim_ids"] == ["C1"]


def test_timeout_keeps_old_status_and_does_not_propose_negative_finding():
    def verify(_request, _timeout):
        raise TimeoutError("timeout")

    result = execute(verify)
    item = result["results"][0]
    assert item["execution_status"] == "TIMEOUT"
    assert item["failure_code"] == "VERIFICATION_PROVIDER_TIMEOUT"
    assert item["prior_verification_status"] == "VERIFIED"
    assert item["proposed_verification_status"] is None
    assert item["commit_status"] == "NOT_COMMITTED"
    assert item["truthfulness_status"] == "UNASSESSED"


def test_provider_exception_is_not_converted_to_claim_contradiction():
    def verify(_request, _timeout):
        raise RuntimeError("private provider error")

    result = execute(verify)
    item = result["results"][0]
    assert item["execution_status"] == "FAILED"
    assert item["failure_code"] == "VERIFICATION_PROVIDER_EXCEPTION:RuntimeError"
    assert item["proposed_verification_status"] is None
    assert "private provider error" not in str(result)


def test_output_missing_required_fields_is_incomplete():
    result = execute(lambda _request, _timeout: {"claim_id": "C1"})
    item = result["results"][0]
    assert item["execution_status"] == "INCOMPLETE"
    assert item["failure_code"] == "VERIFICATION_OUTPUT_MISSING_REQUIRED_FIELDS"


@pytest.mark.parametrize(
    "field, value",
    [
        ("claim_id", "OTHER"),
        ("revision_id", "R-OTHER"),
        ("content_digest", "OTHER-DIGEST"),
        ("evidence_digest", "OTHER-EVIDENCE"),
        ("verifier_revision", "verify-0"),
        ("verification_contract_revision", "contract-0"),
    ],
)
def test_verification_output_binding_mismatch_is_rejected(field, value):
    def verify(request, _timeout):
        result = valid_result(request)
        result[field] = value
        return result

    item = execute(verify)["results"][0]
    assert item["execution_status"] == "INVALID_OUTPUT"
    assert item["failure_code"] == "VERIFICATION_OUTPUT_BINDING_MISMATCH"
    assert item["commit_status"] == "NOT_COMMITTED"


def test_unknown_verification_status_is_rejected():
    item = execute(lambda request, _timeout: valid_result(request, "CERTAIN"))["results"][0]
    assert item["execution_status"] == "INVALID_OUTPUT"
    assert item["failure_code"] == "INVALID_VERIFICATION_STATUS"


def test_result_provenance_is_required_and_cannot_reuse_input_provenance():
    def missing(request, _timeout):
        return valid_result(request) | {"external_result_provenance_ids": []}

    item = execute(missing)["results"][0]
    assert item["execution_status"] == "INCOMPLETE"
    assert item["failure_code"] == "EXTERNAL_RESULT_PROVENANCE_REQUIRED"

    def reused(request, _timeout):
        return valid_result(request) | {
            "external_result_provenance_ids": ["SOURCE-PROV-1"]
        }

    item = execute(reused)["results"][0]
    assert item["execution_status"] == "INVALID_OUTPUT"
    assert item["failure_code"] == "INPUT_PROVENANCE_REUSED_AS_RESULT_PROVENANCE"


def test_changed_evidence_digest_is_recomputed_before_provider_invocation():
    invoked = False

    def verify(request, _timeout):
        nonlocal invoked
        invoked = True
        return valid_result(request)

    item = execute(verify, selected_digest="NOT-THE-CURRENT-EVIDENCE-DIGEST")["results"][0]
    assert item["execution_status"] == "INVALID_OUTPUT"
    assert item["failure_code"] == "CURRENT_EVIDENCE_DIGEST_MISMATCH"
    assert invoked is False


def test_stale_claim_content_digest_is_rejected_before_provider_invocation():
    invoked = False

    def verify(request, _timeout):
        nonlocal invoked
        invoked = True
        return valid_result(request)

    bad = revision()
    bad["content_digest"] = "STALE-DIGEST"
    item = execute(verify, selected_revision=bad)["results"][0]
    assert item["execution_status"] == "INVALID_OUTPUT"
    assert item["failure_code"] == "CURRENT_CLAIM_DIGEST_MISMATCH"
    assert invoked is False


def test_first_time_claim_without_prior_binding_can_be_executed():
    def verify(request, _timeout):
        return valid_result(request, "UNVERIFIED")

    result = execute(
        verify,
        selected_plan=plan(None, False),
        selected_prior=None,
    )
    item = result["results"][0]
    assert item["execution_status"] == "SUCCEEDED"
    assert item["prior_status_known"] is False
    assert item["prior_verification_status"] is None
    assert item["proposed_verification_status"] == "UNVERIFIED"
    assert item["commit_status"] == "NOT_COMMITTED"


def test_prior_status_must_match_the_impact_plan():
    item = execute(
        lambda request, _timeout: valid_result(request),
        selected_prior=prior_binding(status="UNVERIFIED"),
    )["results"][0]
    assert item["execution_status"] == "INVALID_OUTPUT"
    assert item["failure_code"] == "PRIOR_BINDING_STATUS_MISMATCH"


def test_non_executable_plan_is_rejected():
    with pytest.raises(ReverificationExecutionError, match="REVERIFICATION_PLAN_NOT_EXECUTABLE"):
        execute(lambda _request, _timeout: {} , selected_plan={"plan_status": "COMPLETED"})


def test_only_impacted_claim_is_sent_to_verifier():
    calls = []

    def verify(request, _timeout):
        calls.append(request["claim_id"])
        return valid_result(request)

    full_plan = plan()
    full_plan["impacted_claims"].append({
        "claim_id": "C2",
        "prior_verification_status": "PARTIALLY_VERIFIED",
        "prior_status_known": True,
        "review_state": "REQUIRES_REVERIFICATION",
        "trigger": "DEPENDENCY_CHANGED",
        "triggering_changed_node_ids": ["E1"],
        "execution_status": "PLANNED_NOT_EXECUTED",
    })
    result = execute(verify, selected_plan=full_plan)
    assert calls == ["C1"]
    assert result["failed_claim_ids"] == ["C2"]
    assert result["results"][1]["failure_code"] == "CURRENT_CLAIM_REVISION_MISSING"


def test_successful_reverification_proposal_is_logged_but_not_committed():
    ledger = ProvenanceEventLedger()
    result = execute(
        lambda request, _timeout: valid_result(request, "VERIFIED"),
        ledger=ledger,
    )
    assert ledger.verify_chain()["valid"] is True
    assert len(ledger.events) == 1
    event = ledger.events[0]
    assert event["event_type"] == "VERIFICATION_RESULT_PROPOSED"
    replay = ledger.replay_claim("C1")
    assert replay["committed_verification_status"] is None
    assert replay["proposed_results"] == [{
        "event_id": event["event_id"],
        "revision_id": "R2",
        "payload": event["payload"],
    }]
    assert result["results"][0]["commit_status"] == "NOT_COMMITTED"
    assert result["provenance_event_ids"] == [event["event_id"]]


def test_failed_reverification_attempt_is_logged_separately_from_proposal():
    ledger = ProvenanceEventLedger()

    def timeout(_request, _timeout):
        raise TimeoutError("do not persist provider details")

    result = execute(timeout, ledger=ledger)
    event = ledger.events[0]
    assert event["event_type"] == "REVERIFICATION_ATTEMPT_COMPLETED"
    assert event["payload"]["execution_status"] == "TIMEOUT"
    assert "do not persist provider details" not in ledger.to_jsonl()
    assert result["results"][0]["commit_status"] == "NOT_COMMITTED"
    assert ledger.verify_chain()["valid"] is True
