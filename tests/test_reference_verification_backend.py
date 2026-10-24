import importlib.util
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]
BACKEND_SPEC = importlib.util.spec_from_file_location(
    "reference_verification_backend",
    ROOT / "SARA_v2.3" / "reference_verification_backend.py",
)
assert BACKEND_SPEC and BACKEND_SPEC.loader
BACKEND = importlib.util.module_from_spec(BACKEND_SPEC)
BACKEND_SPEC.loader.exec_module(BACKEND)

CALLABLE_SPEC = importlib.util.spec_from_file_location(
    "sara_callable",
    ROOT / "SARA_v2.3" / "07_SYSTEM" / "sara_callable.py",
)
assert CALLABLE_SPEC and CALLABLE_SPEC.loader
CALLABLE = importlib.util.module_from_spec(CALLABLE_SPEC)
CALLABLE_SPEC.loader.exec_module(CALLABLE)


def request(**claim_overrides):
    claim = {
        "id": "C-REF-1",
        "text": "The reference study reports a positive association.",
        "type": "FACT",
        "source": "SRC-1",
        "evidence_ids": ["E-1"],
        "inference_level": "FACT",
    }
    claim.update(claim_overrides)
    return {
        "request_id": "R-REF-1",
        "capability": "verify_claim",
        "claim": claim,
        "evidence": [{
            "id": "E-1",
            "description": "Reference result",
            "source": "SRC-1",
            "source_level": 1,
            "evidence_type": "statistical result",
            "method": "reference corpus",
            "supports_claims": ["C-REF-1"],
            "evidence_strength": "strong",
            "usable_as_verification_evidence": True,
        }],
        "provenance_ids": ["INPUT-REF-1"],
        "adapter_revision": "p6-reference-v1",
        "requested_at": "2026-10-05T00:00:00Z",
        "environment": {},
    }


def backend():
    return BACKEND.ReferenceVerificationBackend({
        "SRC-1": BACKEND.ReferenceSource(
            source_id="SRC-1",
            uri="reference://SRC-1",
            content="The reference study reports a positive association.",
            source_level=1,
            bibliographic_verified=True,
        )
    })


def test_reference_backend_verifies_against_controlled_corpus():
    result = CALLABLE.CallableSARA(backend()).verify_claim(request())

    assert result["status"] == "SUCCEEDED"
    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"
    assert result["external_citation_verification"]["status"] == "VERIFIED"
    assert result["environment"]["live_external_research"] is False
    assert result["external_result_provenance_ids"]


def test_reference_backend_never_establishes_truthfulness():
    result = CALLABLE.CallableSARA(backend()).verify_claim(request())

    assert result["verification"]["verification_status"] == "VERIFIED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"


def test_reference_backend_returns_unverified_when_claim_content_is_absent():
    result = CALLABLE.CallableSARA(backend()).verify_claim(
        request(text="A different claim is asserted by the study.")
    )

    assert result["verification"]["verification_status"] == "UNVERIFIED"
    assert "CLAIM_CONTENT_NOT_FOUND" in result["verification"]["findings"]


def test_reference_backend_provenance_is_deterministic_for_same_corpus_and_claim():
    first = CALLABLE.CallableSARA(backend()).verify_claim(request())
    second = CALLABLE.CallableSARA(backend()).verify_claim(request())

    assert first["external_result_id"] == second["external_result_id"]
    assert first["external_result_provenance_ids"] == second["external_result_provenance_ids"]


def test_callable_firewall_still_blocks_simulated_evidence():
    bad = request()
    bad["evidence"][0]["evidence_type"] = "simulated_reproduction"

    with pytest.raises(CALLABLE.SARAExecutionError):
        CALLABLE.CallableSARA(backend()).verify_claim(bad)
