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

## Promotion Firewall

The following are prohibited without independent source evidence:
- MODEL_INFERENCE → SOURCE_CLAIM
- MODERN_INTERPRETATION → AUTHOR_EXPLICIT
- AGREEMENT → VERIFIED
- CHECKPOINT → EVIDENCE
- EXECUTION_SUCCESS → RESEARCH_VALIDITY

## Temporal Boundary

Historical knowledge and post-publication/current knowledge are separate contexts. Later evidence cannot be silently inserted into Historical Author Mode.

## Revision Loop

SARA verification results return to Co-thoughts as epistemic input for revision. They remain verification results, not new evidence.

## Compatibility

This contract extends SARA v2.3 while preserving:
- system/research verification separation
- provider execution boundary
- fail-closed behavior
- simulation/reproduction separation
- provenance retention
