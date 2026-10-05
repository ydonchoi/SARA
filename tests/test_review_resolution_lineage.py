from SARA_v2.3.review_resolution_lineage import ReviewResolutionLineageGate

def test_valid_resolution_is_bound_to_claim_and_prior_review_state():
    r = ReviewResolutionLineageGate().evaluate(
        review_completed=True, review_event_id="review-001", claim_id="claim-001",
        prior_review_status="REVISION_REQUIRED", resolution="UPHOLD")
    assert r.accepted is True
    assert r.review_event_id == "review-001"
    assert r.claim_id == "claim-001"
    assert r.prior_review_status == "REVISION_REQUIRED"
    assert r.resolution_status == "UPHOLD"
    assert r.truthfulness_status == "UNASSESSED"

def test_missing_claim_id_rejects_lineage():
    r = ReviewResolutionLineageGate().evaluate(
        review_completed=True, review_event_id="review-001", claim_id=None,
        prior_review_status="REVISION_REQUIRED", resolution="UPHOLD")
    assert r.accepted is False
    assert r.resolution_status == "INVALID_REVIEW_LINEAGE"

def test_invalid_prior_state_rejects_lineage():
    r = ReviewResolutionLineageGate().evaluate(
        review_completed=True, review_event_id="review-001", claim_id="claim-001",
        prior_review_status="VERIFIED", resolution="UPHOLD")
    assert r.accepted is False
    assert r.resolution_status == "INVALID_PRIOR_REVIEW_STATE"

def test_unknown_resolution_rejects_lineage():
    r = ReviewResolutionLineageGate().evaluate(
        review_completed=True, review_event_id="review-001", claim_id="claim-001",
        prior_review_status="REVISION_REQUIRED", resolution="UNKNOWN")
    assert r.accepted is False
    assert r.resolution_status == "INVALID_REVIEW_RESOLUTION"

def test_incomplete_review_cannot_be_resolved():
    r = ReviewResolutionLineageGate().evaluate(
        review_completed=False, review_event_id="review-001", claim_id="claim-001",
        prior_review_status="REVISION_REQUIRED", resolution="UPHOLD")
    assert r.accepted is False
    assert r.resolution_status == "REVIEW_REQUIRED"
    assert r.truthfulness_status == "UNASSESSED"
