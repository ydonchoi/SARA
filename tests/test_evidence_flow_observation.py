from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))
from evidence_flow_observation import EvidenceFlowObservation, build_observation

def test_observation_records_flow_without_truthfulness():
    result = build_observation(
        request_id="REQ-P41", claim_id="C-P41", provider_status="SUCCEEDED",
        content_access_status="RETRIEVED", content_scope="SUBSTANTIVE_CONTENT",
        evidence_identity_status="MATCHED", verification_status="VERIFIED",
        finding_codes=(), latency_ms=42,
    )
    assert result.recoverability == "UNKNOWN"
    assert result.verification_status == "VERIFIED"
    assert "truthfulness_status" not in result.to_dict()

def test_recoverable_findings_do_not_promote():
    result = build_observation(
        request_id="REQ-P41-REC", claim_id="C-P41-REC", provider_status="SUCCEEDED",
        content_access_status="NOT_COMPLETED", content_scope="UNKNOWN",
        evidence_identity_status="UNKNOWN", verification_status="UNVERIFIED",
        finding_codes=("P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE",),
    )
    assert result.recoverability == "RECOVERABLE"
    assert result.verification_status == "UNVERIFIED"

def test_invalid_recoverability_is_rejected():
    try:
        EvidenceFlowObservation(
            request_id="REQ", claim_id="C", provider_status="SUCCEEDED",
            content_access_status="RETRIEVED", content_scope="SUBSTANTIVE_CONTENT",
            evidence_identity_status="MATCHED", verification_status="UNVERIFIED",
            finding_codes=(), recoverability="VERIFIED", latency_ms=None,
        )
    except ValueError as exc:
        assert str(exc) == "OBSERVATION_RECOVERABILITY_INVALID"
    else:
        raise AssertionError("invalid recoverability must fail closed")
