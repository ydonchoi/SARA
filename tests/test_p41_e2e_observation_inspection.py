from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from evidence_flow_observation import build_observation
from evidence_flow_observation_sink import EvidenceFlowObservationSink


def test_p41_e2e_observation_report_is_descriptive_only(capsys):
    sink = EvidenceFlowObservationSink(max_records=10)

    sink.record(build_observation(
        request_id="E2E-1",
        claim_id="C-1",
        provider_status="SUCCEEDED",
        content_access_status="RETRIEVED",
        content_scope="SUBSTANTIVE_CONTENT",
        evidence_identity_status="MATCHED",
        verification_status="VERIFIED",
        finding_codes=(),
        latency_ms=18,
    ))
    sink.record(build_observation(
        request_id="E2E-2",
        claim_id="C-2",
        provider_status="FAILED",
        content_access_status="NOT_COMPLETED",
        content_scope="UNKNOWN",
        evidence_identity_status="UNKNOWN",
        verification_status="UNVERIFIED",
        finding_codes=("P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE",),
        latency_ms=42,
    ))

    report = sink.telemetry_summary()
    print(json.dumps(report, sort_keys=True))

    assert report["total"] == 2
    assert report["verified"] == 1
    assert report["unverified"] == 1
    assert report["provider_completion_rate"] == 0.5
    assert report["content_retrieval_success_rate"] == 0.5
    assert report["content_scope_resolution_rate"] == 0.5
    assert report["evidence_identity_match_rate"] == 0.5
    assert report["recoverable_unverified"] == 1
    assert report["non_recoverable_unverified"] == 0
    assert report["latency_ms"] == {"count": 2, "min": 18, "max": 42, "average": 30.0}

    captured = capsys.readouterr().out
    assert '"truthfulness_status"' not in captured
