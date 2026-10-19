"""SARA-owned JEV-style judgment model contract.

This is an internal SARA judgment capability, not an adapter to an external JEV
service. It supplies a judgment rubric to SARA's own model runtime and validates
the returned structured judgment. A passing contract test does not establish
semantic accuracy or prove that a live dialogue runtime is connected.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from hashlib import sha256
import json
from math import isfinite
from typing import Any

JUDGMENT_STATUSES = {
    "INFERENCE_PRESENT",
    "NO_INFERENCE_DETECTED",
    "AMBIGUOUS",
}
INFERENCE_TYPES = {
    "DEDUCTIVE", "INDUCTIVE", "ABDUCTIVE", "CAUSAL", "ANALOGICAL",
    "GENERALIZATION", "INTERPRETIVE", "PREDICTIVE", "NORMATIVE", "OTHER", "NONE",
}
CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}
EXECUTION_STATUSES = {"SUCCEEDED", "FAILED", "TIMEOUT", "INVALID_OUTPUT"}

SARA_JEV_STYLE_JUDGMENT_RUBRIC = """You are SARA's internal inference-judgment component.
Judge whether the supplied dialogue turn contains a conclusion, interpretation,
causal explanation, prediction, generalization, or other claim derived from
premises or context rather than only a directly stated/quoted fact. When
claim_candidates are supplied, bind detected inference to the candidate IDs
whose propositions are actually expressed or entailed by the turn; never invent
candidate IDs or claim references.

Distinguish:
- directly stated or attributed content from a conclusion inferred from it;
- inference presence from inference correctness;
- an inference candidate from a verified or false claim;
- missing information from evidence against a claim.

For any detected inference, identify the shortest relevant text spans, the
inference type, the stated or implied premises, and the inferential gap or
warrant when discernible. Do not invent evidence or source references. If the
turn is genuinely ambiguous, return AMBIGUOUS and explain what is missing.
Do not use a numeric probability or pretend that categorical confidence is
calibrated. Do not decide whether a claim is true; do not perform SARA's
subsequent evidence verification.

Return a JSON object with exactly these fields:
request_id, input_revision_digest, judgment_status, inference_types,
basis_spans, rationale, uncertainty_reason, confidence, premise_refs,
claim_refs, evidence_ids, provenance_ids.
judgment_status must be INFERENCE_PRESENT, NO_INFERENCE_DETECTED, or AMBIGUOUS.
confidence must be HIGH, MEDIUM, or LOW. For NO_INFERENCE_DETECTED, use
inference_types=[] and basis_spans=[]. All references must be drawn from the
input. Echo request_id and input_revision_digest exactly.
"""

GenerateCallable = Callable[[str, Mapping[str, Any], float], Mapping[str, Any]]


class InternalJudgmentError(ValueError):
    """Raised when a judgment request is structurally invalid."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    except (TypeError, ValueError) as exc:
        raise InternalJudgmentError("JUDGMENT_INPUT_NOT_JSON_SERIALIZABLE") from exc


def compute_judgment_input_digest(request: Mapping[str, Any]) -> str:
    """Hash the input fields that the judgment must be bound to."""
    if not isinstance(request, Mapping):
        raise InternalJudgmentError("JUDGMENT_REQUEST_MUST_BE_MAPPING")
    required = ("request_id", "conversation_id", "turn_id", "content")
    for key in required:
        value = request.get(key)
        if not isinstance(value, str) or not value.strip():
            raise InternalJudgmentError(f"JUDGMENT_{key.upper()}_REQUIRED")
    if not isinstance(request.get("context", ""), (str, list, tuple, Mapping)):
        raise InternalJudgmentError("JUDGMENT_CONTEXT_INVALID")
    if not isinstance(request.get("reference_catalog", {}), Mapping):
        raise InternalJudgmentError("JUDGMENT_REFERENCE_CATALOG_INVALID")
    claim_candidates = request.get("claim_candidates", [])
    if not isinstance(claim_candidates, list):
        raise InternalJudgmentError("JUDGMENT_CLAIM_CANDIDATES_MUST_BE_LIST")
    candidate_ids = []
    for candidate in claim_candidates:
        if not isinstance(candidate, Mapping):
            raise InternalJudgmentError("JUDGMENT_CLAIM_CANDIDATE_MUST_BE_MAPPING")
        for field in ("id", "text"):
            value = candidate.get(field)
            if not isinstance(value, str) or not value.strip():
                raise InternalJudgmentError(f"JUDGMENT_CLAIM_CANDIDATE_{field.upper()}_REQUIRED")
        candidate_ids.append(candidate["id"])
    if len(set(candidate_ids)) != len(candidate_ids):
        raise InternalJudgmentError("JUDGMENT_DUPLICATE_CLAIM_CANDIDATE_ID")
    payload = {
        "request_id": request["request_id"],
        "conversation_id": request["conversation_id"],
        "turn_id": request["turn_id"],
        "content": request["content"],
        "context": request.get("context", ""),
        "reference_catalog": request.get("reference_catalog", {}),
        "claim_candidates": claim_candidates,
    }
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list):
        raise InternalJudgmentError(f"JUDGMENT_{field.upper()}_MUST_BE_LIST")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise InternalJudgmentError(f"JUDGMENT_{field.upper()}_ITEM_INVALID")
    if len(set(value)) != len(value):
        raise InternalJudgmentError("JUDGMENT_DUPLICATE_REFERENCE")
    return list(value)


