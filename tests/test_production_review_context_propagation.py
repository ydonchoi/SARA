from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]/"SARA_v2.3"
sys.path.insert(0,str(ROOT))
from production_verification_backend import ProductionVerificationBackend

def test_production_backend_propagates_review_context_only_as_context():
    seen={}
    def provider(req):
        seen.update(req)
        return {"status":"SUCCEEDED","external_result_id":"EXT-1",
                "external_result_provenance_ids":["PROV-1"],
                "verification_status":"UNVERIFIED"}
    backend=ProductionVerificationBackend(provider)
    result=backend({"request_id":"R1","claim":{"id":"C1","text":"claim"},
                    "evidence":[],"adapter_revision":"p27",
                    "requested_at":"2026-10-05T00:00:00Z","environment":{},
                    "review_context":{"status":"CONSUMED_AS_OPERATIONAL_CONTEXT","review_event_id":"REV-1"}})
    assert seen["review_context"]["review_event_id"]=="REV-1"
    assert result["verification"]["verification_status"]=="UNVERIFIED"
    assert result["verification"]["truthfulness_status"]=="UNASSESSED"

def test_production_backend_forwards_no_epistemic_review_fields():
    seen={}
    def provider(req):
        seen.update(req)
        return {"status":"SUCCEEDED","external_result_id":"EXT-2",
                "external_result_provenance_ids":["PROV-2"],
                "verification_status":"UNVERIFIED"}
    ProductionVerificationBackend(provider)({"request_id":"R2","claim":{"id":"C2","text":"claim"},
      "evidence":[],"adapter_revision":"p27","requested_at":"2026-10-05T00:00:00Z",
      "environment":{},"review_context":{"status":"CONSUMED_AS_OPERATIONAL_CONTEXT"}})
    assert "verification_status" not in seen["review_context"]
    assert "truthfulness_status" not in seen["review_context"]
    assert "evidence_ids" not in seen["review_context"]
