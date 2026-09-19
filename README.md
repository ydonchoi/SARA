# SARA
## Evidence-Centered Research Analysis & Simulation System

SARA (**Senior Academic Research Architect**)는 학술 연구를 단순히 요약하는 것을 넘어, 연구의 **Claim → Evidence → Method → Verification → Inference → Uncertainty** 구조를 추적하고, 필요할 경우 연구 방법의 재현 가능성과 시뮬레이션 가능성을 별도로 검토하도록 설계된 연구 분석 시스템이다.

이 저장소는 SARA의 **v1.0부터 v2.3까지의 발전 과정과 버전별 산출물을 함께 보존**한다.

---

## 1. Version Overview

| Version | 핵심 변화 | 주요 구조 |
|---|---|---|
| **v1.0** | 연구 문헌 분석을 위한 초기 통합 프레임워크 | 연구요약 · 방법론 · 인사이트 · 논의/리뷰 · 후속 연구 |
| **v2.1** | 단일 Master Prompt를 계층형 모듈 구조로 분해 | MASTER · CORE · ROUTER · AGENTS · ANALYSIS · OUTPUT · SCHEMA |
| **v2.2** | 모듈 간 실행 관계와 의존성 관리 도입 | v2.1 + SYSTEM / Dependency & Loading Architecture |
| **v2.3** | 구조적 결함 수정 + 검증 계층 분리 + 재현/시뮬레이션 에이전트 도입 | v2.2 + A6 Simulator/Reproducer + Verification Layer Separation |

> 버전별 폴더는 서로 다른 설계 단계를 보존하기 위한 **versioned snapshots**이다. 최신 구조만을 사용해야 하는 경우 `SARA_v2.3/`을 기준으로 한다.

---

# 2. Evolution

## v1.0 — Initial Research Analysis Framework

SARA v1.0은 연구 문헌을 분석하기 위한 초기 형태로, 연구 결과를 여러 분석 산출물로 분리하여 관리하는 접근을 취했다.

### 주요 산출물

- 연구 요약
- 연구 방법론 심화
- 인사이트
- 논의 및 리뷰
- 후속 연구 주제 발굴
- 후속 연구 계획

### v1.0의 성격

v1.0은 현재의 모듈형 시스템이라기보다 **연구 분석 작업을 위한 통합형 분석 프레임워크**에 가깝다.

현재 저장소에서는 다음 경로에 보존되어 있다.

```text
SARA_v1.0/
├─ 1. 연구요약_1229
├─ 2. 연구방법론 심화_1229.methodology
├─ 3. 인사이트_1229
├─ 4. 논의(리뷰)_1229
├─ 4-1. 후속 연구 주제 발굴 심층보고서_1229
└─ 후속 연구 계획서_1229
```

---

# 3. v2.1 — Modular Architecture

v2.1에서는 SARA가 하나의 거대한 Master Prompt에 의존하는 방식에서 벗어나 **계층형 모듈 시스템**으로 재설계되었다.

핵심 분석 구조:

> **Claim → Evidence → Method → Verification → Inference → Uncertainty**

### Architecture

```text
SARA_v2.1/
├─ 00_MASTER/
├─ 01_CORE/
├─ 02_ROUTER/
├─ 03_AGENTS/
├─ 04_ANALYSIS/
├─ 05_OUTPUT/
└─ 06_SCHEMA/
```

### 주요 구성

#### MASTER
시스템의 기본 정체성, 원칙, 실행 규칙을 정의한다.

#### CORE
- Identity
- Core Principles
- Source Policy
- Uncertainty Policy

를 담당한다.

#### ROUTER
사용자 요청을 적절한 Agent로 연결한다.

| 요청 | Agent |
|---|---|
| `/요약` | A1 Summarizer |
| `/검증` | A2 Investigator |
| `/방법론` | A3 Methodologist |
| `/인사이트` | A4 Visionary |
| `/비평` | A5 Reviewer |
| `/통합` | Full Pipeline |

#### AGENTS

- **A1 Summarizer** — 연구 구조 복원
- **A2 Investigator** — 인용 및 근거 검증
- **A3 Methodologist** — 방법론 정합성 감사
- **A4 Visionary** — 연구 공백 및 후속 연구 방향
- **A5 Reviewer** — 종합 비평

