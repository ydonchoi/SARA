# SARA Independent Verification Matrix

**Status:** Initial documentation baseline; not an execution report  
**Scope:** Repository-level independent verification planning without GitHub Actions or runtime execution  
**Canonical comparison baseline:** SARA v2.4  
**Prototype under separate review:** SARA v2.5  
**Last updated:** 2026-10-24

## 1. Purpose and boundaries

This matrix distinguishes what can be assessed from source code and test definitions, what requires local tests, and what requires a real runtime/provider integration or independent human adjudication.

This document does **not** assert that any test passed. During this documentation change:
- GitHub Actions workflows were not run or added.
- The SARA runtime was not executed.
- Existing tests were inspected as repository assets only.
- No production-readiness or semantic-correctness claim is made.

Repository policy in `docs/engineering-principles.md` remains applicable: preserve v2.4 as the canonical baseline, keep v2.5 as a prototype unless separately promoted, and distinguish implementation, test execution, integration, and verification evidence.

## 2. Status vocabulary

Use these statuses for each verification item:

| Status | Meaning |
|---|---|
| `VERIFIED` | The stated acceptance criterion is supported by recorded, inspectable evidence for the exact code revision. |
| `PARTIALLY VERIFIED` | Some, but not all, stated checks have supporting evidence. |
| `NOT RUN` | A defined check exists but was not executed for the revision being reported. |
| `UNVERIFIED` | Evidence is insufficient to establish the claim, or the relevant capability was not exercised. |
| `BLOCKED` | A required dependency, input, permission, or independent review is unavailable. |
| `NOT APPLICABLE` | The criterion does not apply; record the reason. |

Do not mark an item `VERIFIED` merely because source code, a test file, schema, workflow, or example exists. Test status is revision-specific: evidence for an older commit does not establish the status of a later commit.

## 3. Verification matrix

The initial statuses below describe the evidence available from repository inspection for this documentation task. They are **not** claims that tests were executed.

