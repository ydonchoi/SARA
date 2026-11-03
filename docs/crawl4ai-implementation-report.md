# SARA × Crawl4AI 구현·검증 보고서

검토일: 2026-11-03 (Asia/Seoul)

## 결과 요약

기존 SARA v3의 `content_fetcher` 경계에 Crawl4AI를 선택형 단일 페이지 수집 fallback으로 연결했다. 기본 비활성화이며, 허용 도메인이 명시된 경우에만 MCP fetch 이후의 빈/부분 근거를 보완한다. 기존 주장 검증, 출처 신뢰 정책 및 검증 상태 결정은 SARA에 남겨 둔다.

성능 개선은 일반적으로 확인되지 않았다. 공개 JS 데모 페이지 1회 측정에서 직접 HTTP는 0.595초였고 Crawl4AI는 8.069초였다(브라우저 초기화 포함). 직접 HTTP 추출에 없던 동적 페이지의 기대 인용 문구는 Crawl4AI Markdown에서 확인됐다. 따라서 결과는 속도 개선이 아니라 특정 JS 페이지의 추출 범위 개선 가능성에 대한 단일 smoke 비교다. 운영 전 실제 사이트 구성으로 반복 벤치마크해야 한다.

후속 코드 리뷰에서 판정 무결성 결함을 발견해 아래 수정과 회귀 테스트를 추가했다. 새 결과에서 Crawl4AI는 원 출처 전체가 확인되지 않으므로 `ABSTRACT`로만 입력되고 `VERIFIED`에 기여하지 않는다. 신뢰 도메인은 redirect 전 URL이 아니라 검증된 최종 URL로 계산한다. 정보가 없는 부분 추출은 검색 근거를 덮어쓰지 않으며, 유효한 추출이 기존 검색 근거를 보완할 때 기존 서지 정보를 우선 보존한다. 페이지 예산은 각 claim verification 호출에서 초기화된다.

외부 평가 중 P1–P4는 코드에서 재현돼 수정했다. P1의 설명은 부분적으로 정확하다: 본문 없는 partial capture는 실제로 고정 fallback 문구로 검색 snippet을 덮어쓸 수 있었으나, 모든 partial capture가 그렇게 동작하는 것은 아니었다. P5는 실제 제한으로 남긴다. P6은 별도 CDN origin을 허용 목록에 명시해야 하는 정책/기능 절충이다. P7은 ignore 규칙 추가와 함께, 이미 추적되던 bytecode와 제3자 페이지 사본을 Git 추적에서 제거해 완료했다.

## 통합 설계 및 데이터

- 기존 동기식 `content_fetcher.fetch(url)` 계약을 유지한다. 브라우저 crawler는 adapter 수명 동안 재사용한다.
- 설치·설정이 선택 사항이며 기본 비활성화다. 활성화 시 HTTPS 및 명시적 도메인 목록이 필수다.
- 페이지당 결과에서 source URL/final URL, UTC 수집 시각, HTTP 상태, 원문·Markdown SHA-256, content-addressed 저장 참조, extractor 버전 및 상태를 기록한다.
- 원 HTML과 Markdown을 서로 다른 파일로 저장한다. 중복 해시는 기존 저장물을 재사용한다.
- `retrieval_status`, `extraction_status`, `completeness_status`를 별도로 관리한다. 추출기 실행 완료는 발행 원문의 완전성을 증명하지 않으므로 `COMPLETE` 추출은 `completeness_status=UNKNOWN`으로 기록한다. 빈/부분/용량 초과 추출은 `FULL_TEXT`로 승격하지 않는다.
- Crawl4AI는 `verification_status`를 생성하지 않는다. SARA의 관계 평가 및 신뢰 도메인 검사를 계속 거친다.
- 접근은 본문 추출을 위한 단일 URL 요청으로 제한한다. 페이지 최대 3개, 동시성 최대 2(기본 1), 요청 timeout, 허용 도메인, robots 검사 및 이미지/미디어/폰트 차단을 적용한다.

## 변경 파일

