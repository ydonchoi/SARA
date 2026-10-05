"""Tests for the bounded P31 A2 evidence pipeline."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from a2_evidence_pipeline import A2EvidencePipeline


def test_p31_executes_p8_to_p13_and_promotes_without_truthfulness():
    result = A2EvidencePipeline().evaluate(
        claim_id="C1",
        claim_text="Measured measurement",
        evidence_id="E1",
        supports_claim_ids=("C1",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={
            "status": "RETRIEVED",
            "content": "The paper reports Measured measurement in its results.",
            "evidence_id": "E1",
        },
        content_scope="SUBSTANTIVE_CONTENT",
    )

    assert result.verification_status == "VERIFIED"
    assert result.truthfulness_status == "UNASSESSED"
    assert result.citation_fit == "VERIFIED"
    assert result.evidence_strength == "STRONG"
    assert result.claim_bound is True
    assert result.findings == (
        "P31_P8_CONTENT_PAYLOAD_CONSUMED",
        "P31_P9_CITATION_FIT_EXECUTED",
        "P31_P10_EVIDENCE_STRENGTH_EXECUTED",
        "P31_P12_CLAIM_BINDING_EXECUTED",
        "P31_P13_PROMOTION_EXECUTED",
    )


def test_p31_does_not_promote_when_claim_binding_is_missing():
    result = A2EvidencePipeline().evaluate(
        claim_id="C1",
        claim_text="Measured measurement",
        evidence_id="E1",
        supports_claim_ids=("OTHER",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={
            "status": "RETRIEVED",
            "content": "Measured measurement",
            "evidence_id": "E1",
        },
    )

    assert result.verification_status == "UNVERIFIED"
    assert result.truthfulness_status == "UNASSESSED"
    assert result.claim_bound is False


def test_p31_does_not_promote_without_retrieved_content():
    result = A2EvidencePipeline().evaluate(
        claim_id="C1",
        claim_text="Measured measurement",
        evidence_id="E1",
        supports_claim_ids=("C1",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={
            "status": "NOT_COMPLETED",
            "content": "",
            "evidence_id": "E1",
        },
    )

    assert result.verification_status == "UNVERIFIED"
    assert result.truthfulness_status == "UNASSESSED"
    assert result.citation_fit == "UNVERIFIED"


def test_substantive_scope_requires_retrieved_payload():
    pipeline = A2EvidencePipeline()
    result = pipeline.evaluate(
        claim_id="C-P37-1",
        claim_text="A substantive claim",
        evidence_id="E-P37-1",
        supports_claim_ids=("C-P37-1",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={"status": "NOT_COMPLETED", "content": "", "evidence_id": "E-P37-1"},
        content_scope="SUBSTANTIVE_CONTENT",
    )
    assert result.verification_status == "UNVERIFIED"
    assert "P37_SUBSTANTIVE_CONTENT_REQUIRES_RETRIEVED_PAYLOAD" in result.findings


def test_unknown_content_scope_is_not_promotable():
    pipeline = A2EvidencePipeline()
    result = pipeline.evaluate(
        claim_id="C-P37-2",
        claim_text="An unknown-scope claim",
        evidence_id="E-P37-2",
        supports_claim_ids=("C-P37-2",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={"status": "RETRIEVED", "content": "An unknown-scope claim", "evidence_id": "E-P37-2"},
        content_scope="UNKNOWN",
    )
    assert result.verification_status == "UNVERIFIED"
    assert "P37_UNKNOWN_CONTENT_SCOPE_NOT_PROMOTABLE" in result.findings


def test_p38_content_evidence_identity_mismatch_fails_closed():
    result = A2EvidencePipeline().evaluate(
        claim_id="C-P38-1",
        claim_text="Bound content",
        evidence_id="E-P38-1",
        supports_claim_ids=("C-P38-1",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={
            "status": "RETRIEVED",
            "content": "Bound content",
            "evidence_id": "E-OTHER",
        },
        content_scope="SUBSTANTIVE_CONTENT",
    )
    assert result.verification_status == "UNVERIFIED"
    assert "P38_CONTENT_EVIDENCE_ID_MISMATCH" in result.findings


def test_p38_content_evidence_identity_is_required():
    result = A2EvidencePipeline().evaluate(
        claim_id="C-P38-2",
        claim_text="Unbound content",
        evidence_id="E-P38-2",
        supports_claim_ids=("C-P38-2",),
        source_exists=True,
        bibliographic_accuracy="VERIFIED",
        content_access={
            "status": "RETRIEVED",
            "content": "Unbound content",
        },
        content_scope="SUBSTANTIVE_CONTENT",
    )
    assert result.verification_status == "UNVERIFIED"
    assert "P38_CONTENT_EVIDENCE_ID_MISMATCH" in result.findings
