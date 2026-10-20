from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from claim_identity import (
    assess_verification_reuse,
    compute_content_digest,
    create_claim_revision,
)

SCOPE = {
    "population": "adults",
    "setting": "one hospital",
    "time_range": "2020-2024",
    "modality": "observational",
    "outcome": "readmission",
    "causal_strength": "association",
}


def test_revision_digest_is_stable_for_scope_key_order():
    scope_reversed = dict(reversed(list(SCOPE.items())))
    assert compute_content_digest("Outcome was associated.", SCOPE) == compute_content_digest(
        "Outcome was associated.", scope_reversed
    )


def test_material_scope_change_changes_digest():
    changed = dict(SCOPE, population="all patients")
    assert compute_content_digest("Outcome was associated.", SCOPE) != compute_content_digest(
        "Outcome was associated.", changed
    )


def test_revision_text_change_changes_digest():
    assert compute_content_digest("Claim A.", SCOPE) != compute_content_digest(
        "Claim B.", SCOPE
    )


def test_verification_binding_requires_exact_revision_and_digest():
    revision = create_claim_revision(
        claim_id="C1", revision_id="R2", text="Claim A.", scope=SCOPE, provenance_ids=("SRC-1",)
    )
    result = assess_verification_reuse(
        revision=revision,
        prior_binding={
            "claim_id": "C1",
            "revision_id": "R1",
            "content_digest": "old-digest",
            "verifier_revision": "verify-1",
        "verification_contract_revision": "contract-1",
            "evidence_digest": "evidence-1",
            "verification_status": "VERIFIED",
        },
        current_verifier_revision="verify-1",
        current_contract_revision="contract-1",
        current_evidence_digest="evidence-1",
    )
    assert result["review_state"] == "REQUIRES_REVERIFICATION"
    assert result["reuse_allowed"] is False
    assert "CLAIM_REVISION_CHANGED" in result["reasons"]
    assert "CLAIM_CONTENT_OR_SCOPE_CHANGED" in result["reasons"]


def test_current_binding_can_be_reused_only_for_same_revision_evidence_and_verifier():
    revision = create_claim_revision(
        claim_id="C1", revision_id="R1", text="Claim A.", scope=SCOPE, provenance_ids=("SRC-1",)
    )
    result = assess_verification_reuse(
        revision=revision,
        prior_binding={
            "claim_id": revision.claim_id,
            "revision_id": revision.revision_id,
            "content_digest": revision.content_digest,
            "verifier_revision": "verify-1",
            "verification_contract_revision": "contract-1",
            "evidence_digest": "evidence-1",
            "verification_status": "VERIFIED",
        },
        current_verifier_revision="verify-1",
        current_contract_revision="contract-1",
        current_evidence_digest="evidence-1",
    )
    assert result["review_state"] == "CURRENT"
    assert result["reuse_allowed"] is True


@pytest.mark.parametrize(
    "changed_field, current_value, expected_reason",
    [
        ("verifier_revision", "verify-2", "VERIFIER_REVISION_CHANGED"),
        ("evidence_digest", "evidence-2", "RELEVANT_EVIDENCE_CHANGED"),
        ("verification_contract_revision", "contract-2", "VERIFICATION_CONTRACT_CHANGED"),
    ],
)
def test_verifier_or_evidence_change_invalidates_reuse(changed_field, current_value, expected_reason):
    revision = create_claim_revision(
        claim_id="C1", revision_id="R1", text="Claim A.", scope=SCOPE, provenance_ids=("SRC-1",)
    )
    prior = {
        "claim_id": revision.claim_id,
        "revision_id": revision.revision_id,
        "content_digest": revision.content_digest,
        "verifier_revision": "verify-1",
            "verification_contract_revision": "contract-1",
        "evidence_digest": "evidence-1",
        "verification_status": "VERIFIED",
    }
    current_contract = "contract-1"
    if changed_field == "verifier_revision":
        current_verifier = current_value
        current_evidence = "evidence-1"
    elif changed_field == "verification_contract_revision":
        current_verifier = "verify-1"
        current_contract = current_value
        current_evidence = "evidence-1"
    else:
        current_verifier = "verify-1"
        current_evidence = current_value
    result = assess_verification_reuse(
        revision=revision,
        prior_binding=prior,
        current_verifier_revision=current_verifier,
        current_contract_revision=current_contract,
        current_evidence_digest=current_evidence,
    )
    assert result["review_state"] == "REQUIRES_REVERIFICATION"
    assert expected_reason in result["reasons"]


def test_unverified_prior_result_is_unresolved_not_reusable():
    revision = create_claim_revision(
        claim_id="C1", revision_id="R1", text="Claim A.", scope=SCOPE, provenance_ids=("SRC-1",)
    )
    result = assess_verification_reuse(
        revision=revision,
        prior_binding={
            "claim_id": revision.claim_id,
            "revision_id": revision.revision_id,
            "content_digest": revision.content_digest,
            "verifier_revision": "verify-1",
            "verification_contract_revision": "contract-1",
            "evidence_digest": "evidence-1",
            "verification_status": "UNVERIFIED",
        },
        current_verifier_revision="verify-1",
        current_contract_revision="contract-1",
        current_evidence_digest="evidence-1",
    )
    assert result["review_state"] == "UNRESOLVED"
    assert result["reuse_allowed"] is False


def test_verification_contract_revision_is_required():
    revision = create_claim_revision(
        claim_id="C1", revision_id="R1", text="Claim A.", scope=SCOPE, provenance_ids=("SRC-1",)
    )
    with pytest.raises(ValueError, match="VERIFICATION_CONTRACT_REVISION_REQUIRED"):
        assess_verification_reuse(
            revision=revision,
            prior_binding={},
            current_verifier_revision="verify-1",
            current_contract_revision="",
            current_evidence_digest="evidence-1",
        )


def test_claim_and_revision_ids_are_required():
    with pytest.raises(ValueError, match="CLAIM_ID_REQUIRED"):
        create_claim_revision(claim_id="", revision_id="R1", text="x", scope=SCOPE, provenance_ids=("SRC-1",))


def test_revision_without_provenance_cannot_reuse_prior_verification():
    revision = create_claim_revision(
        claim_id="C1", revision_id="R1", text="Claim A.", scope=SCOPE
    )
    result = assess_verification_reuse(
        revision=revision,
        prior_binding={
            "claim_id": revision.claim_id,
            "revision_id": revision.revision_id,
            "content_digest": revision.content_digest,
            "verifier_revision": "verify-1",
            "verification_contract_revision": "contract-1",
            "evidence_digest": "evidence-1",
            "verification_status": "VERIFIED",
        },
        current_verifier_revision="verify-1",
        current_contract_revision="contract-1",
        current_evidence_digest="evidence-1",
    )
    assert result["review_state"] == "UNRESOLVED"
    assert result["reuse_allowed"] is False
    assert "REVISION_PROVENANCE_MISSING" in result["reasons"]
