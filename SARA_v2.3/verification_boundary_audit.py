"""Audit the firewall between review audit context and verification promotion (P25)."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class VerificationBoundaryAudit:
    allowed: bool
    status: str
    truthfulness_status: str

class VerificationBoundaryAuditGate:
    def evaluate(self, *, audit_context_consumed: bool,
                 verification_promotion_requested: bool) -> VerificationBoundaryAudit:
        if audit_context_consumed and verification_promotion_requested:
            return VerificationBoundaryAudit(False, "REVIEW_AUDIT_CANNOT_PROMOTE_VERIFICATION", "UNASSESSED")
        if audit_context_consumed:
            return VerificationBoundaryAudit(True, "REVIEW_AUDIT_BOUNDARY_INTACT", "UNASSESSED")
        return VerificationBoundaryAudit(False, "NO_REVIEW_AUDIT_CONTEXT", "UNASSESSED")
