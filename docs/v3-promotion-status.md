# SARA v3 Canonical Promotion Status

**Decision: PROMOTED — SARA v3.0.0 is canonical as of 2026-11-03 (source release; waived gates are user/operator responsibilities).**

- **작성일:** 2026-11-03
- **대상:** SARA v3.0.0 통합 런타임 후보
- **현재 canonical:** SARA v3.0.0 (2026-11-03부터). SARA v2.4는 이전 baseline이며 rollback·회귀 비교 기준으로 유지
- **후보 commit:** `7db1cdb` (branch `v3-promotion-gates`, ydonchoi/SARA#70; base `main` `9ee11c9`). 이 commit은 G9 SQLite ledger, Crawl4AI 판정 무결성 수정, 저장소 정리를 포함한다. 이후 이 문서만 고치는 commit은 코드·테스트를 바꾸지 않으므로 후보를 바꾸지 않는다. 코드나 테스트가 바뀌면 후보를 다시 지정한다. 이전 후보 `a0f7a63`의 CI 증거는 참고 자료로 남긴다.
- **기준 문서:** [v3 통합 설계 기준 §6–§8](v3-integration-design.md)

이 문서는 v3 release gate별 상태와 증거를 한곳에 기록한다. 구현 완료, 로컬 green test, stub/synthetic provider 실행만으로 승격하지 않는다(설계 기준 §6.6). 모든 gate가 `PASSED` 또는 `WAIVED`이고 아래 승인 기록이 채워진 뒤에만 v3를 canonical로 선언한다.

## 승격 범위 결정 (2026-11-03, 저장소 소유자)

v3 승격은 **코드 공개(source release)** 범위로 한다. 배포 계획이 없으므로 운영·배포 환경에 속한 gate와, SARA 코드가 아니라 사용자 계정·자원에 달린 gate는 승격 단계에서 제외(`WAIVED`)하고 사용자/운영자 책임으로 넘긴다.

- **사용자 부담으로 이관:** G2(live provider: 계정·크레딧), G6(Co-thoughts live 왕복: 계정·크레딧), G8(독립 평가자 지정과 benchmark)
- **배포 범위 밖:** G9(배포 환경의 영속 저장·접근 통제), G10(배포 환경 보안 검토)
- 같은 이유로 G3의 Brave live 검색 smoke와 G5의 host MCP client 측 read-only·timeout 강제도 승격 범위에서 제외한다.

`WAIVED`는 해당 항목이 검증됐다는 뜻이 아니다. 이 SARA 버전을 실제로 운영하려는 사용자는 아래 "운영 전 사용자 책임" 항목을 직접 확인해야 한다.

## 상태 값

| 값 | 의미 |
|---|---|
| `PASSED` | 후보 commit에 묶인 증거가 기록되고 검토됨 |
| `WAIVED` | 저장소 소유자가 승격 범위에서 제외함. 검증되지 않았으며 운영 전 사용자/운영자 책임 |
| `PARTIAL` | 관련 테스트·구현이 있으나 gate 범위를 모두 덮지 못하거나 후보 commit에서 재실행되지 않음 |
| `UNVERIFIED` | 증거 없음; 로컬에서 수행 가능 |
| `BLOCKED` | 외부 환경·배포 선택·사람의 결정이 먼저 필요 |

## Gate 현황

| # | Gate (설계 기준 §7) | 상태 | 근거 | 승격 후 남는 사용자/운영자 책임 |
|---|---|---|---|---|
| G0 | 후보 commit 고정 및 해당 commit의 전체 suite 통과 | `PASSED` | 후보 `7db1cdb`의 GitHub Actions check 34개 모두 success(아래 "후보 CI 증거"). 로컬: 같은 commit에서 520 passed, 3 skipped (skip은 opt-in live 테스트) | 이후 코드·테스트 변경은 각자의 CI로 확인 |
| G1 | JEV rubric 및 v2.5 binding/staleness/failure 계약 회귀 비교 | `PASSED` | `SARA_v3/tests/test_v3_regression_comparison.py` — frozen 8개 케이스(bound/unbound inference, ambiguous, no-inference, medium/low confidence, stale digest, model timeout)가 v2.5와 v3에서 같은 judgment·activation·reason code로 라우팅되고, 출처 검증은 bound high-confidence 케이스에서만 시작됨. v3 envelope의 v2.4 epistemic·logical audit 결과가 직접 실행한 v2.4 결과와 동일 | 없음 |
| G2 | 각 judgment adapter의 실제 API 형식·structured output 확인 | `WAIVED` (사용자 부담) | 지원 provider는 Anthropic만으로 결정. live smoke 하네스 `SARA_v3/tests/test_live_provider_smoke.py` 제공(`SARA_V3_LIVE_SMOKE=1`, 보고서 `SARA_V3_LIVE_SMOKE_REPORT`, API key 노출 검사 포함). 2026-11-03 `claude-sonnet-5-5` 실행은 Anthropic API가 "credit balance is too low"(HTTP 400)로 거절해 계약 확인은 못 함. 이때 judgment는 `NOT_ASSESSED`/`FAILED`, 응답은 `LLM_PROVIDER_HTTP_ERROR_400`으로 fail-closed되었고 결과에 API key가 포함되지 않음 | 사용할 provider 계정으로 하네스 실행. OpenAI·Gemini·Kimi·OpenAI-compatible adapter는 stub 테스트만 있으며 `UNVERIFIED` |
| G3 | 웹 검색 snippet-only / metadata-only / abstract / full-text / unavailable 케이스, snippet-only ≠ `VERIFIED` | `PASSED` (live 검색 제외) | `test_v3_integration.py`의 snippet/full-text 테스트, `test_v3_release_gates.py`의 `test_non_full_text_access_levels_cannot_verify`, `test_unavailable_source_cannot_verify`, `test_empty_search_reports_no_evidence_retrieved`, `test_mcp_fetch_without_full_text_scope_is_abstract_and_does_not_verify`. Crawl4AI 수집 결과도 `ABSTRACT`로만 들어가 `VERIFIED`에 기여하지 않음(`test_crawl_fetcher_integrates_without_trusting_its_status`) | Brave key로 `test_live_web_search_snippets_never_verify` 실행 |
| G4 | provider 임의 `VERIFIED` 무력화; retrieval / citation fit / semantic relation / proposal / reviewer commit 분리 | `PASSED` | 기존 provider-status 거부·span 검증 테스트, `test_full_text_status_transitions`(상태 전이 8가지), `test_retrieval_and_literal_match_without_relation_assessor_do_not_verify`, `test_proposal_recording_never_commits_status`, `test_status_commit_requires_recorded_accept_review_and_persists` | 없음 |
| G5 | MCP allowlist, read-only 기본, timeout, malformed 응답, prompt injection, secret redaction | `PASSED` (host 측 제외) | 기존 allowlist·prompt injection 테스트, `test_mcp_malformed_search_response_is_rejected`, `test_mcp_malformed_fetch_response_is_rejected`, `test_mcp_fetch_rejects_plain_http_and_credential_urls`, `test_mcp_timeouts_fail_closed_without_leaking_exception_text`, `test_relation_assessor_error_text_is_not_reflected` | MCP 연결 시 host client에서 read-only·timeout·서버 인증 강제 |
| G6 | Co-thoughts host 호출 → assessment envelope 반환 → 후속 LLM 맥락 보존, 응답이 상태를 바꾸지 못함 | `WAIVED` (사용자 부담) | 구현과 local 증거는 있음: SARA 측 `test_sara_assessment_is_returned_to_external_llm_as_bound_context`; Co-thoughts 측 ydonchoi/co-thoughts#1(`14c1eee`, CI 통과) — `SARAv3Connection`이 별도 프로세스로 SARA v3를 호출, 전송 범위 제한, envelope 전달·변조 거부, 실제 SARA 프로세스의 fail-closed 확인. live 왕복은 provider 계정이 필요해 실행하지 않음 | `CO_THOUGHTS_SARA_V3_LIVE=1`로 live 왕복 실행 |
| G7 | source verification과 reviewer-bound durable commit 분리; conflict·stale revision·partial failure fail-closed | `PASSED` | v2.5 `commit_verification_proposal` gate, `test_partial_crawl_remains_non_full_text_and_does_not_verify`, `test_trusted_support_and_challenge_conflict_is_not_verified`, `test_stale_revision_id_with_changed_text_is_not_recorded_as_proposal`, `test_partial_relation_failure_keeps_only_validated_support`; SQLite ledger에서도 `test_stale_revision_is_rejected_by_durable_ledger` | 없음 |
| G8 | 독립 adjudication benchmark와 사전 지정 FP/FN/abstention/latency/cost 기준 | `WAIVED` (사용자 부담) | 평가자 미지정, benchmark 미수행. 비교 우위 주장은 하지 않음 | 품질 주장을 하려면 기준치 사전 등록, 독립 평가자 지정, v2.4 대비 비교 |
| G9 | 영속 저장·접근 통제·보존·복구·감사 (실제 배포 환경) | `WAIVED` (배포 범위 밖) | 코드 측 참조 구현은 있음: `SARA_v3/durable_ledger.py`의 `SQLiteProvenanceLedger`(hash chain·전이 규칙, DB trigger로 UPDATE/DELETE 거부, 동시 append 거부, 로드 시 재검증, `verify_storage()` 감사, JSONL 복구, `SARA_PROVENANCE_LEDGER_PATH`). `test_durable_ledger.py` 9 passed | 배포 시 파일 권한·백업·보존·복구 절차 확인. reviewer ID는 호출자가 넘기는 문자열이며 인증되지 않음 |
| G10 | 보안 검토 (SSRF·egress·자격 증명·Crawl4AI 저장물) | `WAIVED` (배포 범위 밖) | Crawl4AI URL/DNS·redirect 정책 테스트 존재. 신뢰 도메인은 최종 redirect host로 판정. 강한 SSRF·응답 크기 보호는 배포 egress 통제에 의존 | 배포 시 egress 방화벽 또는 검증 proxy, 수집 저장물 보존·권한 설정 |

## 후보 CI 증거

- 후보 `7db1cdb`: check 34개 모두 success (2026-11-03) — `SARA v3 Tests`(전체 suite 포함) [push](https://github.com/ydonchoi/SARA/actions/runs/41636547619), [pull_request](https://github.com/ydonchoi/SARA/actions/runs/41636553913); `SARA Contract Tests` [push](https://github.com/ydonchoi/SARA/actions/runs/41636547514), [pull_request](https://github.com/ydonchoi/SARA/actions/runs/41636554130)
- 문서 commit `635dc56`(gate 범위 기록): check 34개 모두 success
- 중간 commit `d2d0ee6` (G9 ledger 추가, 참고): check 33개 모두 success
- 이전 후보 `a0f7a63` (참고): check 33개 모두 success — `SARA v3 Tests` [push](https://github.com/ydonchoi/SARA/actions/runs/41632302037), [pull_request](https://github.com/ydonchoi/SARA/actions/runs/41634392082); `SARA Contract Tests` [push](https://github.com/ydonchoi/SARA/actions/runs/41632301902), [pull_request](https://github.com/ydonchoi/SARA/actions/runs/41634392006)

## 운영 전 사용자 책임

v3를 실제 서비스나 연구 운영에 쓰려면 아래를 직접 확인해야 한다.

- 사용할 LLM provider로 live smoke 실행(G2), Co-thoughts 연동 시 live 왕복 실행(G6)
- 웹 검색 서비스 약관·지역·데이터 보존 조건, 외부 호출로 보내도 되는 대화 범위
- MCP 연결 시 server 목록, 인증, 허용 tool, read-only·timeout 강제
- 영속 ledger 저장 위치의 권한·백업·보존, reviewer 인증 방식(G9)
- egress 통제와 Crawl4AI 수집 저장물 관리(G10)
- 품질·비교 우위를 주장하려면 독립 평가(G8)

## 승격 절차

1. 후보 commit을 지정하고 G0를 기록한다. (완료: `7db1cdb`, CI 34개 통과)
2. 로컬 gate(G1, G3–G5, G7)를 후보 commit에서 확인한다. (완료)
3. 승격 범위 밖 gate를 `WAIVED`로 기록한다. (완료: G2, G6, G8, G9, G10)
4. 아래 승인 기록을 작성한다. (완료)
5. 같은 변경에서 루트 [README](../README.md), [README_v3](../SARA_v3/README_v3.md), [v3 통합 설계 기준](v3-integration-design.md)의 상태 문구를 갱신하고 v2.4를 이전 baseline으로 표시한다. (완료: v2.4·v2.5 문서와 v2.4 회귀 기준 정책의 현재 상태 문구도 함께 갱신)

## 승인 기록

| 항목 | 값 |
|---|---|
| 승인자 | ydonchoi (저장소 소유자) |
| 승인일 | 2026-11-03 |
| 후보 commit | `7db1cdb` (ydonchoi/SARA#70) |
| 승인 조건 | 후보 commit의 CI 통과 시 승격 — 충족(check 34개 success) |
| 범위·예외 | 코드 공개 범위. G2·G6·G8은 사용자 부담, G9·G10은 배포 범위 밖으로 `WAIVED` |

## 현재 결론

- v3 canonical promotion: **APPROVED** (2026-11-03)
- 승격 commit: **`7db1cdb`**
- `PASSED`: G0, G1, G3, G4, G5, G7 / `WAIVED`: G2, G6, G8, G9, G10
- Canonical: **SARA v3.0.0**; v2.4는 이전 baseline·회귀 비교 기준
- 실제 canonical 전환은 ydonchoi/SARA#70이 `main`에 merge될 때 적용된다
