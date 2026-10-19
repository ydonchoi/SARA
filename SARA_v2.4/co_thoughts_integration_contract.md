# Co-thoughts v2.0 ↔ SARA v2.4 Integration Contract

## Boundary

Co-thoughts generates and structures cognitive objects. SARA evaluates their epistemic status. Neither layer inherits the other's authority.

## Knowledge Gate

External source/context enters Co-thoughts through a SARA validation boundary.

Input:
- source
- claims
- premises
- evidence
- temporal context
- interpretive context

Output:
- verification status
- evidence alignment
- uncertainty
- provenance event

## Thought Gate

Co-thoughts may emit:
- new claim
- premise
- inference
- source-grounded interpretation
- modern interpretation
- simulation

SARA evaluates these without treating generation itself as evidence.

## Logical Audit

SARA v2.4 may validate argument-graph references and flag directed support/dependency cycles as candidate findings. A cycle is not, by itself, proof of a semantic fallacy. Semantic issues such as invalid inference, causal overreach, equivocation, overgeneralization, and omitted alternatives require an explicit evaluator or human review.

Each finding records its target, category, status, rationale, related nodes, optional evidence references, severity, and assessor. A substantiated finding requires a rationale and at least one basis reference. Logical-audit output is a decision-support signal, never research evidence or an automatic truth judgment.

For explicitly structured symbols, the checker recognizes modus ponens/modus tollens as valid forms and affirming the consequent/denying the antecedent as invalid forms. It does not parse free-form prose. Broader semantic review remains separate and `semantic_audit_status = NOT_PERFORMED` until such a review runs; absence of structural findings must not be reported as no logical errors found.

## Promotion Firewall

The following are prohibited without independent source evidence:
- MODEL_INFERENCE → SOURCE_CLAIM
- MODERN_INTERPRETATION → AUTHOR_EXPLICIT
- AGREEMENT → VERIFIED
- CHECKPOINT → EVIDENCE
- EXECUTION_SUCCESS → RESEARCH_VALIDITY

## Temporal Boundary

Historical knowledge and post-publication/current knowledge are separate contexts. Later evidence cannot be silently inserted into Historical Author Mode. Temporal context and attribution status are independent fields: AUTHOR_EXPLICIT requires explicit source-attribution evidence, not a particular temporal label.

## Revision Loop

SARA verification results return to Co-thoughts as epistemic input for revision. They remain verification results, not new evidence.

## Compatibility

This contract extends SARA v2.3 while preserving:
- system/research verification separation
- provider execution boundary
- fail-closed behavior
- simulation/reproduction separation
- provenance retention
