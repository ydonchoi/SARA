from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

_PATH = Path(__file__).parents[1] / "SARA_v2.3" / "07_SYSTEM" / "sara_callable.py"
_SPEC = spec_from_file_location("p28_sara_callable", _PATH)
_MODULE = module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
_SPEC.loader.exec_module(_MODULE)
CallableSARA = _MODULE.CallableSARA
SARAExecutionError = _MODULE.SARAExecutionError

def _request(review_context):
    return {
        "request_id": "REQ-P28",
        "capability": "verify_claim",
        "claim": {"id": "C-P28", "text": "claim", "type": "FACT", "source": "SRC-P28"},
        "evidence": [],
        "review_context": review_context,
    }

def test_callable_accepts_operational_review_context():
    seen = {}
    def verifier(request):
        seen.update(request)
        return {
            "claim_id": "C-P28", "status": "SUCCEEDED",
            "external_result_provenance_ids": ["PROV-P28"],
            "verification": {
                "verification_status": "UNVERIFIED",
                "verification_layer": "research_verification",
                "truthfulness_status": "UNASSESSED",
            },
        }
    result = CallableSARA(verifier)(_request({
        "status": "CONSUMED_AS_OPERATIONAL_CONTEXT",
        "review_event_id": "REV-P28",
    }))
    assert seen["review_context"]["review_event_id"] == "REV-P28"
    assert result["status"] == "SUCCEEDED"
    assert result["verification"]["truthfulness_status"] == "UNASSESSED"

@pytest.mark.parametrize("field", ["verification_status", "truthfulness_status", "evidence_ids"])
def test_callable_rejects_epistemic_review_context_fields(field):
    with pytest.raises(SARAExecutionError, match="SARA_REVIEW_CONTEXT_EPISTEMIC_FIELD_FORBIDDEN"):
        CallableSARA(lambda request: {})(_request({
            "status": "CONSUMED_AS_OPERATIONAL_CONTEXT",
            field: "FORBIDDEN",
        }))
