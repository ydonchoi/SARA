# SARA v2.5 Executor CLI — Prototype

## Purpose

`executor.py` supplies an executable, host-neutral JSONL entrypoint around
`SARADialogueRuntime`. It accepts one dialogue-turn request per line, invokes
the inference judgment/activation pipeline, and emits one structured result per
input line.

This is an execution adapter, **not a deployed ChatGPT integration**. It does
not ship a model SDK, credentials, verifier backend, durable event store, or
production service. A real provider module must be configured explicitly.

## Provider contract

Pass a Python import path with `--provider package.module`. The module must
export:

- `MODEL_ID: str`
- `MODEL_REVISION: str`
- `generate(system_prompt, payload, timeout_seconds) -> Mapping`
- `verify_claim(request) -> Mapping`

Optional callables:

- `precheck(request, judgment, decision) -> Mapping`
- `event_sink(event) -> Any`

The `generate` function must return the structured judgment fields required by
`internal_judgment_model.py`. The verifier must return a mapping that obeys the
existing SARA verification contract; a returned mapping is not automatically a
successful verification. Missing required provider functions block startup.

## Input

Each JSONL line is an object containing at least:

```json
{
  "request_id": "req-001",
  "conversation_id": "conv-001",
  "turn_id": "turn-001",
  "content": "The observed outcome improved after the intervention, so the intervention caused the improvement.",
  "claim_candidates": [
    {"id": "claim-001", "text": "The intervention caused the improvement."}
  ],
  "evidence": []
}
```

The sample illustrates shape only; it is not an evaluation case or proof of
correct inference detection. The judgment model validates that references and
basis spans are bound to the input. Use a precheck/review path when candidate
binding or judgment is ambiguous.

## Run

```sh
python SARA_v2.5/executor.py --provider your_package.sara_provider
```

Send one JSON object per line to standard input. The executor emits one JSON
result per nonblank input line. Configuration errors are written to standard
error and exit with code 2. Malformed JSON and per-request errors produce
explicit failure objects rather than being reported as successful execution.

## Result status semantics

The top-level `status` describes execution state, not claim truth:

- `NO_ROUTE_REQUIRED`: judgment pipeline completed and selected no route;
  verification was not run.
- `ROUTE_COMPLETED`: the route callback returned and did not report a known
  failure/review state. Inspect `verification_status` and the full route output
  before interpreting the result.
- `COMPLETED_UNVERIFIED`: callback returned, but output indicates a proposal,
  review queue, or an explicitly unverified/pending result.
- `PARTIAL_OR_FAILED`: route output reported partial/failure/invalid state.
- `FAILED`: request processing or route execution failed.
- `BLOCKED`: provider configuration failed before processing input.

The result also carries `execution_completed`, `route_callback_completed`,
`verification_status`, and `claim_truth_assessed: false`. A callback
completion is not a truth verdict; even a provider's `VERIFIED` label is a
provider-reported status, not independent evidence that the claim is true.

## Security and status boundaries

- Do not put API keys or secrets in the repository or input payloads.
- Configure providers through the deployment's secret/configuration mechanism.
- A judgment signal is not evidence and does not establish claim truth.
- The default precheck reports `NEEDS_REVIEW`; it is not a durable queue.
- Event recording is only reported as recorded when a configured event sink
  returns successfully; this alone does not prove durable persistence.
- This CLI processes explicitly supplied turns. It does not intercept the
  current ChatGPT app's internal conversation stream.
- The executor requires integration tests with a real configured model and
  verifier before any production-use claim or v2.5 promotion.

## Current validation scope

Unit tests cover provider-contract enforcement, fail-closed request handling,
and separation of route completion from verification outcome. They do not
establish that a production model/provider is configured, that external
verification runs, or that the current ChatGPT app invokes this code.
