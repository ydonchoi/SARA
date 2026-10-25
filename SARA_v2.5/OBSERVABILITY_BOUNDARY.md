# SARA v2.5 Observability Boundary — Draft v0.1

**Status:** Design note based on repository code inspection; not a live deployment security assessment.
**Canonical baseline:** SARA v2.4 remains canonical. SARA v3.0 is the integrated successor candidate on `main`; this v2.5 note is version-scoped and does not assert v3 production readiness.

## 1. Finding

The callable dialogue runtime returns a rich result object containing judgment, activation decision, route execution output, verification status, turn identifiers, and audit-record status. Its optional event sink receives a smaller event record containing request/conversation/turn IDs, an input digest, judgment status, activation decision, route execution status, runtime revision, timestamp, and `is_evidence: false`.

The event sink record is narrower than the runtime result, but it is not automatically a durable or access-controlled audit system. The runtime explicitly reports `NOT_CONFIGURED` when no sink is configured and `FAILED` when a configured sink raises an exception. A caller that forwards the entire runtime result to an end user or an untrusted client could disclose more operational detail than needed.

This is a code-level observation, not evidence that a live ChatGPT host is connected to this runtime.

## 2. Three output zones

### A. User-facing status projection

Expose only an allowlisted projection such as:

```json
{
  "schema_version": "sara.public-status.v0.1",
  "status": "REVIEW_REQUIRED",
  "verification_started": false,
  "reason_code": "AMBIGUOUS_INPUT",
  "claim_truth_established": false
}
```

Allowed fields:
- `schema_version`: fixed schema identifier.
- `status`: one of `NOT_ASSESSED`, `REVIEW_REQUIRED`, `VERIFICATION_IN_PROGRESS`, `VERIFICATION_COMPLETED`, `FAILED`.
- `verification_started`: boolean derived from validated route state, not inferred from a judgment alone.
- `reason_code`: stable, non-sensitive public code from an allowlist.
- `claim_truth_established`: always false unless a separate, explicitly defined source-backed claim-verification contract establishes otherwise. A successful model judgment or tool call is insufficient.

The example is illustrative. The exact mapping from internal states to public states must be implemented and tested before use. Do not pass through unknown fields.

### B. Restricted operational audit event

Keep only the minimum fields needed for troubleshooting and accountability:
- pseudonymous request/turn correlation IDs or an access-controlled mapping to them;
- input content digest, not raw content by default;
- judgment status and activation action;
- route execution status and stable error code;
- runtime/code/schema revision and timestamp;
- sink persistence outcome.

If a claim identifier, conversation identifier, or digest can be linked back to a person or sensitive content, treat it as potentially sensitive metadata. Restrict access, define retention, and avoid copying it into user-facing messages. Never record credentials, authorization headers, API keys, or unredacted secrets.

### C. Restricted diagnostic detail

The full judgment payload, rationale, basis spans, selected claim references, provider payloads, stack traces, and detailed verifier output may be needed for debugging or independent audit. They must not be returned by default through the user-facing response boundary. Access should be authenticated, least-privilege, logged, and limited to approved synthetic or appropriately redacted data where possible.

## 3. Failure and inference rules

- A missing event sink means `audit_record_status = NOT_CONFIGURED`; it must never be described as a persisted audit record.
- A sink exception means persistence failed; it must remain visible to authorized operators and must not silently become success.
- A trigger/judgment decision is a routing signal, not evidence.
- Provider invocation is not proof of claim truth.
- Unknown status or reason codes must map to a generic safe failure response; do not expose raw exception messages to the public boundary.
- Public status must be generated from validated internal state, not directly copied from model-generated text.
- Keep the detailed internal result available only to the trusted caller; expose a separate allowlisted serializer for public output.

## 4. Verification required before claiming this boundary is implemented

1. Implement a dedicated public-status projection function.
2. Add allowlist tests proving internal rationale, spans, provider payloads, IDs, raw errors, and unknown fields do not pass through.
3. Add tests for all public status mappings, missing sink, sink failure, malformed status, and verifier failure.
4. Run the tests on the exact candidate commit and retain the CI URLs.
5. Review logging, access controls, retention, and redaction in the actual deployment environment.
6. Perform a host-level test proving the ChatGPT-facing response uses the projection rather than the full runtime result.

Until these are complete, this is a design recommendation only. It does not establish that a public-response sanitizer, secure persistent audit storage, or live host integration exists.