#### ANALYSIS

연구 매핑, citation audit, claim-evidence analysis, methodology audit, critical review, research gap 등의 분석 절차를 독립 모듈로 관리한다.

#### SCHEMA

연구, 주장, evidence를 구조화된 데이터 모델로 관리한다.

### v2.1의 핵심 설계 원칙

- 모든 파일을 매번 읽지 않는다.
- 필요한 모듈만 최소한으로 로드한다.
- 확인되지 않은 내용을 임의로 채우지 않는다.
- 원문 주장과 SARA의 해석을 구분한다.
- 사실과 추론을 구분한다.
- 실제 재현과 시뮬레이션을 구분한다.
- 연구 유형에 맞지 않는 변수를 강제하지 않는다.
- 명시적인 근거 없이 정확도·재현율·신뢰도 등의 수치를 생성하지 않는다.

---

# 4. v2.2 — Dependency & Loading Architecture

v2.2에서는 v2.1의 **논리적 모듈 분리**를 한 단계 확장하여, 모듈들이 실제 실행 과정에서 어떻게 연결되고 로드되는지를 명시하기 시작했다.

### 핵심 변화

> **v2.1: 모듈을 분리했다.**  
> **v2.2: 모듈의 실행 관계까지 명시했다.**

### 추가된 SYSTEM Layer

```text
SARA_v2.2/
├─ 00_MASTER/
├─ 01_CORE/
├─ 02_ROUTER/
├─ 03_AGENTS/
├─ 04_ANALYSIS/
├─ 05_OUTPUT/
├─ 06_SCHEMA/
└─ 07_SYSTEM/
   ├─ dependency_map.md
   ├─ loading_rules.md
   ├─ module_contracts.md
   ├─ validation_rules.md
   └─ architecture_audit.md
```

### 추가된 개념

#### 1. Dependency Map
각 route와 module이 요구하는 dependency를 명시한다.

#### 2. Loading Rules
필요한 파일만 로드하는 **Minimal Loading**을 실행 규칙으로 구체화한다.

#### 3. Module Contracts
각 Agent가 요구하는 입력과 산출물을 계약 형태로 정의한다.

#### 4. Validation Rules
모듈 실행 결과가 정의된 구조와 규칙을 따르는지 검증한다.

#### 5. Architecture Audit
시스템 자체의 구조적 결함을 별도로 감사한다.

### v2.2의 핵심 통찰

> **파일이 존재하는 것과 시스템이 파일을 사용할 수 있는 것은 다르다.**

따라서 연구 내용의 정확성뿐 아니라 **시스템 내부 dependency, loading, contract, validation 자체**가 분석 대상이 되었다.

---

# 5. v2.3 — Research Analysis & Simulation System

v2.3은 v2.2 Architecture Audit에서 확인된 구조적 문제를 수정하고, 연구 방법의 **실행적 재현/시뮬레이션**을 별도의 Agent로 분리한 버전이다.

### 핵심 변화

1. MASTER ↔ SYSTEM 순환 dependency 제거
2. Instruction Hierarchy 단일화
3. Module Contract 기계화
4. Agent → Schema → Output 매핑 명시
5. `/통합` wildcard dependency 제거
6. `system_verification` / `research_verification` 분리
7. **A6 Simulator/Reproducer 신설**
8. External Citation Verification 분리
9. 전 route에 조건부 Confession trigger 확대

---

## 5.1 v2.3 Architecture

```text
SYSTEM (meta/control layer)
        │
        ▼
MASTER
        │
        ▼
CORE
        │
        ▼
ROUTER
        │
        ├──────────────┐
        ▼              ▼
     AGENTS         ANALYSIS
        │              │
        └──────┬───────┘
               ▼
             SCHEMA
               │
               ▼
             OUTPUT
```

SYSTEM은 콘텐츠 모듈이 아니라 **dependency / loading / validation / contract를 통제하는 meta/control layer**로 정의된다.

따라서 v2.2에서 발견된 `MASTER → SYSTEM → MASTER` 순환을 제거하고 단방향 구조를 명시한다.

---

# 6. Verification Architecture

