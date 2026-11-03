# SARA

**Evidence-Centered Research Analysis & Epistemic Verification System**

SARA는 연구 주장을 근거·방법·출처와 연결해 검토하고, 검증 상태와 불확실성을 분리해 기록하는 연구 분석 시스템입니다. 저장소에는 버전별 설계 문서, Python 실행 모듈, 계약 테스트가 함께 있습니다.

> **현재 상태:** v3.0.0이 canonical 버전입니다(2026-11-03 승격, tag `v3.0.0`, 코드 공개 범위). v2.4는 이전 baseline이자 회귀 비교 기준으로 유지되고, v2.5는 호환·trial 경로입니다. 승격은 로컬·CI 계약 gate에 근거하며, live provider 연결, Co-thoughts live 왕복, 독립 평가, 배포 환경의 저장·보안은 검증하지 않고 사용자/운영자 책임으로 남겼습니다. 자세한 내용은 [v3 승격 기록](docs/v3-promotion-status.md)을 참고하세요.

## 무엇을 하는가

- Claim, premise, evidence, source, provenance 사이의 참조와 경계를 추적합니다.
- 시스템 실행 검증과 연구 내용 검증을 구분합니다.
- 검증 결과, 인용 정보, 논리 검토, 판단 신호를 서로 다른 상태로 유지합니다.
- 명시적으로 제공된 주장 후보를 대상으로 선택적 검토와 재검증 흐름을 구성합니다.
- 결정론적 계약 테스트로 입력·출력 및 실패 경계를 확인합니다.

SARA의 구조적·계약 검사는 의미론적 사실 판정이나 독립적인 학술 리뷰를 대신하지 않습니다. `VERIFIED`는 해당 검증 경로의 제한된 결과이며, 그 자체로 주장의 진실성이 확립됐다는 뜻은 아닙니다.

## 버전과 현재 상태

| 버전 | 역할 | 상태 |
|---|---|---|
| v1.0 | 초기 연구 분석 프레임워크 | 이력 (저장소에 포함되지 않음) |
| v2.1 | 분석 모듈화 | 보존된 이력 (`LEGACY/`) |
| v2.2 | 의존성·로딩·계약 관리 | 보존된 이력 (`LEGACY/`) |
| v2.3 | 실행 경계, evidence 검증, 재현/시뮬레이션 구분 | v3가 사용하는 호환·실행 기반 |
| v2.4 | Claim/premise 상태, provenance, attribution, temporal context, 구조화 argument audit | 이전 canonical baseline; 회귀 비교 기준 |
| v2.5 | Claim identity, evidence conflict, provenance ledger, selective reverification, 내부 판단(JEV) 경로와 CLI | 호환·trial 경로; 주요 계약은 v3에 통합됨 |
| **v3.0.0** | v2.3~v2.5 통합 대화 런타임, 외부 LLM judgment/응답, 기본 웹 검색, 선택 MCP·Crawl4AI, SARA assessment envelope, SQLite 영속 ledger | **canonical (2026-11-03, 코드 공개 범위; 운영 검증은 사용자 책임)** |

판단 adapter는 OpenAI API, Anthropic Messages, Gemini `generateContent`, Kimi(OpenAI-compatible JSON mode), 일반 OpenAI-compatible endpoint 경로를 구현합니다. 지원 provider로 지정한 것은 **Anthropic**이며, 나머지 adapter는 stub transport 테스트만 있어 `UNVERIFIED`입니다. Anthropic도 live 계약 확인은 사용자 책임으로 남아 있습니다. JSON mode 응답은 SARA가 로컬 schema 계약으로 다시 검사합니다. 소비자용 ChatGPT, Claude, Gemini 앱의 내부 대화 흐름에는 자동 연결되지 않습니다.

## 빠른 시작

### 요구 사항