- `SARA_v3/crawl4ai_adapter.py`: 선택형 fetch adapter, URL/DNS/브라우저 요청 검사, 저장 및 metadata. Claim당 페이지 예산과 보수적인 ABSTRACT 접근 수준.
- `SARA_v3/crawl4ai_benchmark.py`: 명시된 URL의 직접 HTTP와 브라우저 추출 latency/문구 비교 도구.
- `SARA_v3/contracts.py`, `SARA_v3/verification.py`, `SARA_v3/runtime.py`: 최종 URL 기반 domain 신뢰, UNKNOWN 원문 완전성의 FULL_TEXT 승격 차단, 부분결과 병합 및 설정 시 adapter 수명 정리.
- `SARA_v3/tests/test_crawl4ai_adapter.py`, `SARA_v3/tests/test_crawl4ai_live.py`: deterministic 단위/통합 테스트와 opt-in 실페이지 테스트.
- `requirements-crawl4ai.txt`: 선택 의존성 `crawl4ai==0.9.5`; `requirements-test.txt`의 pytest 고정 의존성 사용.
- `.gitignore`: Python/test/cache, 가상환경과 수집 저장 경로 제외 규칙.
- `SARA_v3/README_v3.md`, `README.md`, `docs/v3-integration-design.md`: 설치, 설정, 상태 의미 및 운영 한계.
- `docs/crawl4ai-implementation-report.md`: 이 결과 보고서.

## 설치 및 실행 방법

Python 3.12 이상 가상환경에서 저장소 루트 기준:

```powershell
python -m pip install -r requirements-test.txt -r requirements-crawl4ai.txt
crawl4ai-setup
python -m pytest -q
```

선택 수집 설정 예시:

```powershell
$env:SARA_CRAWL4AI_ENABLED = "1"
$env:SARA_CRAWL4AI_ALLOWED_DOMAINS = "example.org"
$env:SARA_CRAWL4AI_STORE_DIR = ".sara-crawl4ai"
```

성능 smoke 예시(운영 허가를 받은 호스트만 허용 목록에 기입):

```powershell
python -m SARA_v3.crawl4ai_benchmark --url https://example.org/article --allowed-domains example.org --repetitions 3
```

실페이지 테스트는 기본 제외되어 있다. 격리된 검증 환경에서만 명시적으로 활성화한다:

```powershell
$env:SARA_CRAWL4AI_LIVE_TEST = "1"
$env:SARA_CRAWL4AI_ALLOWED_DOMAINS = "quotes.toscrape.com"
python -m pytest -q SARA_v3/tests/test_crawl4ai_live.py
```

## 검증 결과

