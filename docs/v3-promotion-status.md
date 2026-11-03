# SARA v3 Canonical Promotion Status

**Decision: PROMOTION NOT APPROVED; RELEASE GATES OPEN.**

- **작성일:** 2026-11-03 (초안)
- **대상:** SARA v3.0.0 통합 런타임 후보
- **현재 canonical:** SARA v2.4 (rollback/comparison baseline)
- **후보 commit:** `a0f7a63` (branch `v3-promotion-gates`, ydonchoi/SARA#70; base `main` `9ee11c9`) — 모든 증거는 이 commit에 묶는다. 이후 이 문서만 고치는 commit은 코드·테스트를 바꾸지 않으므로 후보를 바꾸지 않는다. 코드나 테스트가 바뀌면 후보를 다시 지정한다. **G9 SQLite ledger를 추가한 commit은 코드를 바꾸므로, 그 commit의 CI가 통과하면 후보를 그 commit으로 다시 지정해야 한다.**
- **기준 문서:** [v3 통합 설계 기준 §6–§8](v3-integration-design.md)

이 문서는 v3 release gate별 상태와 증거를 한곳에 기록한다. 구현 완료, 로컬 green test, stub/synthetic provider 실행만으로 승격하지 않는다(설계 기준 §6.6). 모든 gate가 `PASSED`이고 아래 승인 기록이 채워진 뒤에만 v3를 canonical로 선언한다.

## 상태 값

| 값 | 의미 |
|---|---|
| `PASSED` | 후보 commit에 묶인 증거가 기록되고 검토됨 |
| `PARTIAL` | 관련 테스트·구현이 있으나 gate 범위를 모두 덮지 못하거나 후보 commit에서 재실행되지 않음 |
| `UNVERIFIED` | 증거 없음; 로컬에서 수행 가능 |
| `BLOCKED` | 외부 환경·배포 선택·사람의 결정이 먼저 필요 |

## Gate 현황

| # | Gate (설계 기준 §7) | 상태 | 현재 근거 | 남은 작업 |
|---|---|---|---|---|
| G0 | 후보 commit 고정 및 해당 commit의 전체 suite 통과 | `PASSED` | 후보 `a0f7a63`의 GitHub Actions check 33개 모두 success (2026-11-03). `SARA v3 Tests`(전체 suite 포함): [push](https://github.com/ydonchoi/SARA/actions/runs/41632302037), [pull_request](https://github.com/ydonchoi/SARA/actions/runs/41634392082); `SARA Contract Tests`: [push](https://github.com/ydonchoi/SARA/actions/runs/41632301902), [pull_request](https://github.com/ydonchoi/SARA/actions/runs/41634392006). 로컬: `9ee11c9`에 후보 변경만 얹은 임시 worktree에서 508 passed, 3 skipped (opt-in live 테스트) | 코드·테스트가 바뀌면 후보 재지정 후 CI 재확인 |
| G1 | JEV rubric 및 v2.5 binding/staleness/failure 계약 회귀 비교 | `PARTIAL` | 로컬 비교 충족: `SARA_v3/tests/test_v3_regression_comparison.py` — frozen 8개 케이스(bound/unbound inference, ambiguous, no-inference, medium/low confidence, stale digest, model timeout)가 v2.5와 v3에서 같은 judgment·activation·reason code로 라우팅되고, 출처 검증은 bound high-confidence 케이스에서만 시작됨; v3 envelope의 v2.4 epistemic·logical audit 결과가 직접 실행한 v2.4 결과와 동일 | 후보 commit에서 재실행 |
| G2 | 각 judgment adapter의 실제 API 형식·structured output 확인 | `BLOCKED` | stub transport 테스트만 존재. live smoke 하네스 `SARA_v3/tests/test_live_provider_smoke.py` 준비(기본 skip, `SARA_V3_LIVE_SMOKE=1`로 활성화, `SARA_V3_LIVE_SMOKE_REPORT`에 commit·provider·결과 기록, API key 노출 검사 포함) 2026-11-03 지원 provider를 **Anthropic만**으로 결정. 같은 날 `claude-sonnet-5-5`로 하네스를 실행했으나 Anthropic API가 HTTP 400 `invalid_request_error`("credit balance is too low")로 거절해 계약 확인은 못 함. 이때 judgment는 `NOT_ASSESSED`/`FAILED`, 응답은 `LLM_PROVIDER_HTTP_ERROR_400`으로 fail-closed되었고 결과에 API key가 포함되지 않음을 확인. Brave key가 없어 웹 검색 smoke는 skip | Anthropic 계정 크레딧 충전 후 후보 commit에서 하네스 재실행, 보고서 첨부. OpenAI·Gemini·Kimi·OpenAI-compatible adapter는 문서에서 `UNVERIFIED`로 표시 |
| G3 | 웹 검색 snippet-only / metadata-only / abstract / full-text / unavailable 케이스, snippet-only ≠ `VERIFIED` | `PARTIAL` | 로컬 계약 충족: `test_v3_integration.py`의 snippet/full-text 테스트, `test_v3_release_gates.py`의 `test_non_full_text_access_levels_cannot_verify`, `test_unavailable_source_cannot_verify`, `test_empty_search_reports_no_evidence_retrieved`, `test_mcp_fetch_without_full_text_scope_is_abstract_and_does_not_verify` | Brave live 검색 smoke; 후보 commit에서 재실행 |
| G4 | provider 임의 `VERIFIED` 무력화; retrieval / citation fit / semantic relation / proposal / reviewer commit 분리 | `PARTIAL` | 로컬 계약 충족: 기존 provider-status 거부·span 검증 테스트, `test_full_text_status_transitions` (상태 전이 8가지), `test_retrieval_and_literal_match_without_relation_assessor_do_not_verify`, `test_proposal_recording_never_commits_status` | 후보 commit에서 재실행 |
| G5 | MCP allowlist, read-only 기본, timeout, malformed 응답, prompt injection, secret redaction | `PARTIAL` | 로컬 계약 충족: 기존 allowlist·prompt injection 테스트, `test_mcp_malformed_search_response_is_rejected`, `test_mcp_malformed_fetch_response_is_rejected`, `test_mcp_fetch_rejects_plain_http_and_credential_urls`, `test_mcp_timeouts_fail_closed_without_leaking_exception_text`, `test_relation_assessor_error_text_is_not_reflected` | read-only·timeout 강제는 host MCP client 책임이므로 실제 host 구성에서 확인; 후보 commit에서 재실행 |
| G6 | Co-thoughts host 호출 → assessment envelope 반환 → 후속 LLM 맥락 보존, 응답이 상태를 바꾸지 못함 | `BLOCKED` | SARA 측 `test_sara_assessment_is_returned_to_external_llm_as_bound_context` (local stub). Co-thoughts 측 구현(ydonchoi/co-thoughts#1, commit `14c1eee`, CI check 2개 success): `SARAv3Connection`이 별도 프로세스(`python -m SARA_v3.cli`)로 SARA v3를 호출하고, `CognitiveRuntime(sara_v3_connection=...)`을 명시적으로 설정했을 때만 실행됨. 전송 범위는 turn ID, 응답 텍스트, claim ID·텍스트로 제한(request context·task·backend evidence·backend status 미전송). 이전 turn의 envelope은 `sara_assessment_envelopes`로 다음 backend 호출에 전달되며, backend가 바꾸거나 지어낸 envelope은 버려지고 `sara_envelope_integrity`에 기록됨. Co-thoughts `tests/unit/test_sara_v3_integration.py` 16 passed, 1 skipped(live) — 실제 SARA checkout을 별도 프로세스로 띄워 provider 미설정 시 fail-closed(`SARA_V3_LLMPROVIDERERROR`)도 확인 | provider를 설정하고 `CO_THOUGHTS_SARA_V3_LIVE=1`로 live 왕복 테스트를 실행해 `CO_THOUGHTS_SARA_V3_LIVE_REPORT` 보고서 첨부. 이 테스트의 Co-thoughts backend는 고정 stub이므로, live 대화 생성 backend를 포함한 사례가 필요하면 별도로 수행 |
| G7 | source verification과 reviewer-bound durable commit 분리; conflict·stale revision·partial failure fail-closed | `PARTIAL` | 로컬 계약 충족: v2.5 `commit_verification_proposal` gate, `test_partial_crawl_remains_non_full_text_and_does_not_verify`, `test_trusted_support_and_challenge_conflict_is_not_verified`, `test_stale_revision_id_with_changed_text_is_not_recorded_as_proposal`, `test_partial_relation_failure_keeps_only_validated_support` | durable ledger(G9)에서 같은 fail-closed 동작 확인; 후보 commit에서 재실행 |
| G8 | 독립 adjudication benchmark와 사전 지정 FP/FN/abstention/latency/cost 기준 | `BLOCKED` | 평가자 미지정, benchmark 미수행 | 기준치 사전 등록, 독립 평가자 지정, v2.4 대비 비교 결과 |
| G9 | 영속 저장·접근 통제·보존·복구·감사 (실제 배포 환경) | `PARTIAL` | 2026-11-03 결정: SQLite 참조 구현. `SARA_v3/durable_ledger.py`의 `SQLiteProvenanceLedger` — v2.5 hash chain·전이 규칙 유지, 한 transaction에 한 event 기록, DB trigger로 UPDATE/DELETE 거부, 다른 프로세스가 먼저 append하면 `LEDGER_CONCURRENT_APPEND`로 거부(chain 분기 방지), 저장 실패 시 메모리 상태 원복, 로드 시 전체 chain·history 재검증, `verify_storage()` 감사, JSONL export/`restore_from_jsonl` 복구. `SARA_PROVENANCE_LEDGER_PATH`로 runtime에 연결되며 proposal의 `ledger_status`가 `DURABLE_SQLITE`로 기록됨. `SARA_v3/tests/test_durable_ledger.py` 9 passed (재시작 후 유지, 변조 거부, 동시 쓰기, 복구, ACCEPT review 없는 commit 거부) | 실제 배포 환경에서 파일 접근 권한·백업·보존 기간·복구 절차 확인; reviewer identity/authorization 방식 결정(§8). 현재 reviewer ID는 호출자가 넘기는 문자열이며 인증되지 않음 |
| G10 | 보안 검토 (SSRF·egress·자격 증명·Crawl4AI 저장물) | `BLOCKED` | Crawl4AI URL/DNS 정책 테스트 존재; 강한 SSRF 보호는 배포 egress 통제에 의존 | 배포 환경의 egress/proxy 구성과 검토 결과 |

`PARTIAL`에 적은 테스트는 후보 `a0f7a63`의 CI(`SARA v3 Tests`)에서 통과했다. 따라서 "후보 commit에서 재실행" 항목은 충족됐다. G1·G4는 남은 작업이 이것뿐이므로, 검토자가 근거를 확인하면 `PASSED`로 올릴 수 있다.

## 미확정 배포 선택 (설계 기준 §8)

G2, G6, G8–G10은 아래 선택이 정해져야 진행할 수 있다.

- [ ] 기본 웹 검색 서비스와 약관·지역·데이터 보존 조건
- [x] 지원 표시할 judgment LLM provider 목록 — 2026-11-03: Anthropic만 (나머지 adapter는 `UNVERIFIED`)
- [ ] MCP server 목록, 인증 방식, 허용 tool, rate limit
- [ ] durable ledger 구현과 reviewer identity/authorization — ledger는 SQLite 참조 구현으로 결정(2026-11-03), reviewer 인증 방식은 미정
- [ ] 외부 호출에 전송 가능한 대화 범위와 retention
- [ ] 배포별 latency·비용 한도와 retry budget

## 승격 절차

1. 후보 commit을 지정하고 G0를 기록한다. (완료: `a0f7a63`)
2. 로컬 gate(G1, G3–G5, G7)의 부족한 테스트를 채우고 후보 commit에서 실행한다.
3. 배포 선택을 확정하고 외부 gate(G2, G6, G8–G10)의 증거를 수집한다.
4. 모든 gate가 `PASSED`가 되면 아래 승인 기록을 작성한다.
5. 같은 변경에서 루트 [README](../README.md), [README_v3](../SARA_v3/README_v3.md), [v3 통합 설계 기준](v3-integration-design.md)의 상태 문구를 갱신하고 v2.4를 이전 baseline으로 표시한다.

후보 commit이 바뀌면 이전 commit의 증거는 참고 자료로만 남기고 해당 gate를 다시 확인한다.

## 승인 기록

| 항목 | 값 |
|---|---|
| 승인자 | _미기록_ |
| 승인일 | _미기록_ |
| 후보 commit | _미기록_ |
| 범위·예외 | _미기록_ |

## 현재 결론

- v3 canonical promotion: **NOT APPROVED**
- 후보 commit: **`a0f7a63`** — CI 33개 check 통과 (G0 `PASSED`)
- Live provider / host / benchmark / durable ledger / security: **UNVERIFIED 또는 BLOCKED**
- Canonical baseline: **SARA v2.4 유지**