| ID | Verification area | Evidence / relevant paths | Method and acceptance criterion | Initial status |
|---|---|---|---|---|
| V-01 | Canonical version boundary | `README.md`, `SARA_v2.4/README_v2.4.md`, `SARA_v2.5/CANONICAL_PROMOTION_STATUS.md` | Confirm v2.4 is the canonical comparison/rollback baseline and v2.5 is explicitly a user-led prototype trial, not production-ready. Record any contradictory version wording separately. | PARTIALLY VERIFIED — documented statements inspected; no full documentation reconciliation performed |
| V-02 | Python syntax / importability | Python files under `SARA_v2.3/`, `SARA_v2.4/`, `SARA_v2.5/`, and root `tests/` | On the local checkout, run syntax/compile checks without invoking the application runtime. Acceptance: no syntax errors in the declared scope; report exclusions and environment. | NOT RUN |
| V-03 | Schema and fixture parseability | `SARA_v2.4/schemas/`, `SARA_v2.5/schemas/`, `SARA_v2.5/benchmark/preflight_cases.json`, `docs/schemas/` | Parse JSON/YAML with declared tooling and validate fixtures against their intended schema where a validator exists. Parseability alone does not prove semantic validity. | NOT RUN |
| V-04 | v2.4 epistemic-state unit tests | `SARA_v2.4/tests/test_epistemic.py` | Run the targeted local test file. Acceptance: all assertions pass on the recorded commit and environment. | NOT RUN |
| V-05 | v2.4 logical-audit unit tests | `SARA_v2.4/tests/test_logical_audit.py`, `SARA_v2.4/logical_audit_contract.md` | Run targeted tests; separately review supported graph/symbolic boundaries and ensure structural findings are not represented as proof of semantic validity. | NOT RUN |
| V-06 | v2.4 runtime-boundary integration | `tests/test_sara_runtime_v24.py` | Run the local callable-path tests. This checks only the tested integration path, not a production host or external model provider. | NOT RUN |
| V-07 | v2.3 callable/execution contracts | `SARA_v2.3/07_SYSTEM/test_sara_callable.py`, `tests/test_external_execution.py`, `SARA_v2.3/07_SYSTEM/external_execution_contract_v01.md` | Run relevant local contract tests and inspect input validation, provider boundary, and fail-closed behavior. Do not infer live-provider correctness from stub tests. | NOT RUN |
| V-08 | Root-level evidence, review, and state modules | Relevant `tests/test_*.py` files at repository root, including citation/evidence, conflict, review-event, provenance, and verification-boundary tests | Select targeted test groups based on the touched module; record exact commands, test counts, and failures. | NOT RUN |
| V-09 | v2.5 claim identity and conflict components | `SARA_v2.5/tests/test_claim_identity.py`, `test_conflict_adjudication.py` | Run targeted tests locally; check claim/revision binding and ensure conflicting evidence is not silently collapsed. Synthetic/component tests are not independent benchmark evidence. | NOT RUN |
| V-10 | v2.5 evaluator and selective re-verification boundaries | `SARA_v2.5/tests/test_evaluator_boundary.py`, `test_evaluator_runner.py`, `test_selective_reverification.py`, `test_reverification_runner.py` | Run targeted tests; verify evaluator output remains a decision-support signal and cannot independently become evidence or promote epistemic status. | NOT RUN |
| V-11 | v2.5 provenance and human-review gates | `SARA_v2.5/tests/test_provenance_ledger.py`, `test_verification_commit_gate.py`, `test_promotion_gate.py` | Run targeted tests; inspect tamper/replay, stale revision, authorization, and explicit review/commit boundary coverage. Production durability and authenticated identity require separate operational evidence. | NOT RUN |
| V-12 | v2.5 dialogue route and failure paths | `SARA_v2.5/tests/test_dialogue_runtime.py`, `SARA_v2.5/dialogue_runtime.py` | Run component tests locally for normal, ambiguous, unbound-claim, malformed-output, and provider-failure paths. Passing isolated tests do not prove host-loop integration. | NOT RUN |
| V-13 | Preflight fixture structure and coverage | `SARA_v2.5/benchmark/preflight_cases.json`, `SARA_v2.5/tests/test_preflight_fixture.py` | Validate JSON and declared suite coverage. Keep fixture validation separate from adjudication and model-performance claims. | NOT RUN |
| V-14 | Independent benchmark adjudication | `SARA_v2.5/benchmark/ADJUDICATION_PROTOCOL.md`, `REVIEWER_PACKET.md`, `docs/v2.5-evaluation-protocol-v0.1.md` | Obtain two independent labels per case, preserve rationales/provenance, adjudicate disagreements, and freeze protocol/data before scoring. Model-generated labels do not count as independent human labels. | BLOCKED — repository docs identify the current fixture labels as draft / not independently adjudicated |
| V-15 | Comparative evaluation | `docs/v2.5-evaluation-protocol-v0.1.md`, `docs/v2.5-promotion-readiness-plan.md` | Compare v2.3, v2.4 without trigger routing, and v2.5 on the same frozen, independently adjudicated cases using predeclared metrics and thresholds. | NOT RUN |
| V-16 | Live host/model/verifier integration | `SARA_v2.5/CANONICAL_PROMOTION_STATUS.md`, `SARA_v2.5/README_v2.5.md` | In a controlled local environment, exercise the actual host dialogue loop with configured model and verifier providers; capture successful and failure-path evidence. | UNVERIFIED — code presence or injected fixtures are not live integration evidence |
| V-17 | Security and secret handling | Repository source, configuration examples, workflow definitions, and `docs/engineering-principles.md` | Inspect secret exposure, untrusted input handling, least privilege, unsafe deserialization, logging, provenance tampering, and dependency risks. Record findings and scope; static review cannot prove absence of vulnerabilities. | NOT RUN |
| V-18 | Reproducibility of local checks | Local environment metadata and recorded commands | Record OS, Python version, dependency lock/source, command, commit SHA, exit status, and artifact/log location. A result without revision/environment identity is incomplete. | NOT RUN |
| V-19 | License boundary | `LICENSE`, `README.md` | Preserve attribution and license notice. The repository states CC BY-NC 4.0 for original materials; commercial use requires separate permission. Third-party components may have different licenses. | PARTIALLY VERIFIED — repository notice inspected; no third-party license audit performed |

