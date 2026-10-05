from SARA_v2.3.production_verification_backend import ProductionVerificationBackend


def test_production_backend_preserves_live_provider_verification_boundary():
    def provider(request):
        assert request["claim"]["id"] == "C1"
        return {
            "status": "SUCCEEDED",
            "external_result_id": "CR-123",
            "external_result_provenance_ids": ["CR-PROV-456"],
            "verification_status": "VERIFIED",
            "findings": ["CROSSREF_SOURCE_RESOLVED"],
            "external_citation_verification": {"status": "NOT_COMPLETED"},
        }

    backend = ProductionVerificationBackend(provider)
    result = backend(
        {
            "request_id": "REQ-1",
            "claim": {"id": "C1", "text": "claim"},
            "evidence": [],
            "adapter_revision": "p7d",
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["status"] == "SUCCEEDED"
    assert result["provider_id"] == "SARA"
    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["verification_layer"] == "research_verification"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert result["external_result_provenance_ids"] == ["CR-PROV-456"]
    assert result["environment"]["backend"] == "production"
    assert result["environment"]["live_external_research"] is True


def test_production_backend_rejects_silent_provider_failure_as_verification():
    def provider(_request):
        return {
            "status": "FAILED",
            "failure": {"code": "PROVIDER_TIMEOUT"},
        }

    result = ProductionVerificationBackend(provider)(
        {
            "request_id": "REQ-2",
            "claim": {"id": "C2", "text": "claim"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["status"] == "FAILED"
    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
