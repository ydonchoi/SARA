from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from a2_evidence_pipeline import A2EvidencePipeline
from production_verification_backend import ProductionVerificationBackend


class FakeContentAccessor:
    def fetch(self, url):
        class Result:
            status = "RETRIEVED"
            content = "Measured measurement"
            url = url
            content_type = "text/plain"
            byte_length = len(content)
            findings = ("CONTENT_ACCESS_COMPLETED",)
        return Result()


def test_p33_production_resolves_source_url_through_content_accessor():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-123",
            "external_result_provenance_ids": ["CR-PROV-456"],
            "verification_status": "VERIFIED",
            "source_exists": True,
            "bibliographic_accuracy": "VERIFIED",
            "evidence_id": "E1",
            "supports_claim_ids": ["C1"],
            "source_url": "https://example.test/source",
        }

    result = ProductionVerificationBackend(
        provider,
        a2_pipeline=A2EvidencePipeline(),
        content_accessor=FakeContentAccessor(),
    )(
        {
            "request_id": "REQ-P33",
            "claim": {"id": "C1", "text": "Measured measurement"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert "P31_P8_CONTENT_PAYLOAD_CONSUMED" in result["verification"]["findings"]


def test_p33_without_accessor_fails_closed_to_unverified():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-123",
            "external_result_provenance_ids": ["CR-PROV-456"],
            "verification_status": "VERIFIED",
            "source_exists": True,
            "bibliographic_accuracy": "VERIFIED",
            "evidence_id": "E1",
            "supports_claim_ids": ["C1"],
            "source_url": "https://example.test/source",
        }

    result = ProductionVerificationBackend(
        provider, a2_pipeline=A2EvidencePipeline()
    )(
        {
            "request_id": "REQ-P33-2",
            "claim": {"id": "C1", "text": "Measured measurement"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
