# Engineering Principles: Correctness-First, Scope-Controlled Changes

**Status:** Active repository-level engineering policy  
**Applies to:** New implementation work, bug fixes, refactors, tests, documentation changes that define implementation behavior, and runtime/integration work across SARA versions  
**Supersedes:** Any prior instruction or working habit that treats “lazy coding,” minimal code changes, smallest-diff-first, or avoiding refactoring as the highest-priority engineering rule.

## 1. Governing Principle

SARA engineering follows **correctness first, scope controlled, evidence based**.

The primary objective is to satisfy the requirements correctly and safely while preserving explicit contracts and verified behavior. The number of changed lines, files, modules, or commits is not an independent measure of quality.

When a minimal patch would leave the root cause unresolved, preserve a broken contract, increase inconsistency, or create material security, data-integrity, or regression risk, make the broader change necessary to resolve the problem.

## 2. Required Decision Rules

1. **Correctness and safety first.** Prioritize requirements, correctness, security, data integrity, module contracts, and maintainability over patch size.
2. **Resolve root causes.** Investigate the failure mechanism and relevant dependencies. Do not merely suppress symptoms, weaken assertions, bypass checks, or add special cases to make a failure disappear.
3. **Respect architecture and contracts.** Inspect affected callers, dependencies, schemas, state transitions, error paths, and integration boundaries. Make structural changes when a local patch would leave the system inconsistent or incorrect.
4. **Control scope without minimizing it blindly.** Avoid unrelated rewrites and speculative expansion. Do not reject a necessary refactor solely because it touches more files or requires more work.
5. **Protect verified behavior.** Preserve the canonical v2.4 verification baseline unless a separately authorized change explicitly changes it. For v2.5 work, do not imply prototype changes promote or replace the canonical baseline.
6. **Test proportionately.** Select unit, contract, regression, integration, and failure-path checks based on the changed behavior and risk. State which checks were actually executed and their results.
7. **Report evidence honestly.** Separate implementation, test execution, integration verification, and performance evaluation. Never claim tests passed when they were not run; never treat synthetic tests or successful callback completion as proof of semantic correctness or truth.
8. **Make trade-offs explicit.** For broad changes, record the root cause, affected interfaces, dependencies, expected benefit, regression risks, alternatives considered, and verification plan.
9. **Optimize against evidence.** Do not optimize for fewer edits, fewer files, or speed alone. Establish a measurable bottleneck or concrete maintenance risk before optimization, and evaluate the result against that target.
10. **Use minimal loading appropriately.** Load only the source files and modules required to understand and execute the task, expanding the investigation when dependencies, root causes, or risk require it. **Minimal Loading is a resource-management principle, not a mandate to make minimal code changes.**

## 3. Required Workflow

For non-trivial changes:

1. Identify the requirement, observable failure, or intended behavior.
2. Inspect the relevant architecture, repository instructions, dependencies, contracts, and existing tests.
3. Form a root-cause hypothesis and identify what evidence would confirm or falsify it.
4. Choose the smallest **sufficient and correct** solution—not automatically the smallest diff.
5. Implement the necessary code, tests, and documentation together where applicable.
6. Run the checks available in the environment; record exact commands or CI evidence and outcomes.
7. Review regressions, failure handling, interface compatibility, security, and unverified assumptions.
8. Report completion status, evidence, remaining risks, and blockers separately.

For trivial, low-risk changes, this workflow may be proportionate and concise; it must not be used to bypass necessary verification.

## 4. Completion and Status Labels

A change is not complete merely because a patch is small, a file was committed, or code appears plausible. Reports must distinguish:

- **Implemented:** The change exists in the stated branch/commit.
- **Tested:** The stated tests were actually executed; include results.
- **Integrated:** The relevant runtime or host path was exercised.
- **Verified:** The declared acceptance criteria have supporting evidence.
- **Unverified / Blocked:** Required evidence or execution was unavailable.

List material unverified items and residual limitations. Do not convert absence of evidence into a claim of success or failure.

## 5. Relationship to Existing SARA Principles

This policy does **not** abolish scope discipline, Minimal Loading, modularity, dependency control, versioned snapshots, or regression protection. It rejects only the unconditional priority given to minimal code modification or “lazy coding.”

Historical/versioned documents may retain the wording that accurately records their original design state. For current work, this policy governs where older wording or informal habits conflict with correctness-first engineering. When a specific version’s documented contract is intentionally being changed, update the relevant versioned artifact and tests explicitly rather than silently rewriting historical snapshots.

## 6. Change Review Checklist

- [ ] Requirement and acceptance criteria are explicit.
- [ ] Root cause and affected dependencies have been investigated.
- [ ] The chosen scope is sufficient; no necessary fix was excluded merely to minimize the diff.
- [ ] Contracts, schemas, security, error paths, and compatibility were reviewed.
- [ ] Relevant tests were executed, or execution blockers are explicitly reported.
- [ ] Regression and integration evidence are distinguished from unit/synthetic tests.
- [ ] Documentation and version/baseline status are consistent.
- [ ] Unverified assumptions, trade-offs, and remaining risks are reported.
