# SARA v3.0.0 integration candidate

**Status:** SARA v3.0.0 integration candidate on `main`, not canonical. SARA v2.4 remains the canonical baseline until the v3 release gates pass. Local contracts and stub tests do not establish live-provider quality, a Co-thoughts → SARA → assessment-return host connection, production security, durable storage, or promotion readiness.

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
| Optional Crawl4AI fetcher | `SARA_CRAWL4AI_ENABLED=1`, `SARA_CRAWL4AI_ALLOWED_DOMAINS=example.org` | Fetch-only fallback after MCP when evidence is not full text. Disabled by default. It uses a local Chromium browser, respects robots.txt, and stores raw HTML and Markdown separately under `SARA_CRAWL4AI_STORE_DIR` (default `.sara-crawl4ai`). |

### Crawl4AI setup and limits

Crawl4AI is an optional dependency, pinned separately from the core runtime:

```powershell
python -m pip install -r requirements-test.txt -r requirements-crawl4ai.txt
crawl4ai-setup
```

Configure an explicit fetch allowlist before enabling it:

```powershell
$env:SARA_CRAWL4AI_ENABLED = "1"
$env:SARA_CRAWL4AI_ALLOWED_DOMAINS = "example.org,example.gov"
$env:SARA_CRAWL4AI_STORE_DIR = ".sara-crawl4ai"
$env:SARA_CRAWL4AI_TIMEOUT_SECONDS = "20"
$env:SARA_CRAWL4AI_MAX_PAGES = "3"
$env:SARA_CRAWL4AI_MAX_STORED_BYTES = "2000000"
```

The adapter accepts only HTTPS on port 443, rejects literal IPs and credential-bearing URLs, checks DNS answers and browser requests against the domain policy, blocks image/media/font requests, and limits each claim verification to at most three pages and one active page by default. Its timeout is per page, not an end-to-end dialogue deadline. Out-of-allowlist subresources are blocked too, so sites that require a separate script/CDN host need that host explicitly allowlisted. These checks reduce exposure but do not pin the browser's DNS resolution or impose a hard network download cap before Chromium has received a response. Production deployments still need network egress controls or a validating proxy for strong SSRF and response-size protection. Use only sources the operator is permitted to access and honor publisher access policies.

The adapter records transport/retrieval status, extraction status and source-level completeness separately; it does not return `verification_status`. A technically complete extraction is recorded as `extraction_status=COMPLETE`, while `completeness_status=UNKNOWN` because Crawl4AI cannot establish that a page contains an entire article or that the publisher exposed all of its content. Crawl4AI output stays at `ABSTRACT` access and cannot by itself produce a `VERIFIED` result; SARA requires independently confirmed `completeness_status=COMPLETE` for full-text evidence. Empty/partial/oversized extraction is not used to replace existing search evidence when it has no useful text. Raw HTML and Markdown can contain sensitive or copyrighted material: configure storage access, retention and cleanup accordingly. Browser startup and JavaScript execution may increase latency; benchmark the actual source mix before enabling it broadly.

For a public-network integration check, set `SARA_CRAWL4AI_LIVE_TEST=1` and `SARA_CRAWL4AI_ALLOWED_DOMAINS=quotes.toscrape.com`, then run `python -m pytest -q SARA_v3/tests/test_crawl4ai_live.py`. The test uses the site's JavaScript demonstration page and stores artifacts under pytest's temporary directory. For a reproducible latency smoke comparison against a direct HTTP fetch, use `python -m SARA_v3.crawl4ai_benchmark --url ... --allowed-domains ...`. Results are workload-specific and not proof of general speed improvement.

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

Run the repository suite with `python -m pytest -q`. The full suite passed locally on 2026-10-25 with Python 3.13.9 and pytest 8.4.2 (453 passed) on the v3 integration candidate. This is local regression evidence only. Before canonical promotion, meet the release gates in [the integration design](../docs/v3-integration-design.md), including live provider smoke tests, an approved Co-thoughts host invocation and assessment-return test, independent adjudication, security review, and durable ledger evidence.
