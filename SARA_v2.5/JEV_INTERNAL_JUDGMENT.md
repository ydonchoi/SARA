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

The result is bound to a canonical digest of `request_id`, `conversation_id`, `turn_id`, `content`, and `context`. The rubric requires the model to separate inference presence from inference correctness, cite relevant spans and known references, state uncertainty, and avoid truth-verification claims.

The output is decision support only:
- it is not research evidence;
- it does not set a claim to `VERIFIED`, `CONTRADICTED`, or any other truth status;
- an execution error is `NOT_ASSESSED`, never a negative inference finding;
- a stale or mismatched digest cannot silently suppress SARA activation.

## Integration boundary and evidence

The Python contract invokes a supplied **SARA model-runtime callable**, not an external JEV provider. The test suite uses deterministic test doubles to verify request binding, structured output validation, and fail-closed activation policy. This is not a live-model quality test and does not prove that the repository is connected to an actual dialogue runtime.

Before canonical promotion, the deployment must demonstrate that the actual SARA runtime calls the internal judgment component at the intended point in dialogue processing; that activation decisions route to the selective reverification workflow; that factual verification routes remain independent; and that a frozen, independently adjudicated benchmark meets predeclared false-trigger and missed-inference thresholds.
