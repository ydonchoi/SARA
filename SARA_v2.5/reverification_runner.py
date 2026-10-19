"""SARA v2.5: execute planned reverification jobs through an injected verifier.

This module runs only claims present in an accepted impact plan. It validates
revision, verifier-contract, evidence, and provenance bindings, records provider
execution outcomes, and returns proposals awaiting review. It does not mutate
current claim state or establish truthfulness.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from math import isfinite
from typing import Any

from claim_identity import VERIFICATION_STATUSES, compute_content_digest

VerificationCallable = Callable[[Mapping[str, Any], float], Mapping[str, Any]]


class ReverificationExecutionError(ValueError):
    """Raised when a re-verification plan or invocation request is invalid."""


class SelectiveReverificationRunner:
    """Run planned verifications without silently promoting the returned status."""

    def __init__(
        self,
        verify: VerificationCallable,
        *,
        verifier_revision: str,
        verification_contract_revision: str,
        runner_revision: str = "sara-selective-reverification-runner-v0.1",
    ) -> None:
        if not callable(verify):
            raise ReverificationExecutionError("VERIFICATION_CALLABLE_REQUIRED")
        for value, code in (
            (verifier_revision, "VERIFIER_REVISION_REQUIRED"),
            (verification_contract_revision, "VERIFICATION_CONTRACT_REVISION_REQUIRED"),
            (runner_revision, "REVERIFICATION_RUNNER_REVISION_REQUIRED"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ReverificationExecutionError(code)
        self._verify = verify
        self.verifier_revision = verifier_revision
        self.verification_contract_revision = verification_contract_revision
        self.runner_revision = runner_revision

    def execute(
        self,
        *,
        plan: Mapping[str, Any],
        claim_revisions: Mapping[str, Mapping[str, Any]],
        evidence_by_claim: Mapping[str, list[Mapping[str, Any]]],
        prior_bindings: Mapping[str, Mapping[str, Any]],
        current_evidence_digests: Mapping[str, str],
        timeout_seconds: float,
    ) -> dict[str, Any]:
        if not isinstance(plan, Mapping) or plan.get("plan_status") != "PLANNED_NOT_EXECUTED":
            raise ReverificationExecutionError("REVERIFICATION_PLAN_NOT_EXECUTABLE")
        if not isinstance(claim_revisions, Mapping):
            raise ReverificationExecutionError("CLAIM_REVISIONS_MUST_BE_MAPPING")
        if not isinstance(evidence_by_claim, Mapping):
            raise ReverificationExecutionError("EVIDENCE_BY_CLAIM_MUST_BE_MAPPING")
        if not isinstance(prior_bindings, Mapping):
            raise ReverificationExecutionError("PRIOR_BINDINGS_MUST_BE_MAPPING")
        if not isinstance(current_evidence_digests, Mapping):
            raise ReverificationExecutionError("EVIDENCE_DIGESTS_MUST_BE_MAPPING")
        if (
            not isinstance(timeout_seconds, (int, float))
            or isinstance(timeout_seconds, bool)
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ReverificationExecutionError("INVALID_REVERIFICATION_TIMEOUT")

        impacted = plan.get("impacted_claims")
        if not isinstance(impacted, list):
            raise ReverificationExecutionError("IMPACTED_CLAIMS_MUST_BE_LIST")
        ids = []
        for item in impacted:
            if not isinstance(item, Mapping):
                raise ReverificationExecutionError("INVALID_IMPACTED_CLAIM_RECORD")
            claim_id = item.get("claim_id")
            if not isinstance(claim_id, str) or not claim_id.strip():
                raise ReverificationExecutionError("IMPACTED_CLAIM_ID_REQUIRED")
            if item.get("review_state") != "REQUIRES_REVERIFICATION":
                raise ReverificationExecutionError("IMPACTED_CLAIM_NOT_MARKED_FOR_REVERIFICATION")
            if claim_id in ids:
                raise ReverificationExecutionError("DUPLICATE_IMPACTED_CLAIM_ID")
            ids.append(claim_id)

        results = []
        for impact in impacted:
            claim_id = impact["claim_id"]
            revision = claim_revisions.get(claim_id)
            if not isinstance(revision, Mapping):
                results.append(self._failure(claim_id, None, "INCOMPLETE", "CURRENT_CLAIM_REVISION_MISSING", impact))
                continue

            required = ("claim_id", "revision_id", "text", "scope", "content_digest")
            if any(key not in revision for key in required):
                results.append(self._failure(claim_id, revision.get("revision_id"), "INCOMPLETE", "CURRENT_CLAIM_REVISION_INCOMPLETE", impact))
                continue
            if revision.get("claim_id") != claim_id:
                results.append(self._failure(claim_id, revision.get("revision_id"), "INVALID_OUTPUT", "CURRENT_CLAIM_ID_MISMATCH", impact))
                continue
            if not isinstance(revision.get("text"), str) or not revision["text"].strip():
                results.append(self._failure(claim_id, revision.get("revision_id"), "INVALID_OUTPUT", "CURRENT_CLAIM_TEXT_INVALID", impact))
                continue
            try:
                computed_digest = compute_content_digest(revision["text"], revision["scope"])
            except (TypeError, ValueError):
                results.append(self._failure(claim_id, revision.get("revision_id"), "INVALID_OUTPUT", "CURRENT_CLAIM_SCOPE_INVALID", impact))
                continue
            if computed_digest != revision["content_digest"]:
                results.append(self._failure(claim_id, revision.get("revision_id"), "INVALID_OUTPUT", "CURRENT_CLAIM_DIGEST_MISMATCH", impact))
                continue

            evidence = evidence_by_claim.get(claim_id)
            evidence_digest = current_evidence_digests.get(claim_id)
            prior_binding = prior_bindings.get(claim_id)
            if not isinstance(evidence, list):
                results.append(self._failure(claim_id, revision["revision_id"], "INCOMPLETE", "CURRENT_EVIDENCE_SET_MISSING", impact, computed_digest))
                continue
            if not isinstance(evidence_digest, str) or not evidence_digest.strip():
                results.append(self._failure(claim_id, revision["revision_id"], "INCOMPLETE", "CURRENT_EVIDENCE_DIGEST_MISSING", impact, computed_digest))
                continue
            if not isinstance(prior_binding, Mapping):
                results.append(self._failure(claim_id, revision["revision_id"], "INCOMPLETE", "PRIOR_VERIFICATION_BINDING_MISSING", impact, computed_digest))
                continue

            expected_prior_status = impact.get("prior_verification_status")
            if prior_binding.get("verification_status") != expected_prior_status:
                results.append(self._failure(claim_id, revision["revision_id"], "INVALID_OUTPUT", "PRIOR_BINDING_STATUS_MISMATCH", impact, computed_digest))
                continue

            request_id = f"REVERIFY:{claim_id}:{revision['revision_id']}"
            input_provenance_ids = tuple(
                item.get("provenance_id") for item in evidence
                if isinstance(item, Mapping)
                and isinstance(item.get("provenance_id"), str)
                and item.get("provenance_id").strip()
            )
            request = {
                "request_id": request_id,
                "claim_id": claim_id,
                "revision_id": revision["revision_id"],
                "claim_text": revision["text"],
                "scope": dict(revision["scope"]),
                "content_digest": computed_digest,
                "evidence": [dict(item) for item in evidence],
                "evidence_digest": evidence_digest,
                "verifier_revision": self.verifier_revision,
                "verification_contract_revision": self.verification_contract_revision,
                "input_provenance_ids": list(input_provenance_ids),
                "timeout_seconds": float(timeout_seconds),
            }

            try:
                raw = self._verify(request, float(timeout_seconds))
            except TimeoutError:
                results.append(self._failure(claim_id, revision["revision_id"], "TIMEOUT", "VERIFICATION_PROVIDER_TIMEOUT", impact, computed_digest))
                continue
            except Exception as exc:
                results.append(self._failure(claim_id, revision["revision_id"], "FAILED", f"VERIFICATION_PROVIDER_EXCEPTION:{type(exc).__name__}", impact, computed_digest))
                continue

            if not isinstance(raw, Mapping):
                results.append(self._failure(claim_id, revision["revision_id"], "INVALID_OUTPUT", "VERIFICATION_OUTPUT_NOT_OBJECT", impact, computed_digest))
                continue

            keys = (
                "claim_id", "revision_id", "content_digest",
                "evidence_digest", "verifier_revision",
                "verification_contract_revision", "verification_status",
                "external_result_id", "external_result_provenance_ids",
            )
            if any(key not in raw for key in keys):
                results.append(self._failure(claim_id, revision["revision_id"], "INCOMPLETE", "VERIFICATION_OUTPUT_MISSING_REQUIRED_FIELDS", impact, computed_digest))
                continue
            expected = {
                "claim_id": claim_id,
                "revision_id": revision["revision_id"],
                "content_digest": computed_digest,
                "evidence_digest": evidence_digest,
                "verifier_revision": self.verifier_revision,
                "verification_contract_revision": self.verification_contract_revision,
            }
            if any(raw.get(key) != value for key, value in expected.items()):
                results.append(self._failure(claim_id, revision["revision_id"], "INVALID_OUTPUT", "VERIFICATION_OUTPUT_BINDING_MISMATCH", impact, computed_digest))
                continue
            status = raw.get("verification_status")
            if not isinstance(status, str) or status not in VERIFICATION_STATUSES:
                results.append(self._failure(claim_id, revision["revision_id"], "INVALID_OUTPUT", "INVALID_VERIFICATION_STATUS", impact, computed_digest))
                continue
            result_id = raw.get("external_result_id")
            if not isinstance(result_id, str) or not result_id.strip():
                results.append(self._failure(claim_id, revision["revision_id"], "INCOMPLETE", "EXTERNAL_RESULT_ID_REQUIRED", impact, computed_digest))
                continue
            result_provenance = raw.get("external_result_provenance_ids")
            if (
                not isinstance(result_provenance, (list, tuple))
                or not result_provenance
                or any(not isinstance(x, str) or not x.strip() for x in result_provenance)
                or len(set(result_provenance)) != len(result_provenance)
            ):
                results.append(self._failure(claim_id, revision["revision_id"], "INCOMPLETE", "EXTERNAL_RESULT_PROVENANCE_REQUIRED", impact, computed_digest))
                continue
            if set(result_provenance) & set(input_provenance_ids):
                results.append(self._failure(claim_id, revision["revision_id"], "INVALID_OUTPUT", "INPUT_PROVENANCE_REUSED_AS_RESULT_PROVENANCE", impact, computed_digest))
                continue

            results.append({
                "request_id": request_id,
                "claim_id": claim_id,
                "revision_id": revision["revision_id"],
                "content_digest": computed_digest,
                "evidence_digest": evidence_digest,
                "prior_verification_status": expected_prior_status,
                "proposed_verification_status": status,
                "verifier_revision": self.verifier_revision,
                "verification_contract_revision": self.verification_contract_revision,
                "external_result_id": result_id,
                "external_result_provenance_ids": list(result_provenance),
                "execution_status": "SUCCEEDED",
                "review_state": "REQUIRES_HUMAN_OR_POLICY_REVIEW",
                "truthfulness_status": "UNASSESSED",
                "commit_status": "NOT_COMMITTED",
                "is_evidence": False,
                "source": "SARA_SELECTIVE_REVERIFICATION_RUNNER",
                "impact": dict(impact),
            })

        return {
            "runner_revision": self.runner_revision,
            "plan_status": plan.get("plan_status"),
            "execution_status": "COMPLETED_WITH_RESULTS",
            "executed_claim_ids": [x["claim_id"] for x in results if x["execution_status"] == "SUCCEEDED"],
            "failed_claim_ids": [x["claim_id"] for x in results if x["execution_status"] != "SUCCEEDED"],
            "results": results,
            "committed_claim_statuses": {},
            "truthfulness_status": "UNASSESSED",
            "is_evidence": False,
            "source": "SARA_SELECTIVE_REVERIFICATION_RUNNER",
        }

    def _failure(
        self,
        claim_id: str,
        revision_id: str | None,
        execution_status: str,
        failure_code: str,
        impact: Mapping[str, Any],
        content_digest: str | None = None,
    ) -> dict[str, Any]:
        return {
            "claim_id": claim_id,
            "revision_id": revision_id,
            "content_digest": content_digest,
            "prior_verification_status": impact.get("prior_verification_status"),
            "proposed_verification_status": None,
            "execution_status": execution_status,
            "failure_code": failure_code,
            "review_state": "REQUIRES_REVIEW",
            "commit_status": "NOT_COMMITTED",
            "truthfulness_status": "UNASSESSED",
            "is_evidence": False,
            "source": "SARA_SELECTIVE_REVERIFICATION_RUNNER",
            "impact": dict(impact),
        }
