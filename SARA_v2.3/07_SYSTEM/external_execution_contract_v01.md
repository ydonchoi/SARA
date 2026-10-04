# SARA v2.3 — External Execution Contract v0.1

## Status
PROPOSED — implementation contract for external callers.

This contract adds an execution boundary to SARA v2.3 without changing the existing research-verification semantics.

## Request
request:
  request_id:
  capability: verify_claim
  claim:
    id:
    text:
    type:
    source:
    evidence_ids: []
    inference_level:
    inference_basis:
    scope:
  evidence: []
  provenance_ids: []
  adapter_revision:
  requested_at:
  environment:

## Response
response:
  request_id:
  claim_id:
  provider_id: SARA
  adapter_revision:
  status: SUCCEEDED | FAILED | REJECTED
  external_result_id:
  external_result_provenance_ids: []
  verification:
    verification_status:
    verification_layer: research_verification
    findings: []
    uncertainty:
    structural_validity:
    truthfulness_status: UNASSESSED
  reproduction_status:
  external_citation_verification:
  timestamp:
  environment:
  failure:

## Boundary rules
1. response claim_id must exactly match the request claim.id; verification results must be bound to the claim they verify.
2. verification_layer for claim/evidence verification is always research_verification.
2. truthfulness_status defaults to UNASSESSED; structural validity does not establish truthfulness. ESTABLISHED requires external_citation_verification.status=VERIFIED.
3. SIMULATED_REPRODUCTION is never verification evidence.
4. External citation verification remains a separate field.
5. Missing provenance for a consequential result is an execution-contract failure. Request/input provenance must not be reused as external-result provenance.
6. Execution SUCCEEDED does not imply verification VERIFIED.
7. SARA does not make a Human Decision.
8. Unknown capabilities or malformed requests must be rejected explicitly.

## Compatibility target
This contract is intentionally transport-neutral. A Python API, CLI, or HTTP service may implement it without changing the Research OS Core boundary.

## Relationship to existing SARA v2.3
This contract exposes existing v2.3 schema semantics; it does not redefine claim/evidence status vocabularies or the A6 simulation firewall.