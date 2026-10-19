# SARA v2.5 Canonical Promotion Status

**Current decision: PROMOTION_BLOCKED.**

SARA v2.4 remains the canonical verification baseline. The v2.5 branch contains prototype code and regression tests, but canonical promotion is conditional on complete acceptance evidence, not merely code presence or a green CI run.

## Required evidence before promotion

1. CI succeeds on the exact candidate head and runs every required test suite.
2. The new callable dialogue-turn entrypoint is bound to the actual host SARA generation/verifier callables and live dialogue loop; input and claim-candidate revisions, model/rubric versioning, failure handling, and route invocation must be independently integration-tested in deployment. The current code is an injectable runtime boundary, not proof that production providers are configured.
3. The selective reverification runner is exercised against the injected verifier contract; successful results remain proposals until the explicit verification commit gate finds a matching proposal, current claim/evidence/verifier/contract digests, and a bound ACCEPT review event.
4. The provenance ledger passes append, tamper detection, export/import, and semantic replay tests. Durable storage, access control, authenticated reviewer identity, signatures, and deployment-level recovery must be established for the intended deployment.
5. Schema, code, tests, and documentation vocabulary are consistent, including the explicit verification commit gate.
6. The Preflight cases are independently adjudicated; at least two independent reviewers record each decision and rationale, and disagreements are resolved.
7. A frozen comparative evaluation of the v2.3 baseline, v2.4 without the JEV-style trigger, and v2.5 with the SARA-internal judgment/trigger path passes predeclared acceptance thresholds.
8. The promotion-gate code/test, all required CI jobs, schema/version consistency, and root README/version docs are reviewed and reverified. Root README and version docs are updated to v2.5 only after all gates above pass.

## Current evidence boundaries

- The fixture is marked DRAFT_NOT_INDEPENDENTLY_ADJUDICATED.
- The internal JEV-style judgment contract and inference-trigger orchestration are tested with deterministic test doubles. A new callable entrypoint (`sara_runtime.process_dialogue_turn`) and `SARA_v2.5/dialogue_runtime.py` connect judgment to claim verification when the judgment binds explicit candidate claim IDs; missing/ambiguous targets route to precheck. This proves the injected contract path only, not that a live dialogue host/model/verifier is configured. The generic evaluator adapter remains a separate prototype and is not evidence that JEV itself is externally integrated.
- Reverification results are proposals; the explicit commit gate rejects stale digests, version drift, missing reviews, non-ACCEPT decisions, and proposals not bound to the current revision. The gate does not authenticate reviewer identities by itself.
- The current provenance ledger is hash-chained and supports JSONL export/import and semantic replay; it is in-memory/caller-persisted, and durable storage, access control, authenticated reviewer identities, signatures, and deployment-level recovery remain outside the prototype.
- A green CI result proves only that the executed tests passed at that head. It is not evidence of research-verification accuracy or real-world improvement.

The machine-readable checklist is in promotion_evidence_template.json. Its runtime status must reflect that a callable prototype entrypoint exists but live host integration remains unverified. Missing or unverified entries must remain blockers.


The explicit status-commit gate is available as a prototype. It only commits after a matching ACCEPT review event and matching current proposal bindings; actual reviewer authentication/authorization is an external deployment responsibility.
