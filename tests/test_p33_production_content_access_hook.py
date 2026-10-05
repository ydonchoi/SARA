[object Object]

def test_p34_bibliographic_metadata_is_not_substantive_evidence():
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
            "source_url": "https://api.crossref.org/works/10.1038/nphys1170",
            "content_scope": "BIBLIOGRAPHIC_METADATA",
        }

    result = ProductionVerificationBackend(
        provider,
        a2_pipeline=A2EvidencePipeline(),
        content_accessor=FakeContentAccessor(),
    )(
        {
            "request_id": "REQ-P34",
            "claim": {"id": "C1", "text": "Measured measurement"},
            "evidence": [],
            "requested_at": "2026-10-05T00:00:00Z",
        }
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert "P31_BIBLIOGRAPHIC_METADATA_NOT_SUBSTANTIVE_EVIDENCE" in result["verification"]["findings"]