class SARAInternalJudgmentModel:
    """Use SARA's own model runtime to judge inference presence and type.

    The generate callable is the host SARA runtime's model-generation function;
    it is not an external JEV endpoint. This boundary intentionally accepts the
    runtime as a dependency so contract tests can use deterministic stubs.
    """

    def __init__(
        self,
        generate: GenerateCallable,
        *,
        model_id: str,
        model_revision: str,
        rubric_revision: str = "sara-jev-style-judgment-rubric-v0.1",
    ) -> None:
        if not callable(generate):
            raise InternalJudgmentError("SARA_MODEL_RUNTIME_REQUIRED")
        for value, code in (
            (model_id, "SARA_JUDGMENT_MODEL_ID_REQUIRED"),
            (model_revision, "SARA_JUDGMENT_MODEL_REVISION_REQUIRED"),
            (rubric_revision, "SARA_JUDGMENT_RUBRIC_REVISION_REQUIRED"),
        ):
            if not isinstance(value, str) or not value.strip():
                raise InternalJudgmentError(code)
        self._generate = generate
        self.model_id = model_id
        self.model_revision = model_revision
        self.rubric_revision = rubric_revision

    def judge(
        self, request: Mapping[str, Any], *, timeout_seconds: float
    ) -> dict[str, Any]:
        digest = compute_judgment_input_digest(request)
        supplied_digest = request.get("input_revision_digest")
        if supplied_digest is not None and supplied_digest != digest:
            raise InternalJudgmentError("JUDGMENT_INPUT_REVISION_MISMATCH")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise InternalJudgmentError("JUDGMENT_TIMEOUT_MUST_BE_POSITIVE_FINITE")

        payload = {
            "request_id": request["request_id"],
            "conversation_id": request["conversation_id"],
            "turn_id": request["turn_id"],
            "content": request["content"],
            "context": request.get("context", ""),
            "reference_catalog": request.get("reference_catalog", {}),
            "claim_candidates": request.get("claim_candidates", []),
            "input_revision_digest": digest,
            "output_contract": {
                "judgment_status": sorted(JUDGMENT_STATUSES),
                "inference_types": sorted(INFERENCE_TYPES),
                "confidence": sorted(CONFIDENCE_LEVELS),
                "references_must_come_from_input": True,
            },
        }
        try:
            raw = self._generate(
                SARA_JEV_STYLE_JUDGMENT_RUBRIC, payload, float(timeout_seconds)
            )
        except TimeoutError:
            return self._execution_failure(request, digest, "TIMEOUT")
        except Exception:
            return self._execution_failure(request, digest, "FAILED")

        try:
            result = self._validate_output(
                raw,
                request_id=request["request_id"],
                digest=digest,
                content=request["content"],
                reference_catalog=request.get("reference_catalog", {}),
            )
        except InternalJudgmentError:
            return self._execution_failure(request, digest, "INVALID_OUTPUT")
        result.update({
            "execution_status": "SUCCEEDED",
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "rubric_revision": self.rubric_revision,
            "source": "SARA_INTERNAL_JEV_STYLE_JUDGMENT",
            "is_evidence": False,
            "claim_truth_assessed": False,
            "is_claim_verification": False,
        })
        return result

    def _validate_output(
        self,
        raw: Any,
        *,
        request_id: str,
        digest: str,
        content: str,
        reference_catalog: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(raw, Mapping):
            raise InternalJudgmentError("JUDGMENT_OUTPUT_MUST_BE_MAPPING")
        if raw.get("request_id") != request_id:
            raise InternalJudgmentError("JUDGMENT_REQUEST_ID_MISMATCH")
        if raw.get("input_revision_digest") != digest:
            raise InternalJudgmentError("JUDGMENT_OUTPUT_DIGEST_MISMATCH")
        status = raw.get("judgment_status")
        if not isinstance(status, str) or status not in JUDGMENT_STATUSES:
            raise InternalJudgmentError("JUDGMENT_STATUS_INVALID")
        types = _string_list(raw.get("inference_types"), "inference_types")
        spans = _string_list(raw.get("basis_spans"), "basis_spans")
        premise_refs = _string_list(raw.get("premise_refs"), "premise_refs")
        claim_refs = _string_list(raw.get("claim_refs"), "claim_refs")
        evidence_ids = _string_list(raw.get("evidence_ids"), "evidence_ids")
        provenance_ids = _string_list(raw.get("provenance_ids"), "provenance_ids")
        if any(item not in INFERENCE_TYPES for item in types):
            raise InternalJudgmentError("JUDGMENT_INFERENCE_TYPE_INVALID")
        confidence = raw.get("confidence")
        if not isinstance(confidence, str) or confidence not in CONFIDENCE_LEVELS:
            raise InternalJudgmentError("JUDGMENT_CONFIDENCE_INVALID")
        rationale = raw.get("rationale")
        uncertainty = raw.get("uncertainty_reason", "")
        if not isinstance(rationale, str) or not rationale.strip():
            raise InternalJudgmentError("JUDGMENT_RATIONALE_REQUIRED")
        if not isinstance(uncertainty, str):
            raise InternalJudgmentError("JUDGMENT_UNCERTAINTY_REASON_INVALID")
        if any(span not in content for span in spans):
            raise InternalJudgmentError("JUDGMENT_BASIS_SPAN_NOT_IN_INPUT")
        catalog_fields = (
            ("premise_refs", premise_refs),
            ("claim_refs", claim_refs),
            ("evidence_ids", evidence_ids),
            ("provenance_ids", provenance_ids),
        )
        for field, refs in catalog_fields:
            known = reference_catalog.get(field, [])
            if not isinstance(known, list) or any(
                not isinstance(value, str) or not value.strip() for value in known
            ):
                raise InternalJudgmentError("JUDGMENT_REFERENCE_CATALOG_INVALID")
            if any(value not in known for value in refs):
                raise InternalJudgmentError(f"JUDGMENT_UNKNOWN_{field.upper()}")

        if status == "INFERENCE_PRESENT":
            if not types or "NONE" in types or not spans:
                raise InternalJudgmentError("INFERENCE_PRESENT_REQUIRES_TYPE_AND_BASIS")
        elif status == "NO_INFERENCE_DETECTED":
            if (types and types != ["NONE"]) or spans:
                raise InternalJudgmentError("NO_INFERENCE_MUST_NOT_EMIT_INFERENCE_BASIS")
            types = []
        elif status == "AMBIGUOUS":
            if not uncertainty.strip():
                raise InternalJudgmentError("AMBIGUOUS_JUDGMENT_REQUIRES_UNCERTAINTY")
            if confidence == "HIGH":
                raise InternalJudgmentError("AMBIGUOUS_JUDGMENT_CANNOT_HAVE_HIGH_CONFIDENCE")
        return {
            "request_id": request_id,
            "input_revision_digest": digest,
            "judgment_status": status,
            "inference_types": types,
            "basis_spans": spans,
            "rationale": rationale.strip(),
            "uncertainty_reason": uncertainty.strip(),
            "confidence": confidence,
            "premise_refs": premise_refs,
            "claim_refs": claim_refs,
            "evidence_ids": evidence_ids,
            "provenance_ids": provenance_ids,
            "review_required": status != "NO_INFERENCE_DETECTED" or confidence != "HIGH",
        }

    def _execution_failure(
        self, request: Mapping[str, Any], digest: str, status: str
    ) -> dict[str, Any]:
        return {
            "request_id": request.get("request_id"),
            "input_revision_digest": digest,
            "judgment_status": "NOT_ASSESSED",
            "inference_types": [],
            "basis_spans": [],
            "rationale": "",
            "uncertainty_reason": "SARA model judgment did not produce a usable result.",
            "confidence": "UNASSESSED",
            "premise_refs": [],
            "claim_refs": [],
            "evidence_ids": [],
            "provenance_ids": [],
            "review_required": True,
            "execution_status": status,
            "model_id": self.model_id,
            "model_revision": self.model_revision,
            "rubric_revision": self.rubric_revision,
            "source": "SARA_INTERNAL_JEV_STYLE_JUDGMENT",
            "is_evidence": False,
            "claim_truth_assessed": False,
            "is_claim_verification": False,
        }
