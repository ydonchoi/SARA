# SARA v2.5 — Claim Identity, Argument Audit & Reverification

## Status

**PROPOSED DESIGN / NOT A RELEASED RUNTIME BASELINE.** SARA v2.4 remains the
canonical verification baseline. This directory records the next-stage
requirements and preflight fixtures; it does not claim that the v2.5 runtime
has been implemented.

## Goal

Increase research-review reliability by making claim identity, argument
structure, evidence conflict, evaluator signals, revision impact, and verification
history explicit. Complexity is justified only where a test demonstrates a
reduction in undetected errors, false positives, stale decisions, or audit gaps.

## Architecture

```text
Claim Identity + Immutable Revision
             |
             v
Argument / Premise Dependency Graph
             |
             v
Evidence Alignment + Conflict State
             |
             v
Logical Audit (v2.4 boundary + explicit semantic reviewer)
             |
             v
Evaluator Signals (separate from evidence and claim status)
             |
             v
Selective Reverification + Provenance Events
             |
             v
Preflight Benchmark / Regression Gate
```

## Existing work to reuse, not duplicate

The current repository already has v2.3 modules/tests for claim-evidence binding,
evidence conflict, contradiction firewall, review-resolution provenance/lineage,
and review-event recording/consistency/integrity. These are implementation
artifacts in the versioned v2.3 layer; their existence does not mean that a v2.5
integration is complete.

Before reusing them, audit their contracts and semantics. In particular,
`claim_evidence_conflict.py` currently maps conflicting verified/contradicted
evidence to claim status `CONTRADICTED`. In v2.5, distinguish **unresolved
evidence conflict** from a conclusion that the claim itself is contradicted.
Adopt or extend existing modules only after a compatibility test demonstrates
that the two states are not conflated.

## Work packages and acceptance gates

### P0 — Claim Identity & Versioning

- Preserve an immutable `claim_id` for the same proposition and scope.
- Give each text/scope revision its own immutable `revision_id`.
- Bind verification to the exact revision and scope digest.
- Text similarity is only a candidate identity signal, never sufficient proof that two claims are identical.
- A material change in meaning or scope creates a new claim identity and may record `derived_from_claim_id`.
- Any change to wording that affects scope, modality, time range, population, or causal strength invalidates reuse of prior verification until assessed.

**Gate:** regression tests show that revised claims cannot inherit stale `VERIFIED`
state and that genuinely distinct claims are not merged based only on similar text.

### P1 — Argument Dependency & Logical Audit

- Represent claim/premise nodes and `SUPPORTS`, `CHALLENGES`, and `DERIVES_FROM` edges.
- Inspect formal validity separately from evidence truth and attribution.
- Inspect inductive strength, causal inference, generalization, equivocation,
  non sequitur, evidence-scope mismatch, and omitted alternatives.
- Keep structural checks deterministic and semantic review explicit.
- Report each issue with its target, supporting rationale, basis references,
  counterexample/alternative when available, status, severity, and assessor.

**Gate:** fixed labelled cases include valid reasoning, known errors, ambiguous
reasoning, and insufficient-information cases; both missed issues and false
positive findings are measured.

### P1 — Evidence Conflict & Adjudication

- Separate evidence-item status, claim verification status, unresolved-conflict
  status, and final research judgment.
- Record source independence, scope, time, study design, and whether apparent
  conflict can be explained by different populations or conditions.
- Do not average or majority-vote conflicting sources without a defined rule.
- Route unresolved material conflict to review; do not silently label it as
  either claim truth or claim falsity.

**Gate:** mixed-support/mixed-challenge cases stay unresolved until a documented
adjudication rule or human review resolves them.

### P1 — Evaluator Boundary & Selective Reverification

- Record evaluator identity/version, rubric version, input revision digest,
  execution status, output status, rationale, and provenance.
- Distinguish `SUCCEEDED`, `FAILED`, `TIMEOUT`, `INVALID_OUTPUT`, and
  `INCOMPLETE`; evaluator failure cannot become a negative research finding.
- Keep evaluator signal separate from evidence and claim verification.
- Use dependency links to identify which claims need re-verification after a
  premise, evidence item, scope, or method changes.

**Gate:** tests verify evaluator failure handling, disagreement retention, stale
state invalidation, and selective re-verification scope.

### P2 — Provenance History

- Reuse the existing review-event/provenance/lineage primitives where contracts fit.
- Add claim revision and evidence/evaluator version references; preserve the old
  state when a new event is appended.
- Make event history replay/audit possible without treating the ledger itself as evidence.
- Do not implement a generalized Event Sourcing platform unless testable needs justify it.

**Gate:** a reviewer can reconstruct why a claim has its current status from
versioned inputs and events, and can identify missing provenance.

### P0, continuous — Benchmark & Preflight

- Keep a small, versioned synthetic seed set plus manually adjudicated research cases.
- Include positive/error cases, hard negatives (valid reasoning), ambiguity,
  evidence conflict, stale-revision, evaluator-failure, and missing-provenance cases.
- Record expected labels, adjudication status, rationale, and fixture version.
- Report precision/recall only when denominators and reference labels are defined.
  Do not claim probability calibration unless probabilities are evaluated against
  a suitable labelled set.
- Compare v2.3 baseline, v2.4 without semantic evaluator, and v2.4 with selective
  semantic evaluation. An unconditional-evaluator condition may be a cost/latency comparator.
- Measure false positives, missed issues, unnecessary abstention/review, state
  leakage, provenance completeness, latency, and tool/model cost.

**Gate:** every change to schemas, status rules, evaluator adapters, or conflict
resolution runs the same frozen regression set. Draft synthetic labels must be
independently reviewed before being treated as a gold standard.

## Core state separation

Never collapse these fields into one score:

- `evidence_status`
- `claim_verification_status`
- `logical_audit_status`
- `evaluator_signal`
- `evaluator_execution_status`
- `conflict_resolution_status`
- `research_judgment`
- `system_execution_status`

`VERIFIED` is a workflow status, not a calibrated probability that a proposition
is true. A logical-audit result does not substitute for source verification.
Human research judgment remains explicit.

## Non-goals

- No autonomous final truth decision.
- No promotion of model dialogue or evaluator output into evidence.
- No automatic claim identity resolution based only on semantic similarity.
- No unconditional use of an external evaluator.
- No expansion into end-to-end autonomous research in this iteration.

## v2.5 completion criteria

1. Versioned claim identity and stale-state invalidation are implemented and tested.
2. Argument edges and logical findings retain node/evidence references and reviewer rationale.
3. Mixed evidence conflict is not conflated with claim-level contradiction.
4. Evaluator disagreement/failure and revision impact are preserved as explicit state.
5. A frozen preflight set is runnable in CI and its labels have documented provenance.
6. Implementation claims are backed by CI results, not documentation alone.
