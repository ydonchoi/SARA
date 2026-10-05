from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from production_verification_backend import ProductionVerificationBackend


def test_provider_failure_cannot_be_promoted_to_verification():
    def provider(_request):
        return {
            "status": "FAILED",
            "failure": {"code": "PROVIDER_TIMEOUT"},
            "external_result_id": None,
            "external_result_provenance_ids": [],
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-FAIL",
            "claim": {"id": "C-FAIL", "text": "claim"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["status"] == "FAILED"
    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"


def test_provider_result_provenance_is_not_replaced_by_request_provenance():
    def provider(request):
        assert request["request_id"] == "REQ-PROV"
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-RESULT",
            "external_result_provenance_ids": ["CR-PROV-1"],
            "verification_status": "VERIFIED",
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-PROV",
            "claim": {"id": "C-PROV", "text": "claim"},
            "evidence": [],
            "provenance_ids": ["REQ-PROVENANCE-1"],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["external_result_provenance_ids"] == ["CR-PROV-1"]
    assert "REQ-PROVENANCE-1" not in result["external_result_provenance_ids"]


def test_production_backend_never_establishes_truthfulness_implicitly():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-RESULT",
            "external_result_provenance_ids": ["CR-PROV-1"],
            "verification_status": "VERIFIED",
            "external_citation_verification": {"status": "VERIFIED"},
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-TRUTH",
            "claim": {"id": "C-TRUTH", "text": "claim"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