## 4. Local-only verification procedure

This procedure is intentionally manual. It does not add a workflow or require GitHub Actions.

1. **Freeze the target revision.** Record `git rev-parse HEAD`, branch, and whether the working tree is clean.
2. **Record the environment.** Record OS, `python --version`, dependency installation method, and relevant package versions. Do not include secrets.
3. **Choose a bounded scope.** Start with the files/modules changed and their direct callers, schemas, contracts, and existing tests. Expand scope when dependencies or failures require it.
4. **Inspect before executing.** Review contracts and tests to determine what each test actually asserts and what it does not cover.
5. **Run only the selected local checks.** Use the existing project environment. Examples for an appropriately configured checkout:
   - Syntax-only compilation: `python -m compileall -q SARA_v2.3 SARA_v2.4 SARA_v2.5 tests`
   - v2.4 focused tests: `python -m pytest SARA_v2.4/tests/test_epistemic.py SARA_v2.4/tests/test_logical_audit.py -q`
   - v2.4 callable-path tests: `python -m pytest tests/test_sara_runtime_v24.py -q`
   - v2.5 dialogue component tests: `python -m pytest SARA_v2.5/tests/test_dialogue_runtime.py -q`
   These are suggested commands, not commands executed as part of this documentation change. Dependency requirements and current test compatibility must be confirmed in the local checkout.
6. **Record failures faithfully.** Preserve the exact command, exit code, concise output, and relevant artifact. Do not weaken assertions or relabel failures as warnings without a justified change.
7. **Separate evidence classes.** Label each result as source inspection, static check, unit/contract test, component test, live integration, independent adjudication, or production/operational evidence.
8. **Review the changed revision.** Confirm the final commit SHA and ensure the evidence refers to that SHA. Any material code change invalidates claims that depend on the previous revision until rechecked.

## 5. Per-run evidence record

Create one record for each verification session. Do not fill fields from assumptions.

```yaml
record_id: "<unique-id>"
repository: "https://github.com/ydonchoi/SARA"
commit_sha: "<exact-commit-sha>"
branch: "<branch>"
scope:
  - "<path or module>"
environment:
  os: "<os/version>"
  python: "<version or not-applicable>"
  dependency_source: "<lockfile / requirements / environment description>"
checks:
  - id: "V-04"
    method: "local-test"
    command: "<exact command>"
    status: "NOT RUN"
    exit_code: null
    evidence_uri: null
    notes: "<what the check does and does not establish>"
runtime_executed: false
github_actions_executed: false
independent_adjudication: "NOT RUN"
limitations:
  - "<known evidence gap>"
reviewed_by: "<reviewer or not-recorded>"
recorded_at: "<ISO-8601 timestamp with timezone>"
```

For a check that was not executed, leave `exit_code` and `evidence_uri` null and retain `NOT RUN`. Do not use an empty or successful-looking log as evidence of a pass.

## 6. Acceptance rules

A verification session is complete only when:
- its scope and target commit are explicit;
- each in-scope criterion has a status and supporting evidence or a documented reason it remains unverified;
- test execution is distinguished from source inspection;
- synthetic fixture coverage is distinguished from independent adjudication;
- local component tests are distinguished from live host/provider integration;
- no conclusion exceeds the capability of the evidence;
- unresolved failures and risks are recorded rather than hidden.

This matrix is a verification plan and evidence index. It is not, by itself, proof that SARA is correct, safe, production-ready, or semantically reliable.

## 7. Related repository artifacts

- [Engineering principles](engineering-principles.md)
- [v2.5 evaluation protocol draft](v2.5-evaluation-protocol-v0.1.md)
- [v2.5 promotion readiness plan](v2.5-promotion-readiness-plan.md)
- [SARA v2.4 README](../SARA_v2.4/README_v2.4.md)
- [SARA v2.5 promotion status](../SARA_v2.5/CANONICAL_PROMOTION_STATUS.md)
