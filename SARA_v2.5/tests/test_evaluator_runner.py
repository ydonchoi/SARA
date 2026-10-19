from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_identity import compute_content_digest
from evaluator_runner import EvaluatorInvocationError, EvaluatorRunner
from provenance_ledger import ProvenanceEventLedger


REQUEST = {
    "request_id": "REQ-1",
    "claim_id": "C1",
    "claim_revision_id": "R1",
    "claim_text": "The policy reduced the outcome.",
    "input_revision_digest": compute_content_digest("The policy reduced the outcome.", {"population": "adults"}),
    "scope": {"population": "adults"},
    "premises": [{"id": "P1", "text": "The outcome decreased after the policy."}],
    "evidence": [{"id": "E1"}],
    "provenance_ids": ["INPUT-PROV-1"],
}


def runner(provider):
    return EvaluatorRunner(
        provider,
        evaluator_id="JEV",
        evaluator_revision="jev-1.2",
        rubric_revision="rubric-3",
    )


def good_response(request):
    return {
        "claim_id": request["claim_id"],
        "claim_revision_id": request["claim_revision_id"],
        "input_revision_digest": request["input_revision_digest"],
        "signal_status": "ISSUE_CANDIDATE",
        "rationale": "The premise establishes temporal order, not causation.",
        "related_node_ids": ["C1", "P1"],
        "evidence_ids": ["E1"],
        "provenance_ids": ["EXT-EVAL-1"],
    }


def test_runner_invokes_provider_and_keeps_signal_out_of_evidence_and_verification():
    captured = {}

    def provider(payload, timeout):
        captured["payload"] = payload
        captured["timeout"] = timeout
        return good_response(payload)

    result = runner(provider).run(
        REQUEST,
        timeout_seconds=5,
        known_node_ids=("C1", "P1"),
        known_evidence_ids=("E1",),
    )

    assert result["execution_status"] == "SUCCEEDED"
    assert result["signal"]["signal_status"] == "ISSUE_CANDIDATE"
    assert result["signal"]["is_evidence"] is False
    assert "verification_status" not in result
    assert result["commit_status"] == "NOT_COMMITTED"
    assert result["signal"]["input_revision_digest"] == compute_content_digest(REQUEST["claim_text"], REQUEST["scope"])
    assert result["signal"]["provenance_ids"] == [
        "EXT-EVAL-1", "EVALUATOR-RUN:REQ-1"
    ]
    assert captured["timeout"] == 5.0
    assert captured["payload"]["rubric_revision"] == "rubric-3"
    assert captured["payload"]["claim_revision_id"] == "R1"


