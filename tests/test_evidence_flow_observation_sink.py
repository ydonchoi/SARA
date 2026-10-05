from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from evidence_flow_observation import build_observation
from evidence_flow_observation_sink import EvidenceFlowObservationSink


def make_observation(status="UNVERIFIED", finding_codes=()):
    return build_observation(
        request_id="REQ-P41-SINK",
        claim_id="C-P41-SINK",
        provider_status="SUCCEEDED",
        content_access_status="RETRIEVED",
        content_scope="SUBSTANTIVE_CONTENT",
        evidence_identity_status="MATCHED",
        verification_status=status,
        finding_codes=finding_codes,
    )


def test_sink_only_observes_and_does_not_change_status():
    sink = EvidenceFlowObservationSink(max_records=2)
    observation = make_observation()
    sink.record(observation)
    assert sink.records()[0].verification_status == "UNVERIFIED"
    assert sink.summary() == {
        "total": 1,
        "verified": 0,
        "unverified": 1,
        "recoverable": 0,
    }


def test_sink_counts_recoverable_rejections_without_promoting():
    sink = EvidenceFlowObservationSink()
    observation = make_observation(
        "UNVERIFIED",
        ("P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",),
    )
    sink.record(observation)
    assert sink.summary()["recoverable"] == 1
    assert sink.records()[0].verification_status == "UNVERIFIED"


def test_sink_is_bounded():
    sink = EvidenceFlowObservationSink(max_records=1)
    sink.record(make_observation())
    try:
        sink.record(make_observation())
    except OverflowError as exc:
        assert str(exc) == "OBSERVATION_SINK_CAPACITY_EXCEEDED"
    else:
        raise AssertionError("sink must fail closed at capacity")


def test_invalid_capacity_is_rejected():
    try:
        EvidenceFlowObservationSink(max_records=0)
    except ValueError as exc:
        assert str(exc) == "OBSERVATION_SINK_CAPACITY_INVALID"
    else:
        raise AssertionError("invalid capacity must fail closed")
