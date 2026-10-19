from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from conflict_adjudication import EvidencePosition, adjudicate_evidence_conflict


def item(eid, relation, scope="S1", time="T1", status="VERIFIED", source="SRC"):
    return EvidencePosition(eid, relation, status, scope, time, source)


def test_mixed_verified_evidence_same_context_is_unresolved_not_claim_contradiction():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[
            item("E1", "SUPPORTS", source="STUDY-A"),
            item("E2", "CHALLENGES", source="STUDY-B"),
        ],
    )
    assert result["conflict_status"] == "UNRESOLVED_CONFLICT"
    assert result["claim_verification_status"] == "UNASSESSED"
    assert result["truthfulness_status"] == "UNASSESSED"
    assert result["automatic_majority_resolution"] is False


def test_mixed_polarities_different_context_require_contextual_review():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[
            item("E1", "SUPPORTS", scope="adults"),
            item("E2", "CHALLENGES", scope="children"),
        ],
    )
    assert result["conflict_status"] == "CONTEXTUAL_DIVERGENCE_REVIEW"


def test_one_polarity_does_not_automatically_verify_claim():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[item("E1", "SUPPORTS")],
    )
    assert result["conflict_status"] == "NO_CROSS_POLARITY_CONFLICT_OBSERVED"
    assert result["claim_verification_status"] == "UNASSESSED"


def test_unverified_support_does_not_resolve_conflict():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[
            item("E1", "SUPPORTS", status="UNVERIFIED"),
            item("E2", "CHALLENGES", status="VERIFIED"),
        ],
    )
    assert result["conflict_status"] == "NO_CROSS_POLARITY_CONFLICT_OBSERVED"
    assert result["supporting_evidence_ids"] == []
    assert result["non_eligible_evidence_ids"] == ["E1"]


def test_duplicate_evidence_ids_are_rejected():
    with pytest.raises(ValueError, match="DUPLICATE_EVIDENCE_ID"):
        adjudicate_evidence_conflict(
            claim_id="C1",
            evidence_positions=[item("E1", "SUPPORTS"), item("E1", "CHALLENGES")],
        )


def test_no_eligible_evidence_remains_unassessed():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[],
    )
    assert result["conflict_status"] == "UNASSESSED"
    assert result["claim_verification_status"] == "UNASSESSED"



def test_partially_verified_opposing_evidence_requires_review():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[
            item("E1", "SUPPORTS", status="VERIFIED"),
            item("E2", "CHALLENGES", status="PARTIALLY_VERIFIED"),
        ],
    )
    assert result["conflict_status"] == "POTENTIAL_CONFLICT_REVIEW"
    assert result["partially_verified_challenging_evidence_ids"] == ["E2"]
    assert result["claim_verification_status"] == "UNASSESSED"


def test_partial_evidence_across_scopes_is_contextual_divergence():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[
            item("E1", "SUPPORTS", scope="adults", status="PARTIALLY_VERIFIED"),
            item("E2", "CHALLENGES", scope="children", status="VERIFIED"),
        ],
    )
    assert result["conflict_status"] == "CONTEXTUAL_DIVERGENCE_REVIEW"
    assert result["source_independence_status"] == "NOT_ADJUDICATED"


def test_neutral_evidence_does_not_claim_to_resolve_polarity():
    result = adjudicate_evidence_conflict(
        claim_id="C1",
        evidence_positions=[
            EvidencePosition("E1", "NEUTRAL", "VERIFIED", "S1", "T1", "SRC")
        ],
    )
    assert result["conflict_status"] == "UNASSESSED"
    assert result["non_eligible_evidence_ids"] == ["E1"]


def test_empty_scope_metadata_is_rejected():
    with pytest.raises(ValueError, match="INVALID_SCOPE_KEY"):
        adjudicate_evidence_conflict(
            claim_id="C1",
            evidence_positions=[
                EvidencePosition("E1", "SUPPORTS", "VERIFIED", "", "T1", "SRC")
            ],
        )
