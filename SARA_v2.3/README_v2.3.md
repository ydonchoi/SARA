# SARA v2.3 — Evidence-Centered Research Analysis & Simulation System

SARA v2.3은 v2.2의 Dependency & Loading Architecture에서 드러난 구조적 결함(순환 dependency,
비기계적 module contract, verification 층위 미분리)을 해소하고, 연구 방법을 실제로
**시뮬레이션/재현(Simulation/Reproduction)** 할 수 있는 독립 에이전트(A6)를 추가한 버전이다.

## Architecture

```text
SARA_v2.3/
├─ 00_MASTER/
│  └─ 00_SARA_MASTER.md              # Instruction Hierarchy 단일화, Verification 2계층 정의
├─ 01_CORE/                           # identity / principles / source_policy / uncertainty (변경 없음)
├─ 02_ROUTER/                         # trigger_map / workflow (변경 없음, /재현 트리거만 추가)
├─ 03_AGENTS/
│  ├─ A1_summarizer.md
│  ├─ A2_investigator.md
│  ├─ A3_methodologist.md            # Audit 관점 — 실행/코드 생성 금지 명시
│  ├─ A4_visionary.md
│  ├─ A5_reviewer.md
│  └─ A6_simulator.md                # ★ v2.3 신규 — Execution 관점, Reproduction ≠ Simulation
├─ 04_ANALYSIS/                       # 변경 없음
├─ 05_OUTPUT/
│  ├─ agent_report.md                # Verification Status 2계층 표 형식으로 갱신
│  ├─ verification.md                # External Citation Verification 섹션 신설
│  ├─ confession.md                  # System Access Status 분리, Reproduction Note 신설
│  ├─ executive.md                   # Reproduction/Simulation Summary 섹션 신설
│  └─ simulation_report.md           # ★ v2.3 신규 — A6 전용 출력 템플릿
├─ 06_SCHEMA/
│  ├─ research_schema.md             # taxonomy_mid/micro/sub, methodology_sub, main_tools/technique 정식 필드화
│  ├─ claim_schema.md                # verification_layer, inference_basis, strength_alignment, external_citation_verification 추가
│  └─ evidence_schema.md             # verification_layer, evidence_strength, usable_as_verification_evidence 추가
└─ 07_SYSTEM/
   ├─ dependency_map.md              # MASTER↔SYSTEM 순환 제거, /통합 wildcard→명시적 closure, /재현 라우트 추가
   ├─ loading_rules.md               # Conflict Resolution 순서 MASTER와 단일화, Circular Dependency 방지 규칙(§7) 신설
   ├─ module_contracts.md            # A1~A6 전 계약 완전 구현 + Agent→Schema→Output 매핑 표
   ├─ validation_rules.md            # §11 Verification Layer Separation, §12 Circular Dependency 재발 방지 신설
   └─ architecture_audit.md          # (v2.2 감사 기록 유지, v2.3 감사 결과는 별도 로그로 누적)
```

## v2.2 → v2.3

### v2.2의 한계 (Architecture Audit 결과)

| 항목 | 판정 |
|---|---|
| SYSTEM ↔ MASTER 순환 dependency | 🔴 FAIL |
| Module Contract 비기계적 정의 | 🟡 PARTIAL |
| Agent Output ↔ Schema 매핑 부재 | 🟡 PARTIAL |
| `/통합` wildcard 해석 불명확 | 🟡 PARTIAL |
| System 파일 접근 실패가 연구결과 검증 상태에 전파 | 🔴 개선 필요 |

### v2.3의 조치

1. **SYSTEM Layer 위상 재정의** — SYSTEM을 MASTER 이하 전 계층을 통제하는 control authority로 재정의하고,
   SYSTEM 파일이 더 이상 MASTER를 `requires`로 선언하지 않도록 하여 순환을 제거했다.
2. **Verification 2계층 분리** — `system_verification`(dependency/module access/loading/contract)과
   `research_verification`(source access/methodology/citation/claim fit/reproduction)을 독립 상태로 분리하고,
   전자의 실패가 후자에 자동 전파되지 않도록 규칙화했다.
3. **Module Contract 완전 구현** — A1~A6 전 에이전트에 requires/inputs/process/outputs/must_not/status_vocabulary를
   실제로 채워, "설계 지침" 수준에서 "검증 가능한 interface"로 전환했다.
4. **Agent → Schema → Output 명시적 매핑** — 어떤 agent가 어떤 schema를 참조해 어떤 output으로 귀결되는지
   표로 고정하여 Schema Consistency 검사를 기계적으로 수행할 수 있게 했다.
5. **`/통합` wildcard 제거** — Default Workflow 순서에 맞춘 명시적 dependency closure로 대체했다.
6. **A6 Simulator/Reproducer 신설** — `/방법론`(A3, Audit)과 명확히 분리된 독립 에이전트로, 논문의 변수
   구조를 반영한 더미 데이터 생성과 분석 재현 코드를 작성한다. **Reproduction ≠ Simulation** 원칙에 따라
   A6의 출력은 evidence_schema의 `usable_as_verification_evidence: false`로 고정되어 A2의 검증 근거로
   사용될 수 없다 (epistemic 순환 검증 방지).
7. **External Citation Verification 분리** — 논문 내부 주장 검증(`verification_status`)과 인용문헌 자체의
   실존·서지정보 검증을 별도 필드로 분리하고, 전용 신규 상태값 `NOT_COMPLETED`를 이 필드 안에서만 허용했다.

## 실행 개념 (v2.3)

```text
User Request
    ↓
MASTER (Instruction Hierarchy 단일화)
    ↓
ROUTER (/요약 /검증 /방법론 /재현 /인사이트 /비평 /통합)
    ↓
Dependency Resolution (SYSTEM이 통제, MASTER를 requires로 참조하지 않음)
    ↓
Minimal Loading
    ↓
Agent (A1~A6) + Analysis
    ↓
Schema Validation (Agent → Schema → Output 매핑 기준)
    ↓
Output (agent_report / verification / executive / simulation_report)
    ↓
Verification Split ─┬─ system_verification
                     └─ research_verification (source / methodology / citation / claim fit / reproduction)
    ↓
Uncertainty / Confession (system 층위와 research 층위 분리 기록)
```

## A3 vs A6 — 두 개의 방법론 관점

| | A3 Methodologist | A6 Simulator/Reproducer |
|---|---|---|
| 관점 | Audit (평가) | Execution (실행) |
| 산출물 | 방법론 타당성·한계 평가 텍스트 | 더미 데이터 생성 코드 + 분석 재현 코드 |
| 원자료 필요 여부 | 불필요 (기술된 내용만으로 평가) | 없으면 Simulated Reproduction으로 전환 |
| 검증 근거 자격 | 해당 없음 | **없음** (usable_as_verification_evidence: false 고정) |

## 핵심 원칙

> **파일이 존재하는 것과 시스템이 파일을 사용할 수 있는 것은 다르다.**
> **그리고 시스템 파일을 사용할 수 없는 것과, 연구 내용 자체가 검증되지 않은 것은 서로 다른 문제다.**

v2.2는 첫 번째 문제까지 다뤘고, v2.3은 두 번째 문제(Verification Layer Separation)와
세 번째 확장(Reproduction ≠ Simulation을 수행하는 A6)까지 다룬다.
