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
        "recovery_candidates": 0,
    }


def test_sink_counts_recovery_candidates_without_promoting():
    sink = EvidenceFlowObservationSink()
    observation = make_observation(
        "UNVERIFIED",
        ("P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",),
    )
    sink.record(observation)
    assert sink.summary()["recovery_candidates"] == 1
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


def test_sink_summary_exposes_bounded_flow_metrics_without_promotion():
    sink = EvidenceFlowObservationSink(max_records=4)
    sink.record(build_observation(
        request_id="REQ-1",
        claim_id="C-1",
        provider_status="SUCCEEDED",
        content_access_status="RETRIEVED",
        content_scope="SUBSTANTIVE_CONTENT",
        evidence_identity_status="MATCHED",
        verification_status="UNVERIFIED",
        finding_codes=("P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",),
        latency_ms=10,
    ))
    sink.record(build_observation(
        request_id="REQ-1",
        claim_id="C-1",
        provider_status="SUCCEEDED",
        content_access_status="RETRIEVED",
        content_scope="SUBSTANTIVE_CONTENT",
        evidence_identity_status="MATCHED",
        verification_status="VERIFIED",
        finding_codes=(),
        latency_ms=20,
    ))
    sink.record(build_observation(
        request_id="REQ-2",
        claim_id="C-2",
        provider_status="FAILED",
        content_access_status="NOT_COMPLETED",
        content_scope="UNKNOWN",
        evidence_identity_status="UNKNOWN",
        verification_status="UNVERIFIED",
        finding_codes=("P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE",),
        latency_ms=None,
    ))

    summary = sink.telemetry_summary()

    assert summary["provider_completion_rate"] == 2 / 3
    assert summary["content_retrieval_success_rate"] == 2 / 3
    assert summary["content_scope_resolution_rate"] == 2 / 3
    assert summary["evidence_identity_match_rate"] == 2 / 3
    assert summary["a2_rejection_rate_by_finding"]["P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE"] == 1 / 3
    assert summary["a2_rejection_rate_by_finding"]["P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE"] == 1 / 3
    assert summary["recoverable_unverified"] == 2
    assert summary["non_recoverable_unverified"] == 1
    assert summary["reverification_success_after_recovery"] == 1
    assert summary["latency_ms"] == {"count": 2, "min": 10, "max": 20, "average": 15.0}
    assert summary["verified"] == 1
    assert summary["unverified"] == 2


def test_sink_summary_empty_dataset_is_bounded_and_deterministic():
    summary = EvidenceFlowObservationSink().telemetry_summary()

    assert summary["total"] == 0
    assert summary["provider_completion_rate"] == 0.0
    assert summary["content_retrieval_success_rate"] == 0.0
    assert summary["content_scope_resolution_rate"] == 0.0
    assert summary["evidence_identity_match_rate"] == 0.0
    assert all(value == 0.0 for value in summary["a2_rejection_rate_by_finding"].values())
    assert summary["recoverable_unverified"] == 0
    assert summary["non_recoverable_unverified"] == 0
    assert summary["reverification_success_after_recovery"] == 0
    assert summary["latency_ms"] == {"count": 0, "min": None, "max": None, "average": None}
