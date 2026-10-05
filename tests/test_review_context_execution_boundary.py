from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from execution import SARAExecutionRequest, SARAExecutionResponse, SARAExecutor, SARAExecutionError

class CaptureBackend:
    def __init__(self):
        self.request = None
    def verify(self, request):
        self.request = request
        return SARAExecutionResponse(
            request_id=request.request_id,
            claim_id=request.claim["id"],
            provider_id="SARA",
            adapter_revision=request.adapter_revision,
            status="SUCCEEDED",
            external_result_id="EXT-1",
            external_result_provenance_ids=("EXT-PROV-1",),
            verification_status="UNVERIFIED",
            verification_layer="research_verification",
            findings=(),
            uncertainty="UNASSESSED",
            structural_validity="VALID",
            truthfulness_status="UNASSESSED",
            reproduction_status=None,
            external_citation_verification={"status":"NOT_COMPLETED"},
            timestamp=request.requested_at,
            environment={"backend":"test"},
        )

def make_request(context=None):
    return SARAExecutionRequest(
        request_id="REQ-1", capability="verify_claim",
        claim={"id":"C-1","text":"claim","inference_level":"FACT"},
        evidence=(), provenance_ids=("REQ-PROV",),
        adapter_revision="p26", requested_at="2026-10-05T00:00:00Z",
        environment={"backend":"test"}, review_context=context,
    )

def test_review_context_reaches_backend_as_operational_context():
    context={"status":"CONSUMED_AS_OPERATIONAL_CONTEXT","review_event_id":"REV-1"}
    backend=CaptureBackend()
    response=SARAExecutor(backend, "p26").verify_claim(make_request(context))
    assert backend.request.review_context == context
    assert response.verification_status == "UNVERIFIED"
    assert response.truthfulness_status == "UNASSESSED"

def test_review_context_cannot_carry_verification_state():
    backend=CaptureBackend()
    try:
        SARAExecutor(backend, "p26").verify_claim(
            make_request({"status":"CONSUMED_AS_OPERATIONAL_CONTEXT","verification_status":"VERIFIED"})
        )
    except SARAExecutionError as exc:
        assert "verification status" in str(exc)
    else:
        raise AssertionError("verification state must be rejected")

def test_review_context_cannot_carry_truthfulness_or_evidence():
    backend=CaptureBackend()
    for forbidden in ({"truthfulness_status":"ESTABLISHED"}, {"evidence_ids":["E-1"]}):
        try:
            SARAExecutor(backend, "p26").verify_claim(make_request(forbidden))
        except SARAExecutionError:
            pass
        else:
            raise AssertionError("forbidden epistemic field must be rejected")

def test_legacy_request_without_review_context_remains_valid():
    backend=CaptureBackend()
    response=SARAExecutor(backend, "p26").verify_claim(make_request())
    assert backend.request.review_context is None
    assert response.status == "SUCCEEDED"
