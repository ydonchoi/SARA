# SARA

**Evidence-Centered Research Analysis & Epistemic Verification System**

SARA는 연구 주장을 근거·방법·출처와 연결해 검토하고, 검증 상태와 불확실성을 분리해 기록하는 연구 분석 시스템입니다. 저장소에는 버전별 설계 문서, Python 실행 모듈, 계약 테스트가 함께 있습니다.

> **현재 상태:** v2.4는 canonical verification baseline입니다. v2.5는 operational trial, v3는 통합 런타임 구현 후보입니다. v3의 live provider, durable host/ledger 운영, 독립 평가와 canonical 승격 근거는 아직 확인되지 않았습니다.

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
| v1.0 | 초기 연구 분석 프레임워크 | 보존된 이력 |
| v2.1 | 분석 모듈화 | 보존된 이력 |
| v2.2 | 의존성·로딩·계약 관리 | 보존된 이력 |
| v2.3 | 실행 경계, evidence 검증, 재현/시뮬레이션 구분 | 호환성과 실행 기반 |
| **v2.4** | Claim/premise 상태, provenance, attribution, temporal context, 구조화 argument audit | **canonical baseline** |
| **v2.5** | Claim identity, evidence conflict, provenance ledger, selective reverification, 내부 판단 경로와 CLI | **operational trial; 승격·운영 준비 미확인** |
| **v3.0.0** | v2.3~v2.5 통합 대화 런타임, 외부 LLM judgment/응답, 기본 웹 검색, 선택 MCP, SARA assessment envelope | **구현 후보; release gate 대기** |

v2.5의 provider-neutral 판단 adapter는 OpenAI API, Anthropic Messages, Gemini `generateContent`, OpenAI-compatible endpoint 형식을 지원합니다. 저장소 테스트는 stub transport를 사용하며, 실제 계정·API key·서비스 연결이 설정됐다는 뜻은 아닙니다. v3는 이 경로에 Kimi(OpenAI-compatible JSON mode)를 포함하며, schema 결과는 응답 후 로컬 검증합니다. 소비자용 ChatGPT, Claude, Gemini 앱의 내부 대화 흐름에도 자동 연결되지 않습니다.

## 빠른 시작

### 요구 사항

- Python 3.12 권장
- 테스트 실행에는 저장소 루트의 `requirements-test.txt`에 고정된 pytest가 필요합니다.
- 2026-10-25 확인: Python 3.13.9 / pytest 8.4.2에서 전체 테스트 **453 passed**.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-test.txt
python -m pytest -q
```

macOS/Linux에서는 가상환경을 `. .venv/bin/activate`로 활성화합니다. 별도 Python 패키지 배포물은 제공하지 않습니다.

### v2.5 대화 입력 실행

한 번의 대화 turn을 처리하는 CLI는 `SARA_v2.5/dialogue_runner.py`입니다. 입력에는 `request_id`, `conversation_id`, `turn_id`, `content`, 그리고 명시적인 `claim_candidates`가 필요합니다. 판단용 LLM은 환경변수로 설정하고, 실제 source 검증기는 별도 provider callable로 주입합니다.

```powershell
$env:SARA_LLM_PROVIDER = "openai" # anthropic, gemini, openai_compatible도 지원
$env:SARA_LLM_MODEL = "your-model-id"
$env:SARA_LLM_API_KEY = "your-api-key"
Get-Content .\turn.json -Raw | python .\SARA_v2.5\dialogue_runner.py `
  --model-revision configured-provider
```

API key를 요청 JSON, 소스 파일, 커밋에 넣지 마세요. source verifier를 설정하지 않으면 결과는 `UNVERIFIED`로 남습니다. 입력 예시와 전체 provider 설정은 [v2.5 사용 안내](SARA_v2.5/README_v2.5.md)를 참고하세요.

### v3 통합 대화 실행

`SARA_v3/cli.py`는 v2.5 JEV judgment를 외부 LLM으로 실행하고, 기본 Brave 웹 검색으로 자료를 찾은 뒤 SARA가 evidence 관계·접근 범위·충돌을 assessment envelope으로 반환합니다. 그 envelope은 후속 LLM 응답에 구조화 맥락으로 전달됩니다. 검색 snippet만으로 `VERIFIED`가 되지 않으며, `VERIFIED` proposal을 내려면 설정한 신뢰 도메인의 원문과 검증된 supporting span이 필요합니다. 모든 결과는 `PROPOSED`이고, 사람 검토와 v2.5 commit gate 전에는 확정 상태가 아닙니다.

```powershell
$env:SARA_LLM_PROVIDER = "openai" # anthropic, gemini, kimi, openai_compatible
$env:SARA_LLM_MODEL = "your-model-id"
$env:SARA_LLM_API_KEY = "your-api-key"
$env:BRAVE_SEARCH_API_KEY = "your-brave-search-key"
$env:SARA_TRUSTED_SOURCE_DOMAINS = "example.gov,example.org"
Get-Content .\turn.json -Raw | python -m SARA_v3.cli
```

MCP는 자동 탐색하지 않습니다. 호스트의 인증된 MCP client를 `SARA_MCP_CALL_TOOL=module:call_tool`로 연결하고, 사용할 tool 이름을 `SARA_MCP_SEARCH_TOOL`/`SARA_MCP_FETCH_TOOL`에 명시해야 합니다. Fetch tool에는 `SARA_MCP_FETCH_ALLOWED_DOMAINS`가 필수입니다. 현재 v3 ledger 기본값은 process-local memory이며, 영속 ledger adapter는 호스트가 주입해야 합니다. 상세 계약·환경변수·미충족 출시 gate는 [v3 안내](SARA_v3/README_v3.md)와 [v3 설계 및 검토 기록](docs/v3-integration-design.md)을 참고하세요.