- Python 3.12 이상 (CI는 3.12, 로컬 확인은 3.13)
- 테스트 실행에는 저장소 루트의 `requirements-test.txt`에 고정된 pytest가 필요합니다.
- 2026-11-03 승격 commit `7db1cdb`: GitHub Actions check 34개 통과, 로컬 Python 3.13 / pytest 8.4.2에서 **520 passed, 3 skipped** (skip은 opt-in live 테스트).

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
python -m pytest -q
```

macOS/Linux에서는 가상환경을 `. .venv/bin/activate`로 활성화합니다. 별도 Python 패키지 배포물은 제공하지 않습니다.

### v3 대화 실행

`SARA_v3/cli.py`는 v2.5 JEV judgment를 외부 LLM으로 실행하고, 기본 Brave 웹 검색으로 자료를 찾은 뒤 SARA가 evidence 관계·접근 범위·충돌을 assessment envelope으로 반환합니다. 그 envelope은 후속 LLM 응답에 구조화 맥락으로 전달됩니다. 검색 snippet만으로 `VERIFIED`가 되지 않으며, `VERIFIED` proposal을 내려면 설정한 신뢰 도메인의 원문과 검증된 supporting span이 필요합니다. 모든 결과는 `PROPOSED`이고, 사람 검토와 v2.5 commit gate 전에는 확정 상태가 아닙니다.

```powershell
$env:SARA_LLM_PROVIDER = "anthropic" # 구현된 경로: openai, gemini, kimi, openai_compatible
$env:SARA_LLM_MODEL = "your-model-id"
$env:SARA_LLM_API_KEY = "your-api-key"
$env:BRAVE_SEARCH_API_KEY = "your-brave-search-key"
$env:SARA_TRUSTED_SOURCE_DOMAINS = "example.gov,example.org"
$env:SARA_PROVENANCE_LEDGER_PATH = ".\sara-ledger.sqlite" # 선택: 영속 ledger
Get-Content .\turn.json -Raw | python -m SARA_v3.cli
```

입력은 `request_id`, `conversation_id`, `turn_id`, `content`, 명시적인 `claim_candidates`를 가진 JSON입니다. API key를 요청 JSON, 소스 파일, 커밋에 넣지 마세요.

- **MCP:** 자동 탐색하지 않습니다. 호스트의 인증된 MCP client를 `SARA_MCP_CALL_TOOL=module:call_tool`로 연결하고, 사용할 tool 이름을 `SARA_MCP_SEARCH_TOOL`/`SARA_MCP_FETCH_TOOL`에 명시해야 합니다. Fetch tool에는 `SARA_MCP_FETCH_ALLOWED_DOMAINS`가 필수입니다.
- **Crawl4AI:** 별도로 설치하는 단일 페이지 수집기가 선택형 fetch fallback으로 제공됩니다. 기본 비활성화이며 명시적인 HTTPS 도메인 허용 목록이 필요합니다. 수집 결과는 `ABSTRACT`로만 들어가 `VERIFIED`에 기여하지 않습니다.
- **Provenance ledger:** 기본값은 process-local memory입니다. `SARA_PROVENANCE_LEDGER_PATH`를 설정하면 SQLite 영속 ledger(append-only, hash chain 재검증, JSONL 복구)를 사용합니다. 파일 권한·백업·보존과 reviewer 인증은 운영자 책임입니다.

상세 계약·환경변수·한계는 [v3 안내](SARA_v3/README_v3.md)와 [v3 설계 기준](docs/v3-integration-design.md)을 참고하세요.

### 운영 전 확인 (사용자 책임)

v3 승격은 코드 공개 범위입니다. 실제로 운영하려면 아래를 직접 확인하세요. 세부 목록은 [승격 기록](docs/v3-promotion-status.md#운영-전-사용자-책임)에 있습니다.

- 사용할 provider로 live smoke 실행: `SARA_V3_LIVE_SMOKE=1 python -m pytest -q SARA_v3/tests/test_live_provider_smoke.py`
- 웹 검색·MCP·Crawl4AI 사용 조건과 외부로 보내도 되는 대화 범위
- 영속 ledger 저장 위치의 권한·백업·보존, reviewer 인증 방식
- egress 통제(강한 SSRF·응답 크기 보호)
- 품질·비교 우위를 주장하려면 독립 평가

### Python 호스트와 Co-thoughts 연동

Python 호스트는 루트의 `sara_runtime.process_v3_dialogue_turn(payload)`로 v3를 호출합니다. 위의 `SARA_*` 환경변수로 provider가 구성됩니다.

Co-thoughts는 `SARAv3Connection`으로 SARA v3를 별도 프로세스(`python -m SARA_v3.cli`)에서 호출하고, 반환된 assessment envelope을 다음 backend 호출에 전달합니다(ydonchoi/co-thoughts#1). 두 저장소에 이름이 같은 모듈이 있어 같은 프로세스에서 import하지 않습니다. 이 연결의 live 왕복은 사용자 책임으로 남아 있습니다.

### 이전 버전 경로 (호환용)

새 통합에는 v3를 사용하세요. 아래 경로는 기존 사용자를 위한 호환 경로입니다.

- **v2.5 대화 CLI:** `SARA_v2.5/dialogue_runner.py` — 판단용 `SARA_LLM_*`와 별도 source verifier를 사용합니다. [v2.5 안내](SARA_v2.5/README_v2.5.md)
- **v2.5 호스트 진입점:** `sara_runtime.process_dialogue_turn_from_environment(payload)` — `SARA_VERIFICATION_PROVIDER=module:callable`로 source verifier를 연결하며, 비어 있으면 fail-closed provider가 사용되어 출처 검증 상태는 `UNVERIFIED`로 유지됩니다.
- **JSONL 실행기:** `python SARA_v2.5/executor.py --provider package.module` — provider module 계약은 [실행기 안내](SARA_v2.5/EXECUTOR.md)에 있습니다.

LLM judgment와 source verification은 서로 다른 provider이며, 둘 다 구성됐다는 사실만으로 claim의 진실성이 보장되지는 않습니다. provider 자격 증명은 호스트 환경에서 관리하세요.

## 설계상 경계

- **판단은 근거가 아닙니다.** LLM의 추론·분류 결과는 evidence나 검증 상태로 승격되지 않습니다.
- **출처 검색은 검증이 아닙니다.** 검색 결과나 DOI 서지정보만으로 원문 내용 또는 주장의 진실성을 확인한 것으로 보지 않습니다.
- **검증 상태와 진실성은 별개입니다.** 각 결과는 어떤 자료와 범위를 확인했는지 함께 해석해야 합니다.
- **구조 검사와 의미 검토는 별개입니다.** v2.4 논리 감사는 명시적으로 입력된 argument graph를 구조적으로 검사합니다. 자유 형식 문장의 논리를 자동으로 완전 판정하지 않습니다.
- **시뮬레이션은 재현이 아닙니다.** 가상 데이터 실행은 원 연구 결과의 확인 근거가 아닙니다.
- **실서비스 운영 근거는 별도입니다.** canonical 승격은 운영 준비를 뜻하지 않습니다. 배포 provider, 지속 저장소, 접근 제어, 독립 benchmark와 host live 연동은 운영자가 따로 확인해야 합니다.

## 저장소 구성

```text
SARA_v3/      canonical 통합 대화 runtime, web/MCP/Crawl4AI source adapter, assessment contract, 영속 ledger
SARA_v2.5/    JEV 판단, claim identity·conflict, provenance ledger, commit gate, 호환 CLI·executor
SARA_v2.4/    이전 canonical epistemic baseline과 구조화 논리 감사
SARA_v2.3/    호환 실행 계약과 evidence 검증 모듈
LEGACY/       v2.1–v2.2 보존 문서
docs/         v3 설계·승격 기록, 회귀 기준, 버전별 검토 기록
tests/        저장소 수준 계약 테스트
sara_runtime.py
              Python 호스트용 진입점 (v3, v2.5, v2.3/v2.4 호환)
