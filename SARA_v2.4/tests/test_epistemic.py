from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sara_v24_epistemic import (
    ClaimEvaluationState,
    PremiseEvaluation,
    assessment_warnings,
    align_evidence,
    validate_state,
)


def test_author_explicit_requires_source_evidence_not_historical_clock():
    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_REQUIRES_SOURCE_EVIDENCE"):
        validate_state(
            ClaimEvaluationState(
                "C1", attribution_status="AUTHOR_EXPLICIT", temporal_status="HISTORICAL"
            )
        )


def test_author_explicit_can_be_contemporary_when_source_grounded():
    state = validate_state(
        ClaimEvaluationState(
            "C1",
            attribution_status="AUTHOR_EXPLICIT",
            temporal_status="CONTEMPORARY",
            attribution_evidence_ids=("E1",),
        ),
        available_evidence_ids={"E1"},
    )
    assert state.attribution_status == "AUTHOR_EXPLICIT"
    assert state.temporal_status == "CONTEMPORARY"


def test_author_explicit_rejects_unresolved_source_evidence_reference():
    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN"):
        validate_state(
            ClaimEvaluationState(
                "C1",
                attribution_status="AUTHOR_EXPLICIT",
                attribution_evidence_ids=("E404",),
            ),
            available_evidence_ids={"E1"},
        )


def test_premise_status_is_independent_but_conflict_requires_review_signal():
    state = validate_state(
        ClaimEvaluationState(
            "C1",
            verification_status="VERIFIED",
            premise_evaluations=(PremiseEvaluation("P1", "CONTRADICTED"),),
        )
    )
    assert state.verification_status == "VERIFIED"
    assert state.premise_evaluations[0].status == "CONTRADICTED"
    assert assessment_warnings(state) == ("CLAIM_VERIFIED_WITH_CONTRADICTED_PREMISE",)


def test_legacy_verification_alias_normalizes_to_schema_spelling():
    state = validate_state(
        ClaimEvaluationState("C1", verification_status="PARTIALLY VERIFIED")
    )
    assert state.verification_status == "PARTIALLY_VERIFIED"


def test_duplicate_premise_ids_are_rejected():
    with pytest.raises(ValueError, match="DUPLICATE_PREMISE_ID"):
        validate_state(
            ClaimEvaluationState(
                "C1",
                premise_evaluations=(
                    PremiseEvaluation("P1"),
                    PremiseEvaluation("P1"),
                ),
            )
        )


def test_alignment_requires_explicit_ids_and_remains_unassessed():
    with pytest.raises(ValueError, match="EVIDENCE_ALIGNMENT_IDS_REQUIRED"):
        align_evidence(relation="SUPPORTS_CLAIM", target_id="", evidence_id="E1")
    result = align_evidence(relation="SUPPORTS_CLAIM", target_id="C1", evidence_id="E1")
    assert result["status"] == "UNASSESSED"
    assert result["is_evidence"] is False


def test_adapter_never_promotes_to_evidence_and_surfaces_state_conflict():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter

    result = CoThoughtsSARAAdapter().evaluate(
        {
            "claim": {"id": "C1", "text": "x", "verification_status": "VERIFIED"},
            "premises": [{"id": "P1", "verification_status": "CONTRADICTED"}],
        }
    )
    assert result["verification_status"] == "VERIFIED"
    assert result["review_required"] is True
    assert result["logical_audit_status"] == "NOT_RUN"
    assert result["is_evidence"] is False


@pytest.mark.parametrize("evidence_item", [
    {"id": "E1"},
    {"id": "E1", "source": ""},
    {"id": "E1", "source": "   "},
])
def test_adapter_rejects_author_explicit_evidence_without_nonempty_source(evidence_item):
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter

    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN"):
        CoThoughtsSARAAdapter().evaluate({
            "claim": {
                "id": "C1",
                "text": "The author explicitly stated this.",
                "attribution_status": "AUTHOR_EXPLICIT",
                "attribution_evidence_ids": ["E1"],
            },
            "evidence": [evidence_item],
        })


def test_adapter_accepts_author_explicit_attribution_with_source_bearing_evidence():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter

    result = CoThoughtsSARAAdapter().evaluate({
        "claim": {
            "id": "C1",
            "text": "The author explicitly stated this.",
            "attribution_status": "AUTHOR_EXPLICIT",
            "attribution_evidence_ids": ["E1"],
        },
        "evidence": [{
            "id": "E1",
            "source": "https://example.org/primary-source",
        }],
    })
    assert result["attribution_status"] == "AUTHOR_EXPLICIT"
    assert result["attribution_evidence_ids"] == ["E1"]
