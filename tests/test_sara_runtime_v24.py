from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sara_runtime import execute_request


def base_payload():
    return {
        "request_id": "REQ-V24-1",
        "capability": "verify_claim",
        "claim": {"id": "C-V24-1", "text": "A test proposition."},
        "premises": [],
        "evidence": [],
        "provenance_ids": ["INPUT-PROV-1"],
        "adapter_revision": "runtime-test-adapter-v1",
        "requested_at": "2026-10-19T10:30:00Z",
        "environment": {"test": True},
    }


def provider_for(_payload):
    return {
        "status": "SUCCEEDED",
        "external_result_id": "EXT-V24-1",
        "external_result_provenance_ids": ["EXT-PROV-V24-1"],
        "verification_status": "UNVERIFIED",
        "findings": ["No independent evidence configured in this test."],
        "uncertainty": "Deterministic provider fixture only.",
    }


def cycle_graph():
    return {
        "nodes": [
            {"node_id": "A", "node_type": "CLAIM", "text": "Claim A."},
            {"node_id": "B", "node_type": "CLAIM", "text": "Claim B."},
            {"node_id": "C", "node_type": "CLAIM", "text": "Claim C."},
        ],
        "edges": [
            {"edge_id": "AB", "source_id": "A", "target_id": "B", "relation": "SUPPORTS"},
            {"edge_id": "BC", "source_id": "B", "target_id": "C", "relation": "SUPPORTS"},
            {"edge_id": "CA", "source_id": "C", "target_id": "A", "relation": "SUPPORTS"},
            {"edge_id": "AC", "source_id": "A", "target_id": "C", "relation": "SUPPORTS"},
        ],
    }


def test_callable_runtime_always_returns_v24_epistemic_boundary_assessment():
    result = execute_request(base_payload(), provider_for)

    assert result.status == "SUCCEEDED"
    assert result.sara_v24_assessment["adapter_revision"] == "co-thoughts-v2.0/sara-v2.4"
    assert result.sara_v24_assessment["epistemic_assessment"]["claim_id"] == "C-V24-1"
    assert result.sara_v24_assessment["epistemic_assessment"]["is_evidence"] is False
    assert result.sara_v24_assessment["logical_audit"]["audit_status"] == "NOT_RUN"
    assert result.sara_v24_assessment["logical_audit"]["reason_code"] == (
        "STRUCTURED_ARGUMENT_GRAPH_NOT_SUPPLIED"
    )
    assert result.sara_v24_assessment["truthfulness_status"] == "UNASSESSED"


def test_callable_runtime_invokes_v24_structural_audit_for_explicit_graph():
    payload = base_payload()
    payload["argument_graph"] = cycle_graph()

    result = execute_request(payload, provider_for)
    audit = result.sara_v24_assessment["logical_audit"]

    assert result.status == "SUCCEEDED"
    assert audit["audit_status"] == "STRUCTURE_CHECKED"
    assert audit["graph_status"] == "STRUCTURALLY_VALID"
    assert len(audit["candidate_findings"]) == 2
    assert audit["semantic_audit_status"] == "NOT_PERFORMED"
    assert audit["is_evidence"] is False


def test_source_less_evidence_cannot_satisfy_author_explicit_runtime_attribution():
    payload = base_payload()
    payload["claim"] = {
        "id": "C-V24-AUTHOR",
        "text": "The author explicitly stated this.",
        "attribution_status": "AUTHOR_EXPLICIT",
        "attribution_evidence_ids": ["E1"],
    }
    payload["evidence"] = [{"id": "E1"}]

    def must_not_reach_provider(_payload):
        raise AssertionError("v2.4 source-attribution guard must run before provider")

    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN"):
        execute_request(payload, must_not_reach_provider)


def test_invalid_structured_graph_is_reported_without_being_promoted_to_evidence():
    payload = base_payload()
    payload["argument_graph"] = {
        "nodes": [{"node_id": "A", "node_type": "CLAIM", "text": "Claim A."}],
        "edges": [{
            "edge_id": "AB",
            "source_id": "MISSING",
            "target_id": "A",
            "relation": "SUPPORTS",
        }],
    }

    result = execute_request(payload, provider_for)
    audit = result.sara_v24_assessment["logical_audit"]

    assert result.status == "SUCCEEDED"
    assert audit["audit_status"] == "INVALID_INPUT"
    assert audit["reason_code"] == "ARGUMENT_EDGE_REFERENCES_UNKNOWN_NODE"
    assert audit["is_evidence"] is False
    assert result.sara_v24_assessment["truthfulness_status"] == "UNASSESSED"