requirements-test.txt
              테스트 의존성
requirements-crawl4ai.txt
              선택 의존성 (Crawl4AI)
```

## 설명 출력 형식

설명·보고서·검토 자료의 표현 매체 선택과 기술문서 작성 원칙은 [설명 출력 프로토콜](docs/explanation-output-protocol-v0.1.md)을 참고하세요. 이 문서는 표현 계층의 지침이며 SARA 런타임의 자동 시각화나 영상 생성을 구현하지 않습니다. SARA의 evidence, provenance, verification status 및 commit 계약은 기존 v3 기준을 그대로 따릅니다.

## 문서와 테스트

현재 상태의 기준 문서는 이 README, [v3 승격 기록](docs/v3-promotion-status.md), [v3 설계 기준](docs/v3-integration-design.md)입니다. `SARA_v2.3/`–`SARA_v2.5/`와 `docs/v2.5-*` 문서는 각 버전의 계약과 당시 검토·승격 기록을 보존합니다. 그 안의 "현재" 표현은 작성 시점 기준이므로 지금 상태와 혼동하지 마세요.

**현재 기준**
- [v3 안내](SARA_v3/README_v3.md)
- [v3 설계 기준](docs/v3-integration-design.md)
- [v3 canonical 승격 기록](docs/v3-promotion-status.md)
- [v2.4 regression baseline 정책](docs/v2.4-regression-baseline.md)
- [엔지니어링 원칙](docs/engineering-principles.md)
- [Crawl4AI 구현 보고서](docs/crawl4ai-implementation-report.md)

**버전별 기록**
- [v2.4 상세 설명](SARA_v2.4/README_v2.4.md)
- [v2.5 상세 설명과 사용 예시](SARA_v2.5/README_v2.5.md), [JSONL 실행기 계약](SARA_v2.5/EXECUTOR.md), [테스트 환경 및 명령](SARA_v2.5/TESTING.md)
- [v2.5 operational trial 기록](SARA_v2.5/CANONICAL_PROMOTION_STATUS.md), [v2.5 승격 준비 기준](docs/v2.5-promotion-readiness-plan.md)
- [독립 검증 matrix (2026-10-25 시점)](docs/independent-verification-matrix.md)

Pull request에는 변경한 계약에 대한 회귀 테스트를 포함하고, CI 결과를 확인하세요. 전체 테스트 명령은 `python -m pytest -q`입니다. 로컬 테스트 통과는 live provider 연결이나 운영 환경 검증을 의미하지 않습니다.

## 라이선스

이 변경이 배포되는 revision부터 저장소의 원본 코드·프롬프트·스키마·문서·테스트 자료는 별도 표기가 없는 한 **MIT License**를 따릅니다. 상업적 이용, 수정, 재배포가 가능하며, 재배포 시 저작권 및 라이선스 고지를 포함해야 합니다. 제3자 자료와 의존성은 각자의 라이선스를 따릅니다. 자세한 범위와 전문은 [LICENSE](LICENSE)를 확인하세요.

이전 revision은 당시 표시된 **CC BY-NC 4.0** 조건으로 이미 허가된 이용 권리를 유지합니다. 이 전환은 이전 배포본에 부여된 라이선스를 철회하지 않습니다.
