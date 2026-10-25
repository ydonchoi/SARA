"""v2.5-compatible append-only recording for v3 proposals.

The default ledger is process-local. Hosts must inject a durable ledger adapter
for persistence; proposal recording never commits claim status.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from pathlib import Path
import sys

_V25 = Path(__file__).resolve().parents[1] / "SARA_v2.5"
if str(_V25) not in sys.path:
    sys.path.insert(0, str(_V25))
from claim_identity import compute_content_digest  # noqa: E402
from provenance_ledger import ProvenanceEventLedger  # noqa: E402
from reverification_runner import compute_evidence_digest  # noqa: E402


def record_proposal(ledger: ProvenanceEventLedger, *, claim: Mapping[str, Any],
                    assessment: Mapping[str, Any], evidence: list[Mapping[str, Any]],
                    input_provenance_ids: list[str] | None = None) -> dict[str, Any]:
    """Append revision/proposal events, reusing an identical registered revision."""
    claim_id = str(claim["id"])
    scope = dict(claim.get("scope") or {})
    text = str(claim["text"])
    digest = compute_content_digest(text, scope)
    revision_id = str(assessment.get("claim_revision_id") or "R-" + digest[:16])
    now = datetime.now(timezone.utc).isoformat()
    events = list(ledger.events)
    registered = next((event for event in reversed(events)
                       if event.get("event_type") == "CLAIM_REVISION_REGISTERED"
                       and event.get("claim_id") == claim_id
                       and event.get("revision_id") == revision_id), None)
    created: list[str] = []
    if registered is None:
        event_id = "REV-" + uuid4().hex
        ledger.append_event(
            event_id=event_id, event_type="CLAIM_REVISION_REGISTERED", claim_id=claim_id,
            revision_id=revision_id, actor_id="SARA_V3", occurred_at=now,
            input_digest=digest, payload={"content_digest": digest},
        )
        created.append(event_id)
    elif registered.get("input_digest") != digest:
        raise ValueError("CLAIM_REVISION_ID_DIGEST_MISMATCH")

    provided = list(input_provenance_ids or [])
    if not provided:
        provided = ["INPUT-" + digest[:20]]
    result_provenance_id = "RESULT-" + uuid4().hex
    result_id = "ASSESSMENT-" + uuid4().hex
    proposal_event_id = "PROP-" + uuid4().hex
    evidence_digest = compute_evidence_digest([dict(item) for item in evidence])
    ledger.append_event(
        event_id=proposal_event_id, event_type="VERIFICATION_RESULT_PROPOSED",
        claim_id=claim_id, revision_id=revision_id, actor_id="SARA_V3", occurred_at=now,
        input_digest=digest,
        payload={
            "proposed_verification_status": assessment["verification_status"],
            "external_result_id": result_id,
            "external_result_provenance_ids": [result_provenance_id],
            "input_provenance_ids": provided,
            "evidence_digest": evidence_digest,
            "verifier_revision": assessment["verifier_revision"],
            "verification_contract_revision": assessment["verification_contract_revision"],
            "commit_status": "NOT_COMMITTED",
        },
    )
    created.append(proposal_event_id)
    return {"event_ids": created, "proposal_event_id": proposal_event_id,
            "ledger_status": "IN_MEMORY_ONLY", "commit_status": "NOT_COMMITTED"}
