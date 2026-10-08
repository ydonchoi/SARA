from sara_v24_epistemic import ClaimEvaluationState, validate_state, align_evidence
import pytest

def test_author_explicit_requires_historical_context():
    with pytest.raises(ValueError, match="AUTHOR_EXPLICIT_REQUIRES_HISTORICAL_CONTEXT"):
        validate_state(ClaimEvaluationState("C1", attribution_status="AUTHOR_EXPLICIT", temporal_status="CONTEMPORARY"))

def test_premise_status_is_independent():
    state=validate_state(ClaimEvaluationState("C1", verification_status="VERIFIED",
        premise_evaluations=(
            __import__("sara_v24_epistemic").PremiseEvaluation("P1","CONTRADICTED"),
        )))
    assert state.verification_status=="VERIFIED"
    assert state.premise_evaluations[0].status=="CONTRADICTED"

def test_alignment_requires_explicit_ids():
    with pytest.raises(ValueError):
        align_evidence(relation="SUPPORTS_CLAIM",target_id="",evidence_id="E1")

def test_adapter_never_promotes_to_evidence():
    from co_thoughts_sara_adapter import CoThoughtsSARAAdapter
    result=CoThoughtsSARAAdapter().evaluate({"claim":{"id":"C1","text":"x"},"premises":[]})
    assert result["verification_status"]=="UNVERIFIED"
    assert result["is_evidence"] is False
