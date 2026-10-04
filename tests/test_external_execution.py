import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).parents[1] / "SARA_v2.3" / "execution.py"
SPEC = importlib.util.spec_from_file_location("sara_execution", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_sara_executor_rejects_unsupported_capability():
    request = MODULE.SARAExecutionRequest(
        request_id="R1",
        capability="unknown",
        claim={"id": "C1", "text": "claim"},
        evidence=(),
        provenance_ids=("P1",),
        adapter_revision="test",
        requested_at="2026-10-04T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            raise AssertionError("backend must not run")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_preserves_verification_boundary():
    request = MODULE.SARAExecutionRequest(
        request_id="R2",
        capability="verify_claim",
        claim={"id": "C1", "text": "claim"},
        evidence=(),
        provenance_ids=("P1",),
        adapter_revision="test",
        requested_at="2026-10-04T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R2",
                claim_id="C1",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="X1",
                external_result_provenance_ids=("P-X1",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-04T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.verification_status == "VERIFIED"
    assert result.truthfulness_status == "UNASSESSED"


def test_sara_executor_rejects_simulated_reproduction_as_verified():
    request = MODULE.SARAExecutionRequest(
        request_id="R3",
        capability="verify_claim",
        claim={"id": "C1", "text": "claim"},
        evidence=(),
        provenance_ids=("P1",),
        adapter_revision="test",
        requested_at="2026-10-04T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R3",
                claim_id="C1",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="X3",
                external_result_provenance_ids=("P-X3",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status="SIMULATED_REPRODUCTION",
                external_citation_verification=None,
                timestamp="2026-10-04T00:00:01Z",
                environment={},
            )

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


@pytest.mark.parametrize("evidence_type", [
    "simulated_reproduction",
    "cognitive_execution",
    "agent_execution",
])
def test_sara_executor_blocks_execution_derived_evidence(evidence_type):
    request = MODULE.SARAExecutionRequest(
        request_id="R-FIREWALL",
        capability="verify_claim",
        claim={"id": "C1", "text": "claim"},
        evidence=({
            "id": "E1",
            "evidence_type": evidence_type,
            "verification_layer": "research_verification",
            "usable_as_verification_evidence": True,
        },),
        provenance_ids=("P1",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            raise AssertionError("blocked evidence must not reach backend")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_rejects_truthfulness_established_without_citation_verification():
    request = MODULE.SARAExecutionRequest(
        request_id="R-TRUTH-1",
        capability="verify_claim",
        claim={"id": "C1", "text": "claim"},
        evidence=({
            "id": "E1",
            "evidence_type": "empirical data",
            "verification_layer": "research_verification",
        },),
        provenance_ids=("P1",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-TRUTH-1",
                claim_id="C1",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="X-TRUTH-1",
                external_result_provenance_ids=("PX-TRUTH-1",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="ESTABLISHED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_rejects_verified_result_with_unverified_external_citation():
    request = MODULE.SARAExecutionRequest(
        request_id="R-STATUS-1",
        capability="verify_claim",
        claim={"id": "C1", "text": "claim"},
        evidence=(),
        provenance_ids=("P1",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-STATUS-1",
                claim_id="C1",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="X-STATUS-1",
                external_result_provenance_ids=("PX-STATUS-1",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification={"status": "UNVERIFIED", "note": "not checked"},
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.verification_status == "VERIFIED"
    assert result.truthfulness_status == "UNASSESSED"


def test_sara_executor_rejects_verified_result_reusing_request_provenance_as_external_provenance():
    request = MODULE.SARAExecutionRequest(
        request_id="R-PROV-1",
        capability="verify_claim",
        claim={"id": "C1", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-PROV-1",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-PROV-1",
                claim_id="C1",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="X-PROV-1",
                external_result_provenance_ids=request.provenance_ids,
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_rejects_cross_claim_external_provenance_reuse():
    request = MODULE.SARAExecutionRequest(
        request_id="R-PROV-2",
        capability="verify_claim",
        claim={"id": "CLAIM-B", "text": "claim B"},
        evidence=(),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-PROV-2",
                claim_id="CLAIM-A",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-B",
                external_result_provenance_ids=("RESULT-A-PROV",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=("claim B verified",),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={"source_claim_id": "CLAIM-A"},
            )

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_rejects_evidence_bound_to_another_claim():
    request = MODULE.SARAExecutionRequest(
        request_id="R-EVID-1",
        capability="verify_claim",
        claim={"id": "CLAIM-B", "text": "claim B"},
        evidence=({
            "id": "E-A",
            "evidence_type": "empirical data",
            "verification_layer": "research_verification",
            "supports_claims": ["CLAIM-A"],
        },),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            raise AssertionError("evidence bound to another claim must not reach backend")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_accepts_evidence_explicitly_bound_to_requested_claim():
    request = MODULE.SARAExecutionRequest(
        request_id="R-EVID-VALID",
        capability="verify_claim",
        claim={"id": "CLAIM-B", "text": "claim B"},
        evidence=({
            "id": "E-B",
            "evidence_type": "empirical data",
            "verification_layer": "research_verification",
            "supports_claims": ["CLAIM-A", "CLAIM-B"],
        },),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-EVID-VALID",
                claim_id="CLAIM-B",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-B",
                external_result_provenance_ids=("RESULT-B-PROV",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=("claim B supported",),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.claim_id == "CLAIM-B"
    assert result.verification_status == "VERIFIED"


def test_sara_executor_accepts_legacy_evidence_without_supports_claims():
    request = MODULE.SARAExecutionRequest(
        request_id="R-EVID-LEGACY",
        capability="verify_claim",
        claim={"id": "CLAIM-B", "text": "claim B"},
        evidence=({
            "id": "E-LEGACY",
            "evidence_type": "empirical data",
            "verification_layer": "research_verification",
        },),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-EVID-LEGACY",
                claim_id="CLAIM-B",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-LEGACY",
                external_result_provenance_ids=("RESULT-LEGACY-PROV",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.claim_id == "CLAIM-B"
