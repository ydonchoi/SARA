from sara_v24_epistemic import ClaimEvaluationState, PremiseEvaluation, validate_state, align_evidence
import pytest


def test_author_explicit_requires_source_evidence_not_historical_timestamp():
    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_REQUIRES_SOURCE_EVIDENCE"):
        validate_state(ClaimEvaluationState("C1", attribution_status="AUTHOR_EXPLICIT", temporal_status="CONTEMPORARY"))


def test_author_explicit_accepts_source_backed_reference_independent_of_temporal_context():
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


def test_author_explicit_rejects_unresolved_evidence_reference():
    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN"):
        validate_state(
            ClaimEvaluationState("C1", attribution_status="AUTHOR_EXPLICIT", attribution_evidence_ids=("E1",)),
            available_evidence_ids=set(),
        )


def test_legacy_verification_status_is_accepted_and_normalized():
    state = validate_state(ClaimEvaluationState("C1", verification_status="PARTIALLY VERIFIED"))
    assert state.verification_status == "PARTIALLY_VERIFIED"


def test_premise_status_is_independent_from_claim_status():
    state = validate_state(ClaimEvaluationState(
        "C1", verification_status="VERIFIED",
        premise_evaluations=(PremiseEvaluation("P1", "CONTRADICTED"),)
    ))
    assert state.verification_status == "VERIFIED"
    assert state.premise_evaluations[0].status == "CONTRADICTED"


def test_duplicate_premise_ids_are_rejected():
    with pytest.raises(ValueError, match="DUPLICATE_PREMISE_ID"):
        validate_state(ClaimEvaluationState("C1", premise_evaluations=(
            PremiseEvaluation("P1"), PremiseEvaluation("P1")
        )))


def test_alignment_requires_explicit_ids():
    with pytest.raises(ValueError):
        align_evidence(relation="SUPPORTS_CLAIM", target_id="", evidence_id="E1")


def test_adapter_never_promotes_to_evidence():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter
    result = CoThoughtsSARAAdapter().evaluate({"claim":{"id":"C1","text":"x"},"premises":[]})
    assert result["verification_status"] == "UNVERIFIED"
    assert result["is_evidence"] is False


def test_adapter_requires_source_for_author_explicit_attribution():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter
    payload = {
        "claim": {"id": "C1", "text": "claim", "attribution_status": "AUTHOR_EXPLICIT",
                  "attribution_evidence_ids": ["E1"]},
        "evidence": [{"id": "E1", "source": "paper.pdf"}],
    }
    result = CoThoughtsSARAAdapter().evaluate(payload)
    assert result["attribution_evidence_ids"] == ["E1"]
    assert result["is_evidence"] is False


def test_adapter_rejects_author_explicit_evidence_without_source():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter
    payload = {
        "claim": {"id": "C1", "text": "claim", "attribution_status": "AUTHOR_EXPLICIT",
                  "attribution_evidence_ids": ["E1"]},
        "evidence": [{"id": "E1", "source": ""}],
    }
    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_EVIDENCE_REFERENCE_UNKNOWN"):
        CoThoughtsSARAAdapter().evaluate(payload)


def test_adapter_rejects_string_instead_of_evidence_id_list():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter
    payload = {
        "claim": {"id": "C1", "text": "claim", "attribution_status": "AUTHOR_EXPLICIT",
                  "attribution_evidence_ids": "E1"},
        "evidence": [{"id": "E1", "source": "paper.pdf"}],
    }
    with pytest.raises(ValueError, match="ATTRIBUTION_EVIDENCE_IDS_MUST_BE_NONEMPTY_LIST"):
        CoThoughtsSARAAdapter().evaluate(payload)
