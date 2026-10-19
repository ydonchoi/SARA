from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
V25_ROOT = REPO_ROOT / "SARA_v2.5"
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(V25_ROOT))

from internal_judgment_model import compute_judgment_input_digest
from sara_runtime import process_dialogue_turn


BASE_CONTENT = (
    "Sales rose after the campaign, therefore the campaign caused the increase."
)


def request():
    return {
        "request_id": "REQ-RT-1",
        "conversation_id": "CONV-1",
        "turn_id": "TURN-3",
        "content": BASE_CONTENT,
        "context": {"role": "assistant"},
        "claim_candidates": [
            {"id": "C-1", "text": "The campaign caused the increase."}
        ],
        "evidence": [],
        "provenance_ids": ["INPUT-PROV-1"],
        "requested_at": "2026-10-19T10:00:00Z",
        "environment": {"test": True},
    }


def generate_for(status="INFERENCE_PRESENT", confidence="HIGH", claim_refs=None, verification_need=None, external_check_need="NOT_REQUIRED"):
    def generate(_rubric, payload, timeout_seconds):
        assert timeout_seconds > 0
        detected = status == "INFERENCE_PRESENT"
        return {
            "request_id": payload["request_id"],
            "input_revision_digest": compute_judgment_input_digest(payload),
            "judgment_status": status,
            "verification_need": verification_need or ("REQUIRED" if detected else "NOT_REQUIRED"),
            "external_check_need": external_check_need,
            "inference_types": ["CAUSAL"] if detected else [],
            "basis_spans": ["therefore the campaign caused the increase"] if detected else [],
            "rationale": "The stated conclusion goes beyond a temporal association.",
            "uncertainty_reason": "Context is insufficient." if status == "AMBIGUOUS" else "",
            "confidence": confidence,
            "premise_refs": [],
            "claim_refs": list(claim_refs if claim_refs is not None else (["C-1"] if detected else [])),
            "evidence_ids": [],
            "provenance_ids": [],
        }
    return generate


def provider_result(**overrides):
    result = {
        "status": "SUCCEEDED",
        "external_result_id": "EXT-RESULT-1",
        "external_result_provenance_ids": ["EXT-PROV-1"],
        "verification_status": "UNVERIFIED",
        "findings": ["SOURCE_EVIDENCE_REQUIRED"],
        "uncertainty": "The provider did not establish claim truthfulness.",
    }
    result.update(overrides)
    return result


def test_callable_sara_runtime_automatically_verifies_claim_bound_to_inference():
    calls = []
    events = []

    def provider(payload):
        calls.append(payload)
        return provider_result()

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for(),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        event_sink=events.append,
    )

    assert result["judgment"]["judgment_status"] == "INFERENCE_PRESENT"
    assert result["activation_decision"]["activation_action"] == "SARA_SELECTIVE_VERIFICATION"
    assert result["pipeline_status"] == "ROUTE_EXECUTED"
    assert result["verification_provider_invoked"] is True
    assert len(calls) == 1
    # ProductionVerificationBackend receives the normalized provider payload;
    # the facade-level capability has already been validated and is not forwarded.
    assert calls[0]["request_id"] == "REQ-RT-1:C-1"
    assert calls[0]["claim"]["id"] == "C-1"
    assert calls[0]["claim"]["inference_level"] == "INFERENCE"
    assert calls[0]["claim"]["inference_basis"] == [
        "therefore the campaign caused the increase"
    ]
    assert result["claim_truth_assessed"] is False
    assert result["is_evidence"] is False
    assert result["verification_status_is_not_truthfulness"] is True
    assert result["audit_record_status"] == "RECORDED_BY_CONFIGURED_EVENT_SINK"
    assert events[0]["event_type"] == "SARA_DIALOGUE_TURN_PROCESSED"
    assert events[0]["is_evidence"] is False


def test_inference_without_bound_claim_candidate_routes_to_precheck():
    calls = {"verify": 0, "precheck": 0}

    def provider(_payload):
        calls["verify"] += 1
        return provider_result()

    def precheck(_request, judgment, decision):
        calls["precheck"] += 1
        assert judgment["judgment_status"] == "INFERENCE_PRESENT"
        assert decision["reason_code"] == "VERIFICATION_HAS_NO_BOUND_CLAIM_CANDIDATE"
        return {"status": "NEEDS_REVIEW"}

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for(claim_refs=[]),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        precheck=precheck,
    )

    assert calls == {"verify": 0, "precheck": 1}
    assert result["verification_provider_invoked"] is False
    assert result["route_execution"]["output"]["status"] == "NEEDS_REVIEW"


def test_ambiguous_judgment_routes_to_precheck_without_verifier_call():
    calls = {"verify": 0, "precheck": 0}

    def provider(_payload):
        calls["verify"] += 1
        return provider_result()

    def precheck(_request, _judgment, _decision):
        calls["precheck"] += 1
        return {"status": "REVIEW_QUEUED"}

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for("AMBIGUOUS", "MEDIUM"),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        precheck=precheck,
    )

    assert calls == {"verify": 0, "precheck": 1}
    assert result["activation_decision"]["activation_action"] == "SARA_PRECHECK_REVIEW"
    assert result["route_execution"]["output"]["status"] == "REVIEW_QUEUED"


def test_high_confidence_no_inference_skips_only_inference_triggered_route():
    calls = {"verify": 0, "precheck": 0}

    def provider(_payload):
        calls["verify"] += 1
        return provider_result()

    def precheck(*_args):
        calls["precheck"] += 1
        return {"status": "REVIEW_QUEUED"}

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for("NO_INFERENCE_DETECTED", "HIGH"),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        precheck=precheck,
    )

    assert calls == {"verify": 0, "precheck": 0}
    assert result["activation_decision"]["activation_action"] == "NO_INFERENCE_TRIGGER"
    assert result["pipeline_status"] == "NO_ROUTE_REQUIRED"
    assert result["verification_provider_invoked"] is False
    assert result["activation_decision"]["other_verification_routes_untouched"] is True


