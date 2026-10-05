from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from evidence_flow_observation_adapter import EvidenceFlowObservationAdapter
from production_verification_backend import ProductionVerificationBackend


class RecordingRecorder:
    def __init__(self):
        self.records = []

    def record(self, observation):
        self.records.append(observation)


class FailingRecorder:
    def record(self, _observation):
        raise RuntimeError("OBSERVATION_SINK_FAILURE")


def request(request_id="REQ-P41-WIRING"):
    return {
        "request_id": request_id,
        "claim": {"id": "C-P41-WIRING", "text": "claim"},
        "evidence": [],
        "requested_at": "2026-10-05T00:00:00Z",
    }


def test_production_backend_records_final_verification_outcome_without_mutating_it():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "RESULT-1",
            "external_result_provenance_ids": ["PROV-1"],
            "verification_status": "VERIFIED",
            "findings": ["PROVIDER_VERIFIED"],
        }

    recorder = RecordingRecorder()
    result = ProductionVerificationBackend(
        provider,
        observation_adapter=EvidenceFlowObservationAdapter(recorder),
    )(request())

    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert len(recorder.records) == 1
    assert recorder.records[0].verification_status == "VERIFIED"
    assert recorder.records[0].request_id == "REQ-P41-WIRING"


def test_observation_failure_does_not_change_verification_result():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "RESULT-2",
            "external_result_provenance_ids": ["PROV-2"],
            "verification_status": "VERIFIED",
        }

    result = ProductionVerificationBackend(
        provider,
        observation_adapter=EvidenceFlowObservationAdapter(FailingRecorder()),
    )(request("REQ-P41-FAILURE-ISOLATION"))

    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"


def test_failed_provider_is_observed_as_unverified():
    def provider(_request):
        return {"status": "FAILED", "findings": ["PROVIDER_TIMEOUT"]}

    recorder = RecordingRecorder()
    result = ProductionVerificationBackend(
        provider,
        observation_adapter=EvidenceFlowObservationAdapter(recorder),
    )(request("REQ-P41-PROVIDER-FAILED"))

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert len(recorder.records) == 1
    assert recorder.records[0].verification_status == "UNVERIFIED"