def test_timeout_is_recorded_as_unavailable_signal_not_finding():
    def provider(_payload, _timeout):
        raise TimeoutError("provider timeout")

    result = runner(provider).run(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "TIMEOUT"
    assert result["signal"]["signal_status"] == "NOT_AVAILABLE"
    assert result["signal"]["review_required"] is True
    assert result["is_evidence"] is False
    assert result["commit_status"] == "NOT_COMMITTED"


def test_provider_exception_does_not_leak_message_into_research_finding():
    def provider(_payload, _timeout):
        raise RuntimeError("private provider response or secret")

    result = runner(provider).run(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "FAILED"
    assert result["failure_code"] == "EVALUATOR_PROVIDER_EXCEPTION:RuntimeError"
    assert "private provider response or secret" not in str(result)
    assert result["signal"]["signal_status"] == "NOT_AVAILABLE"


def test_non_object_provider_output_is_invalid_output():
    result = runner(lambda _payload, _timeout: ["not", "an", "object"]).run(
        REQUEST, timeout_seconds=1
    )
    assert result["execution_status"] == "INVALID_OUTPUT"
    assert result["failure_code"] == "EVALUATOR_OUTPUT_NOT_OBJECT"
    assert result["signal"]["signal_status"] == "NOT_AVAILABLE"


def test_missing_provider_fields_are_incomplete():
    result = runner(lambda _payload, _timeout: {"claim_id": "C1"}).run(
        REQUEST, timeout_seconds=1
    )
    assert result["execution_status"] == "INCOMPLETE"
    assert result["failure_code"] == "EVALUATOR_OUTPUT_MISSING_REQUIRED_FIELDS"


@pytest.mark.parametrize(
    "field, wrong_value",
    [
        ("claim_id", "OTHER"),
        ("claim_revision_id", "R-OLD"),
        ("input_revision_digest", "DIGEST-OLD"),
    ],
)
def test_output_bound_to_wrong_claim_revision_is_rejected(field, wrong_value):
    def provider(payload, _timeout):
        result = good_response(payload)
        result[field] = wrong_value
        return result

    result = runner(provider).run(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "INVALID_OUTPUT"
    assert result["failure_code"] == "EVALUATOR_OUTPUT_IDENTITY_MISMATCH"
    assert result["commit_status"] == "NOT_COMMITTED"


def test_unknown_node_or_evidence_reference_is_rejected():
    def provider(payload, _timeout):
        result = good_response(payload)
        result["related_node_ids"] = ["UNKNOWN-NODE"]
        return result

    result = runner(provider).run(
        REQUEST, timeout_seconds=1, known_node_ids=("C1", "P1"),
        known_evidence_ids=("E1",),
    )
    assert result["execution_status"] == "INVALID_OUTPUT"
    assert result["failure_code"].startswith("EVALUATOR_BOUNDARY_REJECTED:")


def test_unrecognised_signal_status_is_invalid_output():
    def provider(payload, _timeout):
        result = good_response(payload)
        result["signal_status"] = "CLAIM_VERIFIED"
        return result

    result = runner(provider).run(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "INVALID_OUTPUT"


@pytest.mark.parametrize(
    "timeout",
    [0, -1, float("inf"), float("nan"), True, "5"],
)
def test_invalid_timeout_is_rejected_before_provider_invocation(timeout):
    called = False

    def provider(_payload, _timeout):
        nonlocal called
        called = True
        return {}

    with pytest.raises(EvaluatorInvocationError, match="INVALID_EVALUATOR_TIMEOUT"):
        runner(provider).run(REQUEST, timeout_seconds=timeout)
    assert called is False


def test_stale_revision_digest_is_rejected_before_provider_invocation():
    called = False

    def provider(_payload, _timeout):
        nonlocal called
        called = True
        return {}

    with pytest.raises(EvaluatorInvocationError, match="EVALUATOR_INPUT_REVISION_DIGEST_MISMATCH"):
        runner(provider).run(
            {**REQUEST, "input_revision_digest": "OLD-DIGEST"},
            timeout_seconds=1,
        )
    assert called is False


def test_invalid_request_is_rejected_before_provider_invocation():
    called = False

    def provider(_payload, _timeout):
        nonlocal called
        called = True
        return {}

    with pytest.raises(EvaluatorInvocationError, match="EVALUATOR_CLAIM_REVISION_ID_REQUIRED"):
        runner(provider).run({**REQUEST, "claim_revision_id": " "}, timeout_seconds=1)
    assert called is False


def test_provider_cannot_mutate_caller_request():
    original = dict(REQUEST)

    def provider(payload, _timeout):
        payload["claim_id"] = "MUTATED"
        payload["scope"]["population"] = "MUTATED"
        payload["evidence"][0]["text"] = "MUTATED"
        payload["premises"][0]["text"] = "MUTATED"
        return good_response(REQUEST)

    runner(provider).run(REQUEST, timeout_seconds=1)
    assert REQUEST == original


def test_runner_records_execution_and_ledger_does_not_promote_evaluator_signal():
    ledger = ProvenanceEventLedger()
    result = EvaluatorRunner(
        lambda request, _timeout: good_response(request),
        evaluator_id="JEV", evaluator_revision="jev-1.2",
        rubric_revision="rubric-3", ledger=ledger,
    ).run(
        REQUEST, timeout_seconds=1,
        known_node_ids=("C1", "P1"), known_evidence_ids=("E1",),
    )
    assert result["provenance_event_id"]
    assert ledger.verify_chain()["valid"] is True
    replay = ledger.replay_claim("C1")
    assert replay["committed_verification_status"] is None
    assert replay["proposed_results"] == []
    assert [event["event_type"] for event in ledger.events] == [
        "CLAIM_REVISION_REGISTERED", "EVALUATOR_RUN_COMPLETED"
    ]
    evaluator_event = ledger.events[-1]
    assert evaluator_event["payload"]["evaluator_id"] == "JEV"
    assert evaluator_event["payload"]["evaluator_revision"] == "jev-1.2"
    assert evaluator_event["payload"]["rubric_revision"] == "rubric-3"


def test_runner_records_timeout_as_operational_provenance_not_a_claim_finding():
    ledger = ProvenanceEventLedger()

    def timeout_provider(_request, _timeout):
        raise TimeoutError("do not persist provider internals")

    result = EvaluatorRunner(
        timeout_provider,
        evaluator_id="JEV", evaluator_revision="jev-1.2",
        rubric_revision="rubric-3", ledger=ledger,
    ).run(REQUEST, timeout_seconds=1)
    assert result["execution_status"] == "TIMEOUT"
    event = ledger.events[-1]
    assert event["payload"]["execution_status"] == "TIMEOUT"
    assert event["payload"]["signal_status"] == "NOT_AVAILABLE"
    assert "do not persist provider internals" not in ledger.to_jsonl()