def test_model_failure_does_not_become_no_inference():
    calls = {"verify": 0, "precheck": 0}

    def fail_generate(*_args):
        raise TimeoutError("internal test timeout")

    def provider(_payload):
        calls["verify"] += 1
        return provider_result()

    def precheck(_request, judgment, decision):
        calls["precheck"] += 1
        assert judgment["judgment_status"] == "NOT_ASSESSED"
        assert decision["activation_action"] == "SARA_PRECHECK_REVIEW"
        return {"status": "REVIEW_QUEUED"}

    result = process_dialogue_turn(
        request(),
        judgment_generate=fail_generate,
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        precheck=precheck,
    )

    assert calls == {"verify": 0, "precheck": 1}
    assert result["judgment"]["execution_status"] == "TIMEOUT"
    assert result["activation_decision"]["activation_action"] == "SARA_PRECHECK_REVIEW"


def test_changed_claim_candidate_text_changes_the_judgment_digest():
    first = request()
    second = request()
    second["claim_candidates"][0]["text"] = "The increase caused the campaign."
    assert compute_judgment_input_digest(first) != compute_judgment_input_digest(second)


def test_invalid_evidence_container_routes_inference_to_precheck():
    calls = {"verify": 0, "precheck": 0}
    payload = request()
    payload["evidence"] = "not-a-list"

    def provider(_payload):
        calls["verify"] += 1
        return provider_result()

    def precheck(_request, _judgment, decision):
        calls["precheck"] += 1
        assert decision["reason_code"] == "INFERENCE_EVIDENCE_INPUT_INVALID"
        return {"status": "NEEDS_REVIEW"}

    result = process_dialogue_turn(
        payload,
        judgment_generate=generate_for(),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        precheck=precheck,
    )
    assert calls == {"verify": 0, "precheck": 1}
    assert result["verification_provider_invoked"] is False


def test_event_sink_failure_remains_visible_and_does_not_claim_recorded_audit():
    def provider(_payload):
        return provider_result()

    def failing_sink(_event):
        raise OSError("storage unavailable")

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for(),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
        event_sink=failing_sink,
    )
    assert result["audit_record_status"] == "FAILED"
    assert result["audit_record_error_type"] == "OSError"


def test_external_search_runs_for_direct_claim_without_inference_when_required():
    verify_calls = []
    search_calls = []

    def provider(payload):
        verify_calls.append(payload)
        return provider_result()

    def search(payload, timeout):
        search_calls.append((payload, timeout))
        return [{
            "url": "https://example.org/official-report",
            "title": "Official report",
            "snippet": "The report states the policy was announced yesterday.",
        }]

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for(
            "NO_INFERENCE_DETECTED", "HIGH", claim_refs=["C-1"],
            verification_need="REQUIRED", external_check_need="REQUIRED",
        ),
        verification_provider=provider,
        external_search_provider=search,
        model_id="sara-model",
        model_revision="runtime-test-double",
    )

    assert len(search_calls) == 1
    assert search_calls[0][0]["claim_id"] == "C-1"
    assert search_calls[0][1] > 0
    assert len(verify_calls) == 1
    evidence = verify_calls[0]["evidence"]
    assert len(evidence) == 1
    assert evidence[0]["evidence_kind"] == "EXTERNAL_SOURCE_CANDIDATE"
    assert evidence[0]["verification_status"] == "UNASSESSED"
    assert result["external_search_invoked"] is True
    assert result["verification_provider_invoked"] is True
    assert result["judgment"]["judgment_status"] == "NO_INFERENCE_DETECTED"
    assert verify_calls[0]["claim"]["inference_level"] == "FACT"


def test_required_external_search_without_provider_does_not_call_verifier():
    verify_calls = []

    def provider(payload):
        verify_calls.append(payload)
        return provider_result()

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for(
            "NO_INFERENCE_DETECTED", "HIGH", claim_refs=["C-1"],
            verification_need="REQUIRED", external_check_need="REQUIRED",
        ),
        verification_provider=provider,
        model_id="sara-model",
        model_revision="runtime-test-double",
    )

    assert verify_calls == []
    assert result["external_search_provider_configured"] is False
    assert result["verification_provider_invoked"] is False
    item = result["route_execution"]["output"]["verification_results"][0]
    assert item["execution_status"] == "BLOCKED"
    assert item["verification_status"] == "UNVERIFIED"
    assert item["error_code"] == "EXTERNAL_SEARCH_PROVIDER_NOT_CONFIGURED"


def test_no_external_results_does_not_call_verifier_or_claim_falsehood():
    verify_calls = []

    def provider(payload):
        verify_calls.append(payload)
        return provider_result()

    result = process_dialogue_turn(
        request(),
        judgment_generate=generate_for(
            "NO_INFERENCE_DETECTED", "HIGH", claim_refs=["C-1"],
            verification_need="REQUIRED", external_check_need="REQUIRED",
        ),
        verification_provider=provider,
        external_search_provider=lambda *_: [],
        model_id="sara-model",
        model_revision="runtime-test-double",
    )

    assert verify_calls == []
    item = result["route_execution"]["output"]["verification_results"][0]
    assert item["execution_status"] == "NO_EVIDENCE"
    assert item["verification_status"] == "UNVERIFIED"
    assert item["external_search_status"] == "NO_RESULTS"
    assert result["claim_truth_assessed"] is False
