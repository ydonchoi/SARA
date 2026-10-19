"""SARA v2.5 prototype: evaluator execution boundary.

Evaluator output is a decision-support signal, never evidence or a claim
verification result. Execution failure must not be interpreted as a negative
research finding. The module validates a supplied evaluator result; it does
not call external evaluators or assess semantic correctness itself.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable

EXECUTION_STATUSES = {
    "SUCCEEDED", "FAILED", "TIMEOUT", "INVALID_OUTPUT", "INCOMPLETE"
}
SIGNAL_STATUSES = {
    "ISSUE_CANDIDATE", "NO_ISSUE_REPORTED", "UNASSESSED", "NOT_AVAILABLE"
}
REVIEW_SIGNAL_STATUSES = {"ISSUE_CANDIDATE", "UNASSESSED"}


@dataclass(frozen=True)
class EvaluatorSignal:
    signal_id: str
    evaluator_id: str
    evaluator_revision: str
    rubric_revision: str
    input_revision_digest: str
    execution_status: str
    signal_status: str
    rationale: str = ""
    related_node_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    provenance_ids: tuple[str, ...] = ()


def validate_evaluator_signal(
    signal: EvaluatorSignal,
    *,
    expected_input_revision_digest: str,
    known_node_ids: Iterable[str] = (),
    known_evidence_ids: Iterable[str] = (),
) -> dict:
    """Validate a result envelope without promoting it to evidence or truth."""
    required = (
        (signal.signal_id, "SIGNAL_ID_REQUIRED"),
        (signal.evaluator_id, "EVALUATOR_ID_REQUIRED"),
        (signal.evaluator_revision, "EVALUATOR_REVISION_REQUIRED"),
        (signal.rubric_revision, "EVALUATOR_RUBRIC_REVISION_REQUIRED"),
        (signal.input_revision_digest, "EVALUATOR_INPUT_DIGEST_REQUIRED"),
        (expected_input_revision_digest, "EXPECTED_INPUT_DIGEST_REQUIRED"),
    )
    if any(not isinstance(value, str) or not value.strip() for value, _ in required):
        for value, error in required:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(error)

    if not isinstance(signal.rationale, str):
        raise ValueError("INVALID_EVALUATOR_RATIONALE")

    if not isinstance(signal.execution_status, str) or signal.execution_status not in EXECUTION_STATUSES:
        raise ValueError("INVALID_EVALUATOR_EXECUTION_STATUS")
    if not isinstance(signal.signal_status, str) or signal.signal_status not in SIGNAL_STATUSES:
        raise ValueError("INVALID_EVALUATOR_SIGNAL_STATUS")
    if signal.input_revision_digest != expected_input_revision_digest:
        raise ValueError("EVALUATOR_INPUT_REVISION_MISMATCH")

    for values, error in (
        (signal.related_node_ids, "EMPTY_RELATED_NODE_ID"),
        (signal.evidence_ids, "EMPTY_EVALUATOR_EVIDENCE_ID"),
        (signal.provenance_ids, "EMPTY_EVALUATOR_PROVENANCE_ID"),
    ):
        if any(not isinstance(value, str) or not value.strip() for value in values):
            raise ValueError(error)
        if len(set(values)) != len(values):
            raise ValueError("DUPLICATE_EVALUATOR_REFERENCE")

    known_nodes = set(known_node_ids)
    known_evidence = set(known_evidence_ids)
    if any(node_id not in known_nodes for node_id in signal.related_node_ids):
        raise ValueError("EVALUATOR_REFERENCES_UNKNOWN_NODE")
    if any(evidence_id not in known_evidence for evidence_id in signal.evidence_ids):
        raise ValueError("EVALUATOR_REFERENCES_UNKNOWN_EVIDENCE")

    if signal.execution_status != "SUCCEEDED":
        if signal.signal_status != "NOT_AVAILABLE":
            raise ValueError("FAILED_EVALUATOR_CANNOT_EMIT_RESEARCH_SIGNAL")
        if signal.rationale.strip() or signal.related_node_ids or signal.evidence_ids:
            raise ValueError("UNAVAILABLE_EVALUATOR_SIGNAL_CANNOT_CARRY_FINDING")
    else:
        if signal.signal_status == "NOT_AVAILABLE":
            raise ValueError("SUCCEEDED_EVALUATOR_SIGNAL_STATUS_REQUIRED")
        if signal.signal_status == "ISSUE_CANDIDATE":
            if not signal.rationale.strip():
                raise ValueError("EVALUATOR_CANDIDATE_REQUIRES_RATIONALE")
            if not signal.related_node_ids and not signal.evidence_ids:
                raise ValueError("EVALUATOR_CANDIDATE_REQUIRES_BASIS_REFERENCE")

    result = asdict(signal)
    result["review_required"] = (
        signal.execution_status != "SUCCEEDED"
        or signal.signal_status in REVIEW_SIGNAL_STATUSES
    )
    result["source"] = "SARA_EVALUATOR_SIGNAL"
    result["is_evidence"] = False
    return result
