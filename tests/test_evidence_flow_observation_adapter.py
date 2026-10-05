from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from evidence_flow_observation import build_observation
from evidence_flow_observation_adapter import EvidenceFlowObservationAdapter
from evidence_flow_observation_sink import EvidenceFlowObservationSink


def make_observation(status="UNVERIFIED"):
    return build_observation(
        request_id="REQ-P41-ADAPTER",
        claim_id="C-P41-ADAPTER",
        provider_status="SUCCEEDED",
        content_access_status="RETRIEVED",
        content_scope="SUBSTANTIVE_CONTENT",
        evidence_identity_status="MATCHED",
        verification_status=status,
        finding_codes=(),
    )


def test_adapter_records_and_returns_same_observation():
    sink = EvidenceFlowObservationSink()
    adapter = EvidenceFlowObservationAdapter(sink)
    observation = make_observation()
    result = adapter.observe(observation)

    assert result == observation
    assert sink.records() == (observation,)
    assert sink.records()[0].verification_status == "UNVERIFIED"


def test_adapter_does_not_promote_unverified_observation():
    sink = EvidenceFlowObservationSink()
    adapter = EvidenceFlowObservationAdapter(sink)
    observation = make_observation("UNVERIFIED")

    result = adapter.observe(observation)

    assert result.verification_status == "UNVERIFIED"
    assert sink.summary()["verified"] == 0
