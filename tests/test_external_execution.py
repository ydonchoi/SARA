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


def test_sara_executor_rejects_dangling_claim_evidence_reference():
    request = MODULE.SARAExecutionRequest(
        request_id="R-EVID-DANGLING",
        capability="verify_claim",
        claim={
            "id": "CLAIM-B",
            "text": "claim B",
            "evidence_ids": ["E-MISSING"],
        },
        evidence=({
            "id": "E-ACTUAL",
            "evidence_type": "empirical data",
            "verification_layer": "research_verification",
            "supports_claims": ["CLAIM-B"],
        },),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            raise AssertionError("dangling evidence reference must not reach backend")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_rejects_conflicting_claim_evidence_binding():
    request = MODULE.SARAExecutionRequest(
        request_id="R-EVID-CONFLICT",
        capability="verify_claim",
        claim={
            "id": "CLAIM-B",
            "text": "claim B",
            "evidence_ids": ["E-A"],
        },
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
            raise AssertionError("conflicting claim/evidence binding must not reach backend")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_does_not_treat_evidence_status_as_claim_verification_status():
    request = MODULE.SARAExecutionRequest(
        request_id="R-EVID-STATUS-SEPARATION",
        capability="verify_claim",
        claim={
            "id": "CLAIM-B",
            "text": "claim B",
            "evidence_ids": ["E-B"],
        },
        evidence=({
            "id": "E-B",
            "evidence_type": "prior research",
            "verification": "PARTIALLY VERIFIED",
            "verification_layer": "research_verification",
            "evidence_strength": "moderate",
            "usable_as_verification_evidence": True,
            "supports_claims": ["CLAIM-B"],
        },),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-EVID-STATUS-SEPARATION",
                claim_id="CLAIM-B",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-B",
                external_result_provenance_ids=("RESULT-B-PROV",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=("independently verified claim",),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.verification_status == "VERIFIED"


def test_sara_executor_preserves_strength_alignment_as_review_metadata():
    request = MODULE.SARAExecutionRequest(
        request_id="R-STRENGTH-SEPARATION",
        capability="verify_claim",
        claim={
            "id": "CLAIM-B",
            "text": "claim B",
            "evidence_ids": ["E-B"],
            "strength_alignment": "overreach",
        },
        evidence=({
            "id": "E-B",
            "evidence_type": "observation",
            "verification_layer": "research_verification",
            "evidence_strength": "weak",
            "usable_as_verification_evidence": True,
            "supports_claims": ["CLAIM-B"],
        },),
        provenance_ids=("INPUT-B",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-STRENGTH-SEPARATION",
                claim_id="CLAIM-B",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-B",
                external_result_provenance_ids=("RESULT-B-PROV",),
                verification_status="VERIFIED",
                verification_layer="research_verification",
                findings=("verification completed; strength overreach remains a review finding",),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.verification_status == "VERIFIED"


def test_sara_executor_rejects_non_fact_claim_without_inference_basis():
    request = MODULE.SARAExecutionRequest(
        request_id="R-INFERENCE-BASIS-MISSING",
        capability="verify_claim",
        claim={
            "id": "CLAIM-INFERRED",
            "text": "claim inferred from evidence",
            "inference_level": "INFERENCE",
            "evidence_ids": ["E-INFERRED"],
        },
        evidence=({
            "id": "E-INFERRED",
            "evidence_type": "observation",
            "verification_layer": "research_verification",
            "supports_claims": ["CLAIM-INFERRED"],
        },),
        provenance_ids=("INPUT-INFERRED",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            raise AssertionError("schema-invalid inference claim must not reach backend")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


@pytest.mark.parametrize("inference_level", ["BAD", "", "fact", "CONCLUSION"])
def test_sara_executor_rejects_invalid_inference_level(inference_level):
    request = MODULE.SARAExecutionRequest(
        request_id="R-INFERENCE-INVALID",
        capability="verify_claim",
        claim={
            "id": "CLAIM-INVALID",
            "text": "invalid inference level",
            "inference_level": inference_level,
            "inference_basis": "basis",
        },
        evidence=(),
        provenance_ids=("INPUT-INVALID",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            raise AssertionError("invalid inference level must not reach backend")

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_accepts_fact_without_inference_basis():
    request = MODULE.SARAExecutionRequest(
        request_id="R-INFERENCE-FACT",
        capability="verify_claim",
        claim={
            "id": "CLAIM-FACT",
            "text": "fact claim",
            "inference_level": "FACT",
        },
        evidence=(),
        provenance_ids=("INPUT-FACT",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-INFERENCE-FACT",
                claim_id="CLAIM-FACT",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-FACT",
                external_result_provenance_ids=("RESULT-FACT-PROV",),
                verification_status="UNVERIFIED",
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
    assert result.verification_status == "UNVERIFIED"


@pytest.mark.parametrize("inference_level", ["INFERENCE", "HYPOTHESIS", "SPECULATION"])
def test_sara_executor_accepts_non_fact_claim_with_inference_basis(inference_level):
    request = MODULE.SARAExecutionRequest(
        request_id="R-INFERENCE-VALID",
        capability="verify_claim",
        claim={
            "id": f"CLAIM-{inference_level}",
            "text": "non-fact claim",
            "inference_level": inference_level,
            "inference_basis": "explicit basis",
        },
        evidence=(),
        provenance_ids=("INPUT-VALID",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id=request.request_id,
                claim_id=request.claim["id"],
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-VALID",
                external_result_provenance_ids=("RESULT-VALID-PROV",),
                verification_status="UNVERIFIED",
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
    assert result.claim_id == request.claim["id"]


@pytest.mark.parametrize("citation_status", [
    "VERIFIED",
    "PARTIALLY VERIFIED",
    "UNVERIFIED",
    "CONTRADICTED",
    "NOT_COMPLETED",
])
def test_sara_executor_accepts_scoped_external_citation_status(citation_status):
    request = MODULE.SARAExecutionRequest(
        request_id="R-CITATION-SCOPED",
        capability="verify_claim",
        claim={"id": "CLAIM-CIT", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-CIT",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-CITATION-SCOPED",
                claim_id="CLAIM-CIT",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-CIT",
                external_result_provenance_ids=("RESULT-CIT-PROV",),
                verification_status="UNVERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification={"status": citation_status},
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.external_citation_verification["status"] == citation_status


@pytest.mark.parametrize("citation_status", ["INVALID", "VERIFIED_EXTRA", "ESTABLISHED"])
def test_sara_executor_rejects_invalid_external_citation_status(citation_status):
    request = MODULE.SARAExecutionRequest(
        request_id="R-CITATION-INVALID",
        capability="verify_claim",
        claim={"id": "CLAIM-CIT", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-CIT",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-CITATION-INVALID",
                claim_id="CLAIM-CIT",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-CIT",
                external_result_provenance_ids=("RESULT-CIT-PROV",),
                verification_status="UNVERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification={"status": citation_status},
                timestamp="2026-10-05T00:00:01Z",
                environment={},
            )

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


@pytest.mark.parametrize("verification_status", [
    "VERIFIED",
    "PARTIALLY VERIFIED",
    "INFERRED",
    "HYPOTHESIZED",
    "UNVERIFIED",
    "CONTRADICTED",
])
def test_sara_executor_accepts_scoped_verification_status(verification_status):
    request = MODULE.SARAExecutionRequest(
        request_id="R-VERIFICATION-STATUS",
        capability="verify_claim",
        claim={"id": "CLAIM-V", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-V",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-VERIFICATION-STATUS",
                claim_id="CLAIM-V",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-V",
                external_result_provenance_ids=("RESULT-V-PROV",),
                verification_status=verification_status,
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
    assert result.verification_status == verification_status


@pytest.mark.parametrize("verification_status", ["ESTABLISHED", "VALID", "UNKNOWN", ""])
def test_sara_executor_rejects_invalid_verification_status(verification_status):
    request = MODULE.SARAExecutionRequest(
        request_id="R-VERIFICATION-INVALID",
        capability="verify_claim",
        claim={"id": "CLAIM-V", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-V",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-VERIFICATION-INVALID",
                claim_id="CLAIM-V",
                provider_id="SARA",
                adapter_revision="test",
                status="SUCCEEDED",
                external_result_id="RESULT-V",
                external_result_provenance_ids=("RESULT-V-PROV",),
                verification_status=verification_status,
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


@pytest.mark.parametrize("status", ["PENDING", "CANCELLED", "SUCCESS", ""])
def test_sara_executor_rejects_invalid_execution_status(status):
    request = MODULE.SARAExecutionRequest(
        request_id="R-STATUS-INVALID",
        capability="verify_claim",
        claim={"id": "CLAIM-S", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-S",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-STATUS-INVALID",
                claim_id="CLAIM-S",
                provider_id="SARA",
                adapter_revision="test",
                status=status,
                external_result_id=None,
                external_result_provenance_ids=(),
                verification_status="UNVERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="execution did not complete",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
                failure={"code": "BACKEND_FAILURE"},
            )

    with pytest.raises(MODULE.SARAExecutionError):
        MODULE.SARAExecutor(Backend(), "test").verify_claim(request)


def test_sara_executor_accepts_failed_response_without_external_result_provenance():
    request = MODULE.SARAExecutionRequest(
        request_id="R-FAILED-VALID",
        capability="verify_claim",
        claim={"id": "CLAIM-S", "text": "claim"},
        evidence=(),
        provenance_ids=("INPUT-S",),
        adapter_revision="test",
        requested_at="2026-10-05T00:00:00Z",
        environment={},
    )

    class Backend:
        def verify(self, request):
            return MODULE.SARAExecutionResponse(
                request_id="R-FAILED-VALID",
                claim_id="CLAIM-S",
                provider_id="SARA",
                adapter_revision="test",
                status="FAILED",
                external_result_id=None,
                external_result_provenance_ids=(),
                verification_status="UNVERIFIED",
                verification_layer="research_verification",
                findings=(),
                uncertainty="backend failed",
                structural_validity="VALID",
                truthfulness_status="UNASSESSED",
                reproduction_status=None,
                external_citation_verification=None,
                timestamp="2026-10-05T00:00:01Z",
                environment={},
                failure={"code": "BACKEND_FAILURE"},
            )

    result = MODULE.SARAExecutor(Backend(), "test").verify_claim(request)
    assert result.status == "FAILED"
    assert result.external_result_provenance_ids == ()
