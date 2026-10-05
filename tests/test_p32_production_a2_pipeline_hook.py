from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from a2_evidence_pipeline import A2EvidencePipeline
from production_verification_backend import ProductionVerificationBackend


def test_p32_production_backend_executes_a2_pipeline():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-123",
            "external_result_provenance_ids": ["CR-PROV-456"],
            "verification_status": "VERIFIED",
            "findings": ["CROSSREF_SOURCE_RESOLVED"],
            "source_exists": True,
            "bibliographic_accuracy": "VERIFIED",
            "content_scope": "SUBSTANTIVE_CONTENT",
            "evidence_id": "E1",
            "supports_claim_ids": ["C1"],
            "content_access": {
                "status": "RETRIEVED",
                "content": "Measured measurement",
            },
        }

    result = ProductionVerificationBackend(
        provider, a2_pipeline=A2EvidencePipeline()
    )(
        {
            "request_id": "REQ-P32",
            "claim": {"id": "C1", "text": "Measured measurement"},
            "evidence": [],
            "adapter_revision": "p32",
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["status"] == "SUCCEEDED"
    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert "P31_P9_CITATION_FIT_EXECUTED" in result["verification"]["findings"]
    assert "P31_P13_PROMOTION_EXECUTED" in result["verification"]["findings"]


def test_p32_pipeline_cannot_promote_unbound_provider_content():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-123",
            "external_result_provenance_ids": ["CR-PROV-456"],
            "verification_status": "VERIFIED",
            "source_exists": True,
            "bibliographic_accuracy": "VERIFIED",
            "evidence_id": "E1",
            "supports_claim_ids": ["OTHER"],
            "content_access": {
                "status": "RETRIEVED",
                "content": "Measured measurement",
            },
        }

    result = ProductionVerificationBackend(
        provider, a2_pipeline=A2EvidencePipeline()
    )(
        {
            "request_id": "REQ-P32-2",
            "claim": {"id": "C1", "text": "Measured measurement"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"


def test_p32_legacy_backend_without_pipeline_is_unchanged():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-123",
            "external_result_provenance_ids": ["CR-PROV-456"],
            "verification_status": "VERIFIED",
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-P32-3",
            "claim": {"id": "C1", "text": "claim"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"


def test_p39_content_scope_cannot_promote_without_a2_pipeline():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-P39",
            "external_result_provenance_ids": ["CR-P39-PROV"],
            "verification_status": "VERIFIED",
            "source_exists": True,
            "bibliographic_accuracy": "VERIFIED",
            "content_scope": "SUBSTANTIVE_CONTENT",
            "evidence_id": "E-P39",
            "supports_claim_ids": ["C-P39"],
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-P39",
            "claim": {"id": "C-P39", "text": "Content-scoped claim"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert "P39_CONTENT_SCOPE_REQUIRES_A2_PIPELINE" in result["verification"]["findings"]


def test_p40_source_url_cannot_promote_without_a2_pipeline():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-P40",
            "external_result_provenance_ids": ["CR-P40-PROV"],
            "verification_status": "VERIFIED",
            "source_exists": True,
            "bibliographic_accuracy": "VERIFIED",
            "evidence_id": "E-P40",
            "supports_claim_ids": ["C-P40"],
            "source_url": "https://example.test/source",
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-P40",
            "claim": {"id": "C-P40", "text": "Implicit content claim"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert "P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE" in result["verification"]["findings"]


def test_p40_explicit_content_access_cannot_promote_without_a2_pipeline():
    def provider(_request):
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-P40-2",
            "external_result_provenance_ids": ["CR-P40-2-PROV"],
            "verification_status": "VERIFIED",
            "evidence_id": "E-P40-2",
            "supports_claim_ids": ["C-P40-2"],
            "content_access": {
                "status": "RETRIEVED",
                "content": "Implicitly supplied content",
            },
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-P40-2",
            "claim": {"id": "C-P40-2", "text": "Implicitly supplied content"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert "P40_IMPLICIT_CONTENT_REQUIRES_A2_PIPELINE" in result["verification"]["findings"]
