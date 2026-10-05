from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from crossref_content_accessor import CrossrefContentAccessor
from evidence_flow_observation import build_observation
from evidence_flow_observation_sink import EvidenceFlowObservationSink


def test_live_crossref_content_access_produces_bounded_observation():
    accessor = CrossrefContentAccessor()
    result = accessor.fetch("https://api.crossref.org/works/10.1038/s41586-020-2649-2")

    sink = EvidenceFlowObservationSink(max_records=1)
    sink.record(build_observation(
        request_id="LIVE-CROSSREF-P41",
        claim_id="C-LIVE-CROSSREF",
        provider_status="SUCCEEDED",
        content_access_status=result.status,
        content_scope="METADATA_ONLY",
        evidence_identity_status="UNKNOWN",
        verification_status="UNVERIFIED",
        finding_codes=result.findings,
        latency_ms=None,
    ))

    report = sink.telemetry_summary()
    print(json.dumps({
        "observation": sink.records()[0].to_dict(),
        "telemetry_summary": report,
        "content_bytes": result.byte_length,
        "content_type": result.content_type,
    }, sort_keys=True))

    assert result.status == "RETRIEVED"
    assert result.byte_length > 0
    assert sink.records()[0].verification_status == "UNVERIFIED"
    assert sink.records()[0].evidence_identity_status == "UNKNOWN"