Python 호스트(Co-thoughts 포함)는 루트의 `sara_runtime.process_dialogue_turn_from_environment(payload)`를 호출할 수 있습니다. 이 진입점은 위의 `SARA_LLM_*` 설정으로 판단 provider를 구성하고, 선택적으로 아래처럼 source verifier를 연결합니다.

```powershell
$env:SARA_VERIFICATION_PROVIDER = "my_sara_provider:verify_claim"
```

판단용 `SARA_LLM_*` 설정은 필수이며, 누락 시 실행이 명시적 구성 오류로 종료됩니다. 검증 callable은 SARA 요청 mapping을 받고 provider 결과 mapping을 반환해야 합니다. `SARA_VERIFICATION_PROVIDER`가 비어 있으면 fail-closed provider가 사용되어 출처 검증 상태는 `UNVERIFIED`로 유지됩니다. LLM judgment와 source verification은 서로 다른 provider이며, 둘 다 구성됐다는 사실만으로 claim의 진실성이 보장되지는 않습니다. provider 자격 증명은 호스트 환경에서 관리하세요.

### JSONL 실행기

`SARA_v2.5/executor.py`는 provider module을 명시해 여러 요청을 한 줄에 하나씩 처리하는 host-neutral 실행기입니다.

```sh
python SARA_v2.5/executor.py --provider package.module
```

provider module 계약, 입력 형식, 결과 상태는 [실행기 안내](SARA_v2.5/EXECUTOR.md)에 있습니다. 판단 callable과 source verification callable이 필요하며, 실행기만으로 provider나 검증 서비스가 구성되지는 않습니다.

## 설계상 경계

- **판단은 근거가 아닙니다.** LLM의 추론·분류 결과는 evidence나 검증 상태로 승격되지 않습니다.
- **출처 검색은 검증이 아닙니다.** 검색 결과나 DOI 서지정보만으로 원문 내용 또는 주장의 진실성을 확인한 것으로 보지 않습니다.
- **검증 상태와 진실성은 별개입니다.** 각 결과는 어떤 자료와 범위를 확인했는지 함께 해석해야 합니다.
- **구조 검사와 의미 검토는 별개입니다.** v2.4 논리 감사는 명시적으로 입력된 argument graph를 구조적으로 검사합니다. 자유 형식 문장의 논리를 자동으로 완전 판정하지 않습니다.
- **시뮬레이션은 재현이 아닙니다.** 가상 데이터 실행은 원 연구 결과의 확인 근거가 아닙니다.
- **실서비스 운영 근거가 필요합니다.** 배포 provider, 지속 저장소, 접근 제어, 독립 benchmark와 host 연동은 별도 평가 대상입니다.

## 저장소 구성

```text
SARA_v2.3/   호환 실행 계약과 evidence 검증 모듈
SARA_v2.4/   canonical epistemic baseline과 구조화 논리 감사
SARA_v2.5/   trial runtime, provider adapter, executor, 재검증·승격 프로토타입
SARA_v3/    통합 대화 runtime 후보, web/MCP source adapter, assessment contract
SARA_v1.0/   초기 연구 분석 산출물
SARA_v2.1/   모듈형 architecture 문서
SARA_v2.2/   dependency와 loading architecture 문서
README.md    저장소 개요와 시작 안내
requirements-test.txt
              테스트 의존성
```

## 문서와 테스트

- [v2.4 상세 설명](SARA_v2.4/README_v2.4.md)
- [v2.5 상세 설명과 사용 예시](SARA_v2.5/README_v2.5.md)
- [JSONL 실행기 계약](SARA_v2.5/EXECUTOR.md)
- [테스트 환경 및 명령](SARA_v2.5/TESTING.md)
- [현재 v2.5 operational trial 상태](SARA_v2.5/CANONICAL_PROMOTION_STATUS.md)
- [v2.5 승격 준비 기준](docs/v2.5-promotion-readiness-plan.md)
- [v2.4 regression baseline 정책](docs/v2.4-regression-baseline.md)
- [v3 구현·통합 설계 기준](docs/v3-integration-design.md)

Pull request에는 변경한 계약에 대한 회귀 테스트를 포함하고, CI 결과를 확인하세요. 전체 테스트 명령은 `python -m pytest -q`입니다. 위의 로컬 테스트 통과는 live provider 연결이나 v3 canonical 승격 gate 통과를 의미하지 않습니다.

## 라이선스

이 변경이 배포되는 revision부터 저장소의 원본 코드·프롬프트·스키마·문서·테스트 자료는 별도 표기가 없는 한 **MIT License**를 따릅니다. 상업적 이용, 수정, 재배포가 가능하며, 재배포 시 저작권 및 라이선스 고지를 포함해야 합니다. 제3자 자료와 의존성은 각자의 라이선스를 따릅니다. 자세한 범위와 전문은 [LICENSE](LICENSE)를 확인하세요.

이전 revision은 당시 표시된 **CC BY-NC 4.0** 조건으로 이미 허가된 이용 권리를 유지합니다. 이 전환은 이전 배포본에 부여된 라이선스를 철회하지 않습니다.
