"""Consume the bounded P23 review audit summary without promoting truth."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class ReviewAuditConsumption:
    accepted: bool
    status: str
    truthfulness_status: str

class ReviewAuditConsumptionGate:
    def evaluate(self, *, audit_complete: bool, audit_status: str,
                 requested_action: str) -> ReviewAuditConsumption:
        if not audit_complete:
            return ReviewAuditConsumption(False, "AUDIT_INCOMPLETE", "UNASSESSED")
        if audit_status != "P18_P22_OPERATIONAL_CHAIN_COMPLETE":
            return ReviewAuditConsumption(False, "INVALID_AUDIT_STATUS", "UNASSESSED")
        if requested_action not in {"AUDIT_RECORD", "HUMAN_REVIEW_CONTEXT"}:
            return ReviewAuditConsumption(False, "UNSUPPORTED_CONSUMPTION", "UNASSESSED")
        return ReviewAuditConsumption(True, "CONSUMED_AS_OPERATIONAL_CONTEXT", "UNASSESSED")