v2.3의 중요한 변화는 **시스템 자체의 검증과 연구 내용의 검증을 분리한 것**이다.

### System Verification

시스템이 올바르게 구성되고 실행되는지를 확인한다.

```yaml
system_verification:
  dependency_resolution:
  module_access:
  loading_completeness:
  contract_compliance:
```

### Research Verification

연구 내용 자체가 어느 정도 확인되는지를 평가한다.

```yaml
research_verification:
  source_access:
  methodology_evidence:
  citation_verification:
  claim_evidence_fit:
  reproduction_status:
```

### 핵심 규칙

> **SYSTEM verification 실패가 RESEARCH verification 실패를 자동으로 의미하지 않는다.**

예를 들어 특정 SARA 시스템 파일에 접근하지 못했다는 사실과 논문의 연구방법이 원문에서 확인되는지는 서로 다른 검증 층위다.

---

# 7. A6 — Simulator / Reproducer

v2.3에서 가장 큰 기능적 확장 중 하나다.

기존 A3 Methodologist가 **방법론을 감사(Audit)**했다면, A6는 방법론을 **실행 관점에서 재현/시뮬레이션(Execution)**한다.

| | A3 Methodologist | A6 Simulator/Reproducer |
|---|---|---|
| 관점 | Audit | Execution |
| 핵심 질문 | 이 방법론은 타당한가? | 이 방법론을 실제/가상 데이터로 실행할 수 있는가? |
| 산출물 | Methodology Audit | Dummy Data + Analysis Code + Simulation Report |
| 원자료 | 필수 아님 | Full reproduction에는 필요 |
| 원자료가 없을 때 | 방법론 평가 | Simulated Reproduction |
| 검증 근거 | 방법론 분석 | **A2의 verification evidence로 인정하지 않음** |

### Reproduction ≠ Simulation

v2.3은 이 구분을 명시적인 시스템 원칙으로 채택한다.

- **Full Reproduction** — 원자료와 실제 절차를 이용한 재현
- **Simulated Reproduction** — 논문의 변수구조와 분석방법을 반영한 가상 데이터 실행
- **Reproduction Unavailable** — 필요한 자료가 없어 실행 자체가 불가능한 경우

시뮬레이션 결과는 실제 논문의 결과를 검증한 것으로 취급하지 않는다.

---

# 8. v2.3 Agent Architecture

| Agent | 역할 | 주요 산출물 |
|---|---|---|
| A1 | Structural Research Summarizer | 연구 구조 요약 |
| A2 | Citation & Evidence Verifier | Verification Report |
| A3 | Methodology Auditor | Methodology Audit |
| A4 | Research Gap & Vision Generator | Research Gap / Vision |
| A5 | Critical Reviewer | Critical Review |
| **A6** | **Simulator / Reproducer** | **Simulation Report** |

### Agent → Schema → Output

```text
A1 → research_schema → agent_report
A2 → claim_schema + evidence_schema → verification
A3 → research_schema + methodology_audit → agent_report
A4 → uncertainty + research_gap → agent_report
A5 → claim_schema + evidence_schema → agent_report
A6 → research_schema + simulation_schema → simulation_report
```

이 명시적 mapping을 통해 Agent가 어떤 Schema를 사용하고 어떤 Output으로 연결되는지 추적할 수 있다.

---

# 9. v2.3 Routing

| Trigger | Route |
|---|---|
| `/요약` | A1 |
| `/검증` | A2 |
| `/방법론` | A3 |
| `/재현` | A6 |
| `/시뮬레이션` | A6 |
| `/인사이트` | A4 |
| `/비평` | A5 |
| `/통합` | Default Full Pipeline |

A6는 기본 통합 pipeline에 무조건 포함되지 않는다. 사용자가 재현 또는 시뮬레이션을 요청한 경우에 선택적으로 활성화한다.

---

# 10. Default Workflow

```text
1. Research Mapping
        ↓
2. Summary
        ↓
3. Verification
        ↓
4. Methodology Audit
        ↓
5. [Optional] Reproduction / Simulation
        ↓
6. Claim–Evidence Matrix
        ↓
7. Critical Review
        ↓
8. Research Gap / Vision
        ↓
9. Uncertainty Audit
        ↓
10. Executive Synthesis
```

