# SARA v3.0.0 integration candidate

**Status:** Implemented candidate, not canonical. v2.4 remains the canonical baseline. The v3 local contract and stub tests do not establish live-provider quality, Co-thoughts host integration, production security, durable storage, or promotion readiness.

## Runtime

Run one dialogue turn from stdin or a UTF-8 JSON file:

```powershell
Get-Content .\turn.json -Raw | python -m SARA_v3.cli
python -m SARA_v3.cli --request .\turn.json --timeout-seconds 20
```

The request follows the v2.5 dialogue contract: `request_id`, `conversation_id`, `turn_id`, `content`, and explicit `claim_candidates`. Do not put credentials in the request. The output is `sara.dialogue-result.v3`; its `assessment_envelopes` are also supplied to the response LLM. The response must reference every assessed `claim_id`; missing references fail response validation. The SARA status remains a separate field and cannot be changed by the response model.

## Providers

| Purpose | Configuration | Behavior |
|---|---|---|
| JEV judgment LLM | `SARA_LLM_PROVIDER`, `SARA_LLM_MODEL`, `SARA_LLM_API_KEY`; optional `SARA_LLM_BASE_URL`, `SARA_LLM_MODEL_REVISION` | Supports OpenAI, Anthropic, Gemini, Kimi, and OpenAI-compatible APIs through the v2.5 adapter. Kimi defaults to Moonshot's OpenAI-compatible endpoint and JSON object mode; SARA validates returned JSON against the requested schema. |
| Evidence relation LLM | Optional `SARA_RELATION_LLM_PROVIDER`, `SARA_RELATION_LLM_MODEL`, `SARA_RELATION_LLM_API_KEY` and `SARA_RELATION_LLM_` fields | Defaults to the judgment model. Configure a separate model when independent assessment is useful; model agreement still does not replace the source-span and SARA status rules. |
| Default web search | `BRAVE_SEARCH_API_KEY`; optional `SARA_WEB_SEARCH_PROVIDER=brave` | Brave Web Search API supplies snippets and URLs. Search results are not verification. |
| Trusted source policy | `SARA_TRUSTED_SOURCE_DOMAINS=example.gov,example.org` | Only full-text supporting evidence from an explicitly trusted domain can yield a `VERIFIED` proposal. Empty allowlist fails closed to `PARTIALLY_VERIFIED` at best. |
| Optional response LLM | `SARA_RESPONSE_LLM_PROVIDER`, `SARA_RESPONSE_LLM_MODEL`, `SARA_RESPONSE_LLM_API_KEY`; other fields use the `SARA_RESPONSE_LLM_` prefix | Defaults to the JEV model configuration. It receives SARA assessment envelopes as structured context. |
| Optional MCP bridge | `SARA_MCP_CALL_TOOL=module:call_tool`, `SARA_MCP_SEARCH_TOOL`, `SARA_MCP_FETCH_TOOL`; fetch additionally requires `SARA_MCP_FETCH_ALLOWED_DOMAINS` | The host supplies an already-authenticated MCP client callback. Only named tools are called; fetch URLs must be HTTPS and within the configured domain allowlist. This package does not configure MCP servers, authentication, or transport. |

The MCP callback accepts `(tool_name, arguments)` and returns an MCP mapping with `structuredContent` or JSON text content. Search results use a top-level `results` list. Fetch returns `url`, `content`, and optional `content_scope` (`FULL_TEXT` to assert full-text access), title, publisher, and publication date. The host adapter must enforce its own timeout, server identity, authentication, and read-only policy.

## Assessment and state boundaries

- JEV judgment follows the v2.5 rubric and binds only to explicit `claim_candidates`; it does not establish factual truth.
- v2.3 literal citation-fit and evidence-strength signals are kept separate from semantic source alignment.
- v2.4 epistemic and structured logical audit fields are included. Free-text semantic logic is not inferred by the structural audit.
- Evidence relation spans must be exact substrings of the retrieved content. The LLM's relation remains an evaluator proposal, not evidence.
- Snippets/metadata/abstracts alone cannot yield `VERIFIED`. Retrieval success never sets a claim status.
- Evidence placed directly in the dialogue request is treated as an untrusted snippet even when a `text` field is present. Full-text access must come from the configured retrieval/fetch adapter, not an input assertion.
- Evidence conflicts are assessed using v2.5 scope/time/source-independence distinctions; unresolved conflict downgrades the proposal for review.
- Assessments are `PROPOSED`; `truthfulness_status` remains `UNASSESSED`. No response-model output commits a claim status.
- v2.5 provenance events can be recorded in an injected ledger. The default is in-memory and process-local. Durable storage and reviewer authentication are host responsibilities. Commit must use the v2.5 `commit_verification_proposal` gate and a separately recorded ACCEPT review.
- Failure outputs use stable error codes and remain `UNVERIFIED`/`UNASSESSED`; raw exception messages and secrets are not returned.

## Verification

Run the repository suite with `python -m pytest -q`. The full suite passed locally on 2026-10-25 with Python 3.13.9 and pytest 8.4.2 (453 passed). This is local regression evidence only. Before canonical promotion, meet the release gates in [the integration design](../docs/v3-integration-design.md), including live provider smoke tests, Co-thoughts round-trip, independent adjudication, security review, and durable ledger evidence.
