"""G1: frozen cases must route identically through the v2.5 dialogue runtime and v3,
and v3 must carry the v2.4 epistemic assessment unchanged."""
from __future__ import annotations

import copy

import pytest

from SARA_v3.runtime import SARA_v3Runtime
from SARA_v3.verification import verify_claim_from_sources
from internal_judgment_model import compute_judgment_input_digest
from sara_runtime import _run_v24_assessment, process_dialogue_turn

CONTENT = "Sales rose after the campaign, therefore the campaign caused the increase."
CLAIM_TEXT = "The campaign caused the increase."


def frozen_request():
    return {
        "request_id": "REQ-G1", "conversation_id": "CONV-G1", "turn_id": "TURN-1",
        "content": CONTENT, "context": {"role": "assistant"},
        "claim_candidates": [{"id": "C-1", "text": CLAIM_TEXT}],
        "evidence": [], "provenance_ids": ["INPUT-PROV-1"],
    }


def judgment(status="INFERENCE_PRESENT", confidence="HIGH", claim_refs=("C-1",), stale=False, fail=False):
    def generate(_rubric, payload, _timeout):
        if fail:
            raise TimeoutError("frozen-case timeout")
        detected = status == "INFERENCE_PRESENT"
        digest = compute_judgment_input_digest(payload)
        return {
            "request_id": payload["request_id"],
            "input_revision_digest": ("0" * 64) if stale else digest,
            "judgment_status": status,
            "inference_types": ["CAUSAL"] if detected else [],
            "basis_spans": ["therefore the campaign caused the increase"] if detected else [],
            "rationale": "The stated conclusion goes beyond a temporal association.",
            "uncertainty_reason": "Context is insufficient." if status == "AMBIGUOUS" else "",
            "confidence": confidence,
            "premise_refs": [], "claim_refs": list(claim_refs) if detected else [],
            "evidence_ids": [], "provenance_ids": [],
        }
    return generate


FROZEN_CASES = {
    "bound_high_confidence_inference": judgment(),
    "unbound_inference": judgment(claim_refs=()),
    "ambiguous": judgment("AMBIGUOUS", "MEDIUM"),
    "no_inference_high_confidence": judgment("NO_INFERENCE_DETECTED", "HIGH"),
    "medium_confidence_inference": judgment(confidence="MEDIUM"),
    "low_confidence_inference": judgment(confidence="LOW"),
    "stale_input_digest": judgment(stale=True),
    "model_timeout": judgment(fail=True),
}


def routing_signature(result):
    judged, decision = result["judgment"], result["activation_decision"]
    return {
        "judgment_status": judged.get("judgment_status"),
        "judgment_execution_status": judged.get("execution_status"),
        "activation_action": decision.get("activation_action"),
        "reason_code": decision.get("reason_code"),
    }


class EmptySearch:
    def __init__(self):
        self.calls = 0

    def search(self, _query, *, count):
        self.calls += 1
        return []


@pytest.mark.parametrize("case", sorted(FROZEN_CASES))
def test_v3_routes_frozen_cases_like_v25(case):
    generate = FROZEN_CASES[case]
    v25_calls = []

    def v25_provider(payload):
        v25_calls.append(payload)
        return {"status": "SUCCEEDED", "external_result_id": "EXT-1", "external_result_provenance_ids": ["EXT-P-1"],
                "verification_status": "UNVERIFIED", "findings": ["SOURCE_EVIDENCE_REQUIRED"],
                "uncertainty": "Frozen comparison provider."}

    v25 = process_dialogue_turn(copy.deepcopy(frozen_request()), judgment_generate=generate,
                                verification_provider=v25_provider, model_id="frozen-model",
                                model_revision="frozen-rev")
    search = EmptySearch()
    v3 = SARA_v3Runtime(judgment_generate=generate, judgment_model_id="frozen-model",
                        judgment_model_revision="frozen-rev", search_provider=search,
                        relation_assessor=None).process_turn(copy.deepcopy(frozen_request()))

    assert routing_signature(v3) == routing_signature(v25)
    assert (search.calls > 0) == bool(v25_calls)
    assert v3["truthfulness_status"] == "UNASSESSED"
    assert v3["is_evidence"] is False


def test_only_fresh_bound_high_confidence_inference_triggers_source_verification():
    triggered = set()
    for case, generate in FROZEN_CASES.items():
        search = EmptySearch()
        SARA_v3Runtime(judgment_generate=generate, judgment_model_id="frozen-model",
                       judgment_model_revision="frozen-rev", search_provider=search,
                       relation_assessor=None).process_turn(frozen_request())
        if search.calls:
            triggered.add(case)
    assert triggered == {"bound_high_confidence_inference"}


@pytest.mark.parametrize("premises, evidence", [
    ([], []),
    ([{"id": "P1", "text": "Sales rose after the campaign.", "verification_status": "VERIFIED"}], []),
    ([{"id": "P1", "text": "Sales rose.", "verification_status": "CONTRADICTED"}],
     [{"id": "EV-1", "source": "https://official.example/a", "alignment": "UNASSESSED"}]),
])
def test_v3_carries_v24_epistemic_assessment_unchanged(premises, evidence):
    claim = {"id": "C-1", "text": CLAIM_TEXT}
    request = {"claim": claim, "premises": premises, "provenance_ids": ["INPUT-PROV-1"],
               "evidence": [{"id": e["id"], "url": e["source"], "snippet": "Sales rose."} for e in evidence]}
    v3 = verify_claim_from_sources(request, search_provider=EmptySearch(), mcp_source=None, relation_assessor=None)
    v24_evidence = [{"id": e["id"], "source": e["source"], "alignment": "UNASSESSED"} for e in evidence]
    direct = _run_v24_assessment({"claim": claim, "premises": premises, "evidence": v24_evidence,
                                  "provenance_ids": ["INPUT-PROV-1"], "argument_graph": None})
    assert v3["assessment"]["v24_epistemic_assessment"] == direct["epistemic_assessment"]
    assert v3["assessment"]["v24_logical_audit"] == direct["logical_audit"]