핵심 원칙은 **No Blind Loading**이다. 요청과 관계없는 모듈은 불필요하게 실행하지 않는다.

---

# 11. Information Boundary

SARA는 정보의 인식론적 상태를 명시적으로 구분한다.

| Status | 의미 |
|---|---|
| `VERIFIED` | 직접 확인됨 |
| `PARTIALLY VERIFIED` | 일부 확인됨 |
| `INFERRED` | 근거로부터 합리적으로 추론 |
| `HYPOTHESIZED` | 검증 전 가설 |
| `UNVERIFIED` | 확인할 수 없음 |
| `CONTRADICTED` | 신뢰할 수 있는 근거와 충돌 |

또한 내용의 성격을 다음과 같이 분리한다.

- **FACT**
- **INFERENCE**
- **HYPOTHESIS**
- **SPECULATION**

---

# 12. Source & Evidence Policy

기본적인 source hierarchy:

1. **Primary Source** — 분석 대상 원문
2. **Official / Original Academic Source**
3. **Review / Secondary Academic Source**
4. **General Web**

외부 검색은 다음과 같은 경우에 한해 수행한다.

- 인용문헌의 존재 및 서지정보 확인
- 원문만으로 사실 확인이 불가능한 경우
- 최신 연구·정책·통계 확인
- 경쟁 가설 또는 반대 증거 확인
- 사용자가 외부 검증을 요청한 경우

핵심 verification sequence:

```text
Existence
    ↓
Bibliographic Accuracy
    ↓
Content
    ↓
Citation Fit
    ↓
Evidence Strength
```

---

# 13. Output Principles

SARA의 출력은 다음 원칙을 따른다.

- 기본 언어: 한국어
- 핵심 academic terminology: English 병기
- Markdown / Obsidian-compatible 구조
- 외부 자료는 가능한 경우 APA 7 reference로 기록
- 핵심 주장과 evidence의 관계를 명시
- 확인되지 않은 내용을 확인된 사실처럼 표현하지 않음
- 저자의 주장과 SARA의 해석을 분리
- 실제 재현과 시뮬레이션을 분리
- 근거 없는 정량 점수를 생성하지 않음
- 불확실성을 숨기지 않고 별도로 기록

---

# 14. Versioned Directory

현재 저장소의 주요 버전 보존 구조:

```text
SARA/
├─ SARA_v1.0/
├─ SARA_V2.1/
├─ SARA_v2.2/
├─ SARA_v2.3/
└─ legacy
```

### Latest

**v2.3**

`SARA_v2.3/`에는 다음 계층이 포함된다.

```text
00_MASTER
01_CORE
02_ROUTER
03_AGENTS
04_ANALYSIS
05_OUTPUT
06_SCHEMA
07_SYSTEM

SARA_v2.3_Master.md
SARA_v2.3_Restructure.md
README_v2.3.md
```

---

# 15. Version History

| Version | Architectural Focus | Major Addition |
|---|---|---|
| **v1.0** | Integrated research analysis | 연구요약·방법론·인사이트·리뷰·후속 연구 |
| **v2.1** | Modularization | Master / Core / Router / Agents / Analysis / Output / Schema |
| **v2.2** | Systemization | Dependency Map / Loading Rules / Module Contracts / Validation |
| **v2.3** | Verification & Execution | Verification Layer Separation / A6 / Simulation / Contract Mapping |

---

## 16. Design Philosophy

SARA의 발전은 단순한 기능 추가의 연속이라기보다 다음과 같은 **구조적 이동**으로 볼 수 있다.

```text
v1.0
연구를 분석한다
        ↓
v2.1
분석 과정을 모듈화한다
        ↓
v2.2
모듈의 실행 관계를 관리한다
        ↓
v2.3
시스템 검증과 연구 검증을 분리하고
방법론의 실행 가능성까지 다룬다
```

즉, SARA는

> **Research Analysis → Modular Research Architecture → Executable Research Architecture → Evidence-Centered Analysis & Simulation**

의 방향으로 확장되었다.

---

## Repository

https://github.com/ydonchoi/SARA

## Current Version

**SARA v2.3**
