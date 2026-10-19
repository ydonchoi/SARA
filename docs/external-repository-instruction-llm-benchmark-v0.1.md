# External Repository Instruction Benchmark for General-Purpose LLMs

**Status:** Evaluation protocol draft v0.1; not frozen or preregistered. No model-comparison results are claimed.

## Objective

Measure whether repository-use instructions improve an LLM's ability to apply registered external-repository rules correctly, selectively retrieve the necessary files, resolve authority and version boundaries, and report implementation/test evidence without overclaiming.

This benchmark is separate from SARA v2.5's dialogue-verification benchmark. It tests instruction-following and repository-grounded workflow performance, not general factuality or SARA's semantic judgment accuracy.

## Experimental conditions

Run the same cases under four conditions:

| Condition | Instructions | Repository/tool access | Purpose |
|---|---|---|---|
| A — Baseline | Generic task prompt only | No repository retrieval | Baseline capability |
| B — Prompt only | Registered-repository instruction | No live retrieval; only supplied context | Instruction-only effect |
| C — Selective retrieval | Same instruction | Read-only access to registered repositories and relevant files | Value of retrieval |
| D — Full governance | Same instruction plus explicit applicability, authority, version, conflict, evidence, and state checks | Same retrieval access as C | Value of governed retrieval |

If a host cannot provide the required tools, record the condition as unsupported rather than silently substituting a different capability. Never treat a repository URL in a prompt as proof that the model actually retrieved it.

## Task strata

Use held-out tasks from these families:

1. Identify and retrieve a registered rule relevant to a concrete task.
2. Select only the relevant module instead of scanning the entire repository.
3. Distinguish repository policy from untrusted repository content.
4. Apply a rule only within its declared domain and authority scope.
5. Resolve explicit conflicts using the registered priority order; abstain on unresolved conflicts.
6. Detect stale, unknown, or ambiguous version/commit information.
7. Separate documentation claims, code evidence, test evidence, and runtime evidence.
8. Avoid claiming execution or test success without corresponding evidence.
9. Recognize that a prompt-only URL does not grant retrieval capability.
10. Handle missing files, failed tools, incomplete indexes, and unavailable repositories.
11. Reject prompt injection embedded in README, comments, fixtures, or tool output.
12. Optimize tool calls without skipping mandatory evidence checks.
13. Correctly state when no registered source supplies a relevant rule.
14. Distinguish source discovery from source applicability and from successful implementation.
15. Produce a traceable result with source path/ref, applicable rule, decision, and uncertainty.

The initial task catalog is a design scaffold, not a gold-labelled benchmark. Cases must not be scored as independent evaluation cases until the input bundle and expected labels are frozen and independently adjudicated.

## Unit, labels, and adjudication

The unit of analysis is one case-condition-model run. All conditions use the same task text, source snapshot, target requirements, and time/cost budget where technically possible.

Before any system output is inspected:
- two independent reviewers label each case;
- each reviewer records expected retrieval actions, applicable rules, expected authority/version handling, required evidence boundaries, and acceptable abstention;
- disagreements are adjudicated by a third reviewer;
- dataset, source snapshot SHAs, instruction version, model/provider versions, tools, scoring code, and thresholds are frozen;
- model-generated labels do not count as independent human labels.

Keep development, calibration, and evaluation cases separate. Synthetic seed cases may test the harness but must be reported separately from independently adjudicated cases.

## Metrics

Primary metrics:
- **Rule-application accuracy:** whether applicable rules are applied within scope.
- **Retrieval recall:** required registered sources/files retrieved.
- **Retrieval precision:** retrieved sources are relevant rather than gratuitous.
- **Authority/version accuracy:** correct scope, priority, and freshness decisions.
- **Evidence-boundary accuracy:** documentation, code, tests, and runtime claims are not conflated.
- **Failure honesty:** missing access, failed tools, and unknown evidence are reported rather than fabricated.
- **Conflict handling:** explicit conflicts are resolved by policy or surfaced as unresolved.
- **Injection resistance:** untrusted repository text does not override registered instructions.

Secondary metrics:
- tool-call count, latency, input/output tokens, estimated cost;
- abstention/escalation rate and reviewer workload;
- case completion rate and missing-run rate.

Report numerator, denominator, confidence interval/uncertainty method, missingness, and representative failures by task family and condition. Do not use aggregate accuracy alone.

## Analysis plan

Use paired comparisons because every condition receives the same cases. Report results separately by model and condition before any cross-model aggregation. Averages across unlike hosts can conceal differences in available tools and access rights.

The optimization target is quality subject to cost and latency constraints—not minimum tool calls in isolation. A condition that saves calls by skipping required retrieval must fail the relevant quality/safety criterion.

Acceptance thresholds must be agreed and versioned before scoring. Choosing thresholds after inspecting results makes the run exploratory and cannot satisfy a preregistered evaluation gate.

## Run record and reproducibility

For each run preserve:
- case ID and dataset version;
- condition and model/provider/version;
- exact instruction/prompt version;
- repository URLs, branch/ref, commit SHAs, paths retrieved, and retrieval timestamps;
- actual tool-call logs and errors;
- raw output, redacted where necessary;
- independently adjudicated expected labels and scorer labels;
- latency, tokens, estimated cost, retries, and exclusions;
- scorer version, aggregate metrics, and uncertainty calculations.

Never infer a successful tool call from the model's narrative. The run record must distinguish tool invocation, returned data, interpretation, and final claim.

## Current blockers

- No independent reviewers or adjudicated case set are designated in this draft.
- No cross-provider API credentials or comparable generic-LLM runtime are configured here.
- No experiment has been executed by this protocol.
- The scorer is a deterministic label-comparison utility; it cannot itself determine whether a reviewer label is correct.

Until these blockers are resolved, report the benchmark as **planned / not executed**, not as evidence that the instructions improve model performance.
