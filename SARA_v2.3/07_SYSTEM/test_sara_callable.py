import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from sara_callable import CallableSARA, SARAExecutionError

def request():
    return {
        "request_id": "REQ-1",
        "capability": "verify_claim",
        "claim": {
            "id": "C1", "text": "A claim", "type": "research_claim",
            "source": "source-1", "evidence_ids": ["E1"],
            "inference_level": "FACT",
        },
        "evidence": [{"id": "E1", "supports_claims": ["C1"]}],
    }

def response(status="SUCCEEDED"):
    return {
        "request_id": "REQ-1", "claim_id": "C1", "provider_id": "SARA",
        "status": status, "external_result_id": "SARA-R1",
        "external_result_provenance_ids": ["SARA-EVENT-1"],
        "verification": {
            "verification_status": "VERIFIED",
            "verification_layer": "research_verification",
            "truthfulness_status": "UNASSESSED",
        },
    }

class CallableSARATest(unittest.TestCase):
    def test_success_separates_execution_and_verification(self):
        result = CallableSARA(lambda _: response())(request())
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["verification"]["verification_status"], "VERIFIED")

    def test_named_verify_claim_alias_preserves_callable_contract(self):
        result = CallableSARA(lambda _: response()).verify_claim(request())
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["claim_id"], "C1")

    def test_provider_failure_never_becomes_verification(self):
        def fail(_):
            raise RuntimeError("provider unavailable")
        result = CallableSARA(fail)(request())
        self.assertEqual(result["status"], "FAILED")
        self.assertNotIn("verification", result)

    def test_dangling_evidence_is_rejected(self):
        req = request()
        req["claim"]["evidence_ids"] = ["MISSING"]
        with self.assertRaisesRegex(SARAExecutionError, "DANGLING"):
            CallableSARA(lambda _: response())(req)

    def test_invalid_execution_status_is_rejected(self):
        with self.assertRaisesRegex(SARAExecutionError, "STATUS_INVALID"):
            CallableSARA(lambda _: response("VERIFIED"))(request())

    def test_established_truthfulness_requires_verified_citation(self):
        res = response()
        res["verification"]["truthfulness_status"] = "ESTABLISHED"
        with self.assertRaisesRegex(SARAExecutionError, "CITATION_INVALID"):
            CallableSARA(lambda _: res)(request())

    def test_succeeded_requires_result_provenance(self):
        res = response()
        res["external_result_provenance_ids"] = []
        with self.assertRaisesRegex(SARAExecutionError, "PROVENANCE_REQUIRED"):
            CallableSARA(lambda _: res)(request())

    def test_invalid_citation_status_is_rejected(self):
        res = response()
        res["external_citation_verification"] = {"status": "ESTABLISHED"}
        with self.assertRaisesRegex(SARAExecutionError, "CITATION_STATUS_INVALID"):
            CallableSARA(lambda _: res)(request())

if __name__ == "__main__":
    unittest.main()
