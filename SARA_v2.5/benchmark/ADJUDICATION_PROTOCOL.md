# SARA v2.5 Preflight — Independent Adjudication Protocol

## Status

**NOT STARTED / LABELS REMAIN DRAFT.** This protocol describes how to turn the synthetic seed fixture into an adjudicated evaluation set. It is not evidence that adjudication has taken place.

## Unit of adjudication

Each case is assessed against its stated input, scope, dependency graph, prior status, and expected decision boundary. Reviewers must assess the case specification itself, not whether the current prototype happens to emit the expected answer.

## Independent review record

Each reviewer completes a separate record before seeing the other reviewer's decision:

- Case ID and fixture version.
- Reviewer ID and independence declaration.
- Decision from the documented label vocabulary.
- Rationale tied to the case's premises, relations, and scope.
- Uncertainty or missing-context notes.
- Any proposed correction to the case label.

The review records must preserve the initial decisions. Do not overwrite one reviewer's entry with the reconciled decision.

## Disagreement resolution

When reviewers disagree, preserve both decisions and route the case to a designated resolver. The resolver records a decision and rationale. Unresolved disagreement remains a blocker for the gold set.

## Label quality controls

1. Include hard negatives: valid reasoning that resembles a known fallacy.
2. Include insufficient-context and ambiguous cases; the correct label may be UNASSESSED.
3. Keep source truth, claim verification, logical validity, evaluator signal, and execution status as distinct dimensions.
4. Do not infer that a test target is a feature already implemented.
5. Keep draft cases outside precision/recall or calibration calculations.
6. Freeze the fixture and adjudication records before running comparative evaluations.

## Comparative evaluation

Run the same adjudicated cases against the v2.3 baseline, v2.4 without semantic evaluator, and v2.4 with selective evaluator; an unconditional evaluator can be included as a cost/latency comparator. Report false positives, missed issues, unnecessary review/abstention, stale-state reuse, provenance completeness, latency, and cost. Acceptance thresholds must be written down before comparing outcomes; they must not be adjusted after observing results.

## Current blocker

The repository fixture currently declares DRAFT_NOT_INDEPENDENTLY_ADJUDICATED. No performance claim or canonical promotion may treat the fixture as a gold benchmark until independent records and disagreement resolutions are present and verified.
