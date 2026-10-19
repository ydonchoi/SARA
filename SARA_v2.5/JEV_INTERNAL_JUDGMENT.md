# SARA v2.5 — Internal JEV-Style Judgment, Verification Need & External Check

**Status: prototype; not yet verified as a live dialogue-runtime integration.**

## Intended architecture

SARA's internal JEV-style judgment model emits three distinct decisions:

1. `judgment_status`: whether inference is present, absent, or ambiguous;
2. `verification_need`: whether the turn contains a claim that needs verification;
3. `external_check_need`: whether that verification requires external sources.

The model uses SARA's own injected model-generation callable and a versioned rubric; it does not call an external JEV service. The activation policy then selects:
- `SARA_SELECTIVE_VERIFICATION` when verification or an external check is required;
- `SARA_PRECHECK_REVIEW` when judgment or verification need is ambiguous, low-confidence, unavailable, invalid, or stale;
- `NO_INFERENCE_TRIGGER` only when both verification needs are explicitly `NOT_REQUIRED` with a usable high-confidence judgment.

Inference presence is not identical to verification need. A directly asserted factual claim may require external checking even when no inference is detected. Conversely, an inference does not automatically require an external search.

## Judgment contract

The result is bound to a canonical digest of `request_id`, `conversation_id`, `turn_id`, `content`, `context`, `reference_catalog`, and the full `claim_candidates` (IDs and text). A changed candidate proposition therefore changes the judgment digest. The v0.2 rubric requires the model to separate inference presence from verification need, bind claims requiring verification to candidate IDs, state uncertainty, and avoid truth-verification claims.

The output is decision support only:
- it is not research evidence;
- it does not set a claim to `VERIFIED`, `CONTRADICTED`, or any other truth status;
- an execution error is `NOT_ASSESSED`, never a negative inference finding;
- a stale or mismatched digest cannot silently suppress SARA activation.

## Integration boundary and evidence

The callable route is now exposed as `sara_runtime.process_dialogue_turn(...)` and implemented in `SARA_v2.5/dialogue_runtime.py`. It takes an explicit SARA model-generation callable and routes judgment outcomes as follows:

- A claim is sent to the existing SARA claim-verification facade when verification is required and the judgment returns one or more candidate claim IDs bound to the turn, whether directly asserted or inferred.
- A missing/unbound claim candidate, ambiguous/low-confidence judgment, invalid input, or model timeout goes to precheck instead of silently skipping review.
- A high-confidence result with both needs set to `NOT_REQUIRED` skips only this v2.5 route; other source/factual verification routes are untouched.
- When `external_check_need=REQUIRED`, the runtime invokes the injected external-search callable, normalizes source candidates, and passes them to the verifier. Retrieved candidates remain `UNASSESSED`; no results or a missing search provider produce an explicit `UNVERIFIED`/blocked outcome rather than a false verdict.
- Verification execution output, judgment output, and truthfulness/evidence status remain separate. An optional event sink can record a turn decision, but the sink is caller-managed and does not establish durable storage.

The test suite uses deterministic test doubles to verify the callable route, candidate binding, verifier invocation, fail-closed handling, and event-sink failure visibility. This is **contract/integration-test evidence only**: no real model SDK/provider is configured here, and the actual host dialogue loop/deployment is not independently verified.

Before canonical promotion, the deployment must demonstrate that the actual model-generation and verification callables are bound to the live dialogue loop; that the invoked verification provider runs with the intended source/evidence semantics; that factual verification routes remain independent; that audit events are durable and access-controlled where required; and that a frozen, independently adjudicated benchmark meets predeclared false-trigger, missed-inference, latency, and cost thresholds.


## External-search boundary

The search provider is injected by the host via `process_dialogue_turn(..., external_search_provider=...)`. The repository now defines and tests the callable contract, source-record validation, deduplication, timeout/failure handling, and no-result behavior. It does not configure a live web-search provider, credentials, production transport, or a ChatGPT host integration. See [the external-evidence architecture note](../docs/v2.5-external-evidence-architecture-v0.2.md).
