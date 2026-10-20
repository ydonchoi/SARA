# SARA v2.4 — Logical Audit Contract

## Status

**Additive v2.4 improvement.** The graph checker validates references and flags support/dependency cycles; the module also checks four explicitly supplied symbolic conditional forms. It does not parse free-form prose or establish premise/conclusion truth. Broader semantic review still requires an explicit evaluator or human reviewer.

## Purpose

Inspect the links between claims and premises without confusing:
- structural graph integrity with inferential validity;
- a suspected issue with a substantiated finding;
- a logical-audit signal with evidence or a verification result.

## Graph contract

Nodes:
- `CLAIM`
- `PREMISE`

Directed edges:
- `SUPPORTS`
- `CHALLENGES`
- `DERIVES_FROM`

The checker rejects malformed identifiers, duplicate IDs, unknown edge targets,
unknown node types, unknown relations, and unknown inference-type values.
Cycles in directed support/dependency edges are returned as
`CIRCULAR_REASONING / CANDIDATE`. This is a structural warning, not proof that
the propositions form a circular argument. Challenge edges are excluded from
cycle detection because challenge relations do not, by themselves, assert a
dependency chain.

## Explicit symbolic conditional-form check

When the caller supplies antecedent/consequent atoms, a second literal premise, conclusion polarity, and node IDs as structured inputs, the module recognizes:

- Modus ponens: P → Q; P; therefore Q — valid form.
- Modus tollens: P → Q; not Q; therefore not P — valid form.
- Affirming the consequent: P → Q; Q; therefore P — invalid deductive form.
- Denying the antecedent: P → Q; not P; therefore not Q — invalid deductive form.

These checks operate only on supplied symbolic structure; they do not extract it from prose. Unrecognized forms remain UNASSESSED. A valid form does not verify its premises; an invalid form does not prove its conclusion false. Outputs carry `is_evidence: false`.

## Semantic finding contract

Each finding contains:
- `finding_id`, `target_id`, and `related_node_ids`;
- `category`: formal validity, inference strength, causal inference,
  generalization, concept equivocation, circular reasoning, non sequitur,
  evidence-scope mismatch, alternative explanation, or other;
- `status`: `CANDIDATE`, `SUBSTANTIATED`, `REJECTED`, or `UNASSESSED`;
- `severity`: `CRITICAL`, `MATERIAL`, `MINOR`, or `UNASSESSED`;
- rationale, optional counterexample/alternative, evidence references, and assessor.

A `SUBSTANTIATED` finding requires a non-empty rationale and at least one
reference to a related node or known evidence item. All referenced node and
evidence IDs must resolve. Output explicitly carries `is_evidence: false`.

## Required boundaries

1. A graph with no structural cycle is **not** labelled logically valid.
2. A candidate issue is not automatically upgraded to `SUBSTANTIATED`.
3. An evaluator response is a decision-support signal, not evidence.
4. Logical issue status does not overwrite claim verification status.
5. A verified source or true premise does not, by itself, establish a valid inference.
6. A valid deductive form does not establish that its premises are true.
7. For inductive, causal, and abductive arguments, inspect scope, uncertainty,
   alternative explanations, and study design; do not treat deduction-only rules as sufficient.
8. When context is insufficient, return `UNASSESSED` or `REQUIRES_REVIEW`.

## Integration

The Co-thoughts adapter reports `logical_audit_status: NOT_RUN` until a semantic
review actually runs. The symbolic form checker is a separate explicit call, not an automatic prose parser. It also surfaces a review signal if a claim marked
`VERIFIED` contains a premise marked `CONTRADICTED`; neither status is silently
rewritten. The signal is for review, not an automatic claim-level verdict.

## Validation coverage

The added unit tests cover valid acyclic structure, support-cycle candidates,
unknown references, duplicate nodes, incomplete substantiated findings, and
epistemic separation. They must be run by CI before this change is considered
verified. The GitHub editing connector itself does not execute Python tests.