| 항목 | 상태 | 실제 결과 / 기대 기준 | 미해결 사항 |
|---|---|---|---|
| pytest 및 Crawl4AI 실행환경 | Completed, Verified | Python 3.13.9 환경에 pytest 8.4.2, Crawl4AI 0.9.5, 브라우저 설치 | 이 검증환경은 저장소 기본 Python 실행 파일 대신 별도 가상환경을 사용함 |
| Adapter/계약/회귀 테스트 | Verified | 수정 후 `python -m pytest -p no:cacheprovider -q`: **470 passed, 1 skipped, 12.96s** | opt-in 실페이지는 기본 전체 테스트에서 skip됨 |
| 기존 v3 통합 포함 집중 테스트 | Verified | 수정 후 **26 passed, 1 skipped, 3.13s** | 없음 |
| P1–P4 회귀 테스트 | Verified | UNKNOWN 전체 텍스트 거부, 최종 redirect host 사용, 빈 부분 추출 시 기존 evidence 보존, claim마다 page budget 초기화 테스트 추가 | P5 end-to-end deadline은 보장하지 않음 |
| 실페이지 JS 수집 | Verified | 허용 목록 `quotes.toscrape.com`의 `/js/`: 최종 코드 **1 passed, 14.55s**. HTTP 200, marker 추출, `ABSTRACT` 반환 확인 | 제3자 공개 데모의 일회성 실행 |
| 성능 smoke 비교 | Partially verified | 1회: 직접 HTTP 0.595초, 본문 5,808 bytes/583 visible chars, 기대 문구 없음. Crawl4AI 8.069초, Markdown 1,666 chars, 기대 문구 발견. 원 출처 완전성은 `UNKNOWN` | 표본 1회, 네트워크/브라우저 cold-start 영향, 처리량·정확도 통계 미측정. 일반 속도 향상 근거 없음 |
| SSRF/URL 정책 단위 검사 | Partially verified | 테스트에서 HTTP scheme, 비허용 호스트, userinfo/비표준 포트, IP literal, loopback/private/link-local 주소 및 저장 경로 traversal 차단 확인 | 실제 내부망 및 클라우드 메타데이터 대상 접근 시험은 실행하지 않음 |
| 리디렉션 목적지 | Partially verified | 브라우저 요청 라우팅 검사와 최종 URL allowlist 검증 코드 존재 | 외부 실페이지 redirect를 이용한 동작 검증은 하지 않음 |
| Robots 정책 | Partially verified | Crawl4AI `check_robots_txt=True` 설정 | robots 거부 fixture/live 시나리오는 실행하지 않음 |
| 프롬프트 인젝션 문자열 | Verified | 단위 테스트에서 문자열을 출처 데이터로 전달하며 provider 결과가 검증 상태를 설정하지 못함 | 실제 LLM 연결은 실행하지 않음 |
| 비밀정보 비노출 | Partially verified | 오류는 안정된 코드로 변환되고 테스트 fetch에 credentials 없음 | 실제 자격 증명 입력/로그 수집 점검은 실행하지 않음 |
| 저장 크기 제한 | Partially verified | 초과 결과 저장 참조를 발급하지 않고 `OVERSIZE` 처리 | 제한은 browser가 응답을 메모리에 받은 뒤 적용됨. 다운로드 전 네트워크 상한이 아님 |
| 저장소 Git diff/변경목록 확인 | Verified | 2026-11-03 Git 접근이 가능한 환경에서 `9ee11c9` 대비 diff를 검토함. 변경은 위 P1–P4 수정, 회귀 테스트, 문서 갱신과 일치하며 추가 결함은 발견되지 않음 | 없음 |
| 저장소 정리 평가(P7) | Completed | `9ee11c9` 기준 `.pyc`/`__pycache__` 118개와 제3자 페이지 사본(`.sara-crawl4ai-benchmark/` 아래 quotes.toscrape.com HTML 1개, Markdown 1개)이 추적되고 있었음. 모두 Git 추적에서 제거하고(로컬 파일은 유지) `.gitignore`를 커밋함 | 이전 commit 이력에는 해당 파일이 남아 있음. 이력에서 지우려면 별도 history rewrite가 필요함 |
| 임시 가상환경 정리 | Completed | 2026-11-03 확인 시 `.venv-crawl4ai` 디렉터리가 더 이상 존재하지 않음 | 없음 |

## 보안 및 운영 한계

1. URL 사전 DNS 검사와 Playwright 요청 hook의 DNS 검증 사이에는 DNS 재바인딩/TOCTOU 가능성이 있다. 브라우저가 검사한 IP로 고정 접속하도록 보장하지 않는다. 운영에서 SSRF를 강하게 방어하려면 외부 egress 방화벽 또는 DNS/IP를 고정 검증하는 outbound proxy가 필요하다.
2. 최대 저장 바이트는 browser 결과가 메모리에 생성된 뒤 저장 여부를 정한다. 매우 큰 응답의 네트워크/메모리 사용량을 차단하는 hard limit은 아니다.
3. redirect 검사, DNS 검사, 허용 도메인 및 robots 설정이 있어도 사이트 이용약관, 저작권, 개인정보 처리 및 접근 허가를 대신하지 않는다. raw HTML과 Markdown의 보존 기간/파일 권한을 운영자가 정해야 한다.
4. 악성 웹 콘텐츠는 신뢰하지 않는 source text로 전달되며, 이 모듈은 페이지 문구를 실행하거나 도구 지시로 처리하지 않는다. 후속 LLM 시스템은 별도 prompt-injection 경계를 유지해야 한다.
5. 작성 당시에는 Git 상태 접근 장애로 변경 diff를 독립 검토하지 못했다. 2026-11-03 Git 접근이 가능한 환경에서 diff를 검토하고 저장소 정리(P7)를 마쳤다.
6. 하위 요청도 같은 도메인 허용 정책을 적용하므로 별도 CDN/script origin이 필요한 사이트는 기능이 제한될 수 있다. 해당 origin을 추가할 때는 운영자가 허용 근거를 확인해야 한다.
7. P5의 전체 turn deadline은 기존 SARA 호출 계약에서도 구현되어 있지 않다. Crawl4AI는 페이지마다 timeout을 적용하고 claim당 페이지 수를 제한하지만, 최대 3개 수집과 LLM/검색 시간을 합친 전체 벽시계 예산은 아직 강제하지 않는다.
