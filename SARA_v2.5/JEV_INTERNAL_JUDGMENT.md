# SARA v2.5 — Internal JEV-Style Judgment and Inference Trigger

**Status: prototype; not yet verified as a live dialogue-runtime integration.**

## Intended architecture

SARA has two related but distinct capabilities:

1. **Internal judgment model** (module: internal_judgment_model.py): uses SARA's own model runtime with a SARA-owned, versioned judgment rubric to decide whether a dialogue turn contains inference, classify the inference type, expose the textual basis and uncertainty, and return a revision-bound structured result. It does not call an external JEV service.
2. **Activation policy** (module: inference_trigger.py): consumes that result and selects one of three actions:
   - `SARA_SELECTIVE_VERIFICATION` when inference is detected;
   - `SARA_PRECHECK_REVIEW` when the judgment is ambiguous, low-confidence, unavailable, invalid, or stale;
   - `NO_INFERENCE_TRIGGER` only when no inference is detected with high confidence.

The activation policy is scoped to the inference-triggered path. `NO_INFERENCE_TRIGGER` does **not** disable other factual, source, safety, or policy-based verification routes.

## Judgment contract

The result is bound to a canonical digest of `request_id`, `conversation_id`, `turn_id`, `content`, `context`, `reference_catalog`, and the full `claim_candidates` (IDs and text). A changed candidate proposition therefore changes the judgment digest. The rubric requires the model to separate inference presence from inference correctness, cite relevant spans and known references, bind selected claims to candidate IDs, state uncertainty, and avoid truth-verification claims.

The output is decision support only:
- it is not research evidence;
- it does not set a claim to `VERIFIED`, `CONTRADICTED`, or any other truth status;
- an execution error is `NOT_ASSESSED`, never a negative inference finding;
- a stale or mismatched digest cannot silently suppress SARA activation.

## Integration boundary and evidence

The callable route is now exposed as `sara_runtime.process_dialogue_turn(...)` and implemented in `SARA_v2.5/dialogue_runtime.py`. It takes an explicit SARA model-generation callable and routes judgment outcomes as follows:

- A detected inference is sent to the existing SARA claim-verification facade only when the judgment returns one or more candidate claim IDs bound to the turn.
- A missing/unbound claim candidate, ambiguous/low-confidence judgment, invalid input, or model timeout goes to precheck instead of silently skipping review.
- A high-confidence no-inference result skips only the inference-triggered route; other source/factual verification routes are untouched.
- Verification execution output, judgment output, and truthfulness/evidence status remain separate. An optional event sink can record a turn decision, but the sink is caller-managed and does not establish durable storage.

The test suite uses deterministic test doubles to verify the callable route, candidate binding, verifier invocation, fail-closed handling, and event-sink failure visibility. This is **contract/integration-test evidence only**: no real model SDK/provider is configured here, and the actual host dialogue loop/deployment is not independently verified.

Before canonical promotion, the deployment must demonstrate that the actual model-generation and verification callables are bound to the live dialogue loop; that the invoked verification provider runs with the intended source/evidence semantics; that factual verification routes remain independent; that audit events are durable and access-controlled where required; and that a frozen, independently adjudicated benchmark meets predeclared false-trigger, missed-inference, latency, and cost thresholds.
