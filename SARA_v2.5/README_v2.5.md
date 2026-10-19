# SARA v2.5 — Claim Identity, Argument Audit & Reverification

## Status

**PROTOTYPE / NOT A RELEASED RUNTIME BASELINE.** SARA v2.4 remains the
canonical verification baseline. v2.5 now has callable evaluator and selective
re-verification adapters, a hash-chained provenance ledger with JSONL
export/import and replay, and a deterministic promotion gate. The adapters are
tested with injected providers; no live external evaluator provider is configured.
Durable deployment storage/access control, independently adjudicated benchmarks,
and evidence for comparative research-quality improvement remain incomplete.

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

Prototype `conflict_adjudication.py` separates:
- fully verified opposing evidence in matching scope/time (`UNRESOLVED_CONFLICT`);
- partially verified opposing signals (`POTENTIAL_CONFLICT_REVIEW`);
- opposing evidence from different scope/time (`CONTEXTUAL_DIVERGENCE_REVIEW`).

Evidence that is unverified, contradicted at the item level, or neutral is not
silently discarded: its ID remains in `non_eligible_evidence_ids`. Source
independence is surfaced but remains `NOT_ADJUDICATED`.

**Gate:** mixed-support/mixed-challenge cases stay unresolved until a documented
adjudication rule or human review resolves them. No conflict state automatically
promotes or downgrades the claim's verification or truthfulness status.

### P1 — Evaluator Boundary & Selective Reverification

- Record evaluator identity/version, rubric version, input revision digest,
  execution status, output status, rationale, and provenance.
- Distinguish `SUCCEEDED`, `FAILED`, `TIMEOUT`, `INVALID_OUTPUT`, and
  `INCOMPLETE`; evaluator failure cannot become a negative research finding.
- Keep evaluator signal separate from evidence and claim verification.
- Use dependency links to identify which claims need re-verification after a
  premise, evidence item, scope, or method changes.

`evaluator_boundary.py` validates the output envelope; `evaluator_runner.py`
invokes a provider supplied by the caller. The runner passes an explicit timeout
to the provider, binds output to the exact input digest and claim revision, and
normalizes timeout, exception, missing fields, identity mismatch, and invalid
signals into distinct execution outcomes. Python cannot forcibly cancel an
arbitrary synchronous callable; the injected transport must enforce the timeout.
A successful call emits a decision-support signal, not research evidence or a
claim-verification status, and remains `NOT_COMMITTED`. `NO_ISSUE_REPORTED`
does not assert logical validity.

The callable interface is tested with stub providers. A live provider integration,
credentials/transport setup, and independently measured evaluator reliability
remain unverified.

**Gate:** runtime integration evidence must verify the actual provider, timeout
behavior, rubric/version binding, provenance, malformed output handling, and
disagreement retention on the deployment transport.

### Selective Reverification Planning — Prototype

`selective_reverification.py` computes transitive impact from explicit
upstream-to-dependent edges. `reverification_runner.py` then executes only the
claims in that plan through an injected verification provider. It recomputes the
claim and evidence digests, checks verifier and contract revisions, validates
result provenance, and distinguishes failed, timed-out, incomplete, and invalid
outputs. Successful statuses are returned as proposals requiring review; the
runner leaves current claim status unchanged and records no truthfulness upgrade.

**Gate:** tests cover direct/transitive impact, unaffected claims, missing prior
state, unknown references, duplicate edges, cyclic dependencies, successful
proposal handling, provider failure, stale digests, binding mismatch, provenance
separation, and non-promotion. The transport still needs deployment-level
verification; the runner does not autonomously commit claim statuses.


### Explicit Verification Commit Gate — Prototype

`verification_commit_gate.py` is the only v2.5 path that appends a
`CLAIM_STATUS_COMMITTED` event. It recomputes the current claim and evidence
digests and requires a proposal for the exact current revision, matching
verifier/contract versions, and a linked `ACCEPT` review event with rationale.
The ledger independently checks the proposal/review binding and keeps the commit
in the hash chain. Stale revisions, changed evidence, version drift, rejected
reviews, missing reviews, and mismatched proposal IDs fail closed.

This gate checks the declared reviewer ID and can compare it to an expected ID,
but **does not authenticate that identity**. Authentication/authorization must
be enforced by the caller's trusted identity boundary. The gate commits a
workflow verification status only; it does not set claim truthfulness. There is
no automatic commit after evaluator or verifier success.

**Gate:** tests prove that accepted reviews can commit only the corresponding
current proposal, stale or mismatched proposals cannot commit, and the committed
state stays distinct from truthfulness. Deployment-level review authentication
and durable persistence are still required.

### P2 — Provenance History

`provenance_ledger.py` provides a small append-only hash chain, unique event IDs,
monotonic sequence numbers, tamper detection, canonical JSONL export/import, and
claim replay. The evaluator and re-verification runners can append operational
events. Replay changes the committed verification state only for an explicit
`CLAIM_STATUS_COMMITTED` event; proposed results and evaluator signals remain
separate. Every event states that it is not research evidence.

The ledger is presently in-memory with caller-managed JSONL export/import. A
durable storage backend, access control, signatures, deployment backup/recovery,
and concurrency guarantees are not claimed.

**Gate:** a reviewer can reconstruct why a claim has its current committed
status from versioned inputs/events, tampering and semantically invalid imported
histories are rejected, and missing provenance is visible.

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

The current 18-case draft fixture includes executable checks for implemented
claim-identity, evidence-conflict, evaluator-boundary, callable evaluator,
selective-planning, re-verification execution, and structural-cycle prototypes.
Other semantic logical-audit cases remain target cases, not evidence that a
natural-language fallacy detector exists. All labels remain DRAFT.

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
6. The verification commit gate binds status changes to a current proposal and explicit review.
7. A live evaluator integration and required deployment controls are verified.
8. Implementation claims are backed by CI results for the exact candidate head, not documentation alone.

## Canonical Promotion Gate

`promotion_gate.py` evaluates explicit evidence for the exact candidate head:
current-head CI and required jobs, runtime integration, schema/documentation
consistency, independent per-case adjudications, disagreement resolution,
predeclared benchmark metric decisions, and absence of open blockers. The gate
only reports `PROMOTION_APPROVED` or `PROMOTION_BLOCKED`; it never changes the
canonical version itself. It now also requires the human-review commit gate test
suite and a verified readiness status for that transition.

Current promotion evidence is maintained in `promotion_evidence_template.json`
and the decision in `CANONICAL_PROMOTION_STATUS.md`. As long as the benchmark is
DRAFT, a real provider is unconfigured, or other required evidence is missing,
v2.4 remains canonical.
