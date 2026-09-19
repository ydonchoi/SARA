# SARA v2.3 — Module Contracts

## Contract Interface

각 module은 다음 interface를 **완전히 채워** 준수한다 (v2.2에서는 A1~A5가 input/output/must_not 정도만 정의되어
"검증 가능한 interface"가 아니라 "설계 지침"에 가깝다는 🟡 PARTIAL 판정을 받았음 — v2.3에서 해소).

```yaml
module:
  id:
  role:
  purpose:

requires: []
inputs: []
process: []
outputs: []
must_not: []
status_vocabulary: []
```

## Agent Contracts

### A1 — Summarizer
```yaml
module:
  id: A1
  role: Structural Research Summarizer
  purpose: Primary Source의 구조(연구문제, 연구유형, 핵심결과)를 매핑
requires:
  - 04_ANALYSIS/research_mapping.md
  - 06_SCHEMA/research_schema.md
inputs: [primary research document]
process:
  - 연구문제 및 연구유형 식별
  - 학문분류(taxonomy_mid/micro/sub), methodology/methodology_sub 태깅
  - 핵심 결과 구조화
outputs: [structural research summary → agent_report]
must_not: [unsupported inference]
status_vocabulary: [VERIFIED, PARTIALLY VERIFIED, INFERRED, UNVERIFIED]
```

### A2 — Investigator
```yaml
module:
  id: A2
  role: Citation & Evidence Verifier
  purpose: 인용·근거의 존재·정합성 검증
requires:
  - 01_CORE/source_policy.md
  - 04_ANALYSIS/citation_audit.md
  - 04_ANALYSIS/claim_evidence.md
  - 06_SCHEMA/claim_schema.md
  - 06_SCHEMA/evidence_schema.md
inputs: [citations, claims, external sources when required]
process:
  - Existence → Bibliographic Accuracy → Content → Citation Fit → Evidence Strength
outputs: [verification report → verification.md]
must_not: [claim verification without evidence]
status_vocabulary: [VERIFIED, PARTIALLY VERIFIED, UNVERIFIED, CONTRADICTED, NOT_COMPLETED]
```

### A3 — Methodologist (Audit 관점)
```yaml
module:
  id: A3
  role: Methodology Auditor
  purpose: 연구설계·표집·분석기법·causal inference 강도의 타당성 평가 (실행/코드 생성 없음)
requires:
  - 04_ANALYSIS/methodology_audit.md
  - 06_SCHEMA/research_schema.md
inputs: [research design, sampling, data, analysis/coding procedure]
process:
  - Research Design 확인
  - Participants/Sampling 대표성 평가
  - Data & Analysis 기법 확인
  - Coding/Reliability 절차 확인
  - Claim Strength vs Design Strength 비교 (causal overreach 탐지)
outputs: [methodology audit report → agent_report]
must_not:
  - simulation/reproduction 코드 생성 (A6 영역, 상호 배타)
  - 근거 없는 평가어 사용 — 예: "신뢰도가 낮다" 대신 "~는 논문에서 확인되지 않음"
status_vocabulary: [VERIFIED, PARTIALLY VERIFIED, NOT_IDENTIFIED, UNVERIFIED]
```

### A4 — Visionary
```yaml
module:
  id: A4
  role: Research Gap & Vision Generator
  purpose: 한계·공백으로부터 후속 연구 방향 도출
requires:
  - 01_CORE/uncertainty.md
  - 04_ANALYSIS/research_gap.md
inputs: [limitations, gaps, evidence]
process:
  - Paper-derived limitation → Evidence-informed gap → Hypothesis → Speculative extension
outputs: [research vision → agent_report]
must_not: [present speculation as established finding]
status_vocabulary: [INFERENCE, HYPOTHESIS, SPECULATION]
```

### A5 — Reviewer
```yaml
module:
  id: A5
  role: Critical Reviewer
  purpose: claim-evidence-method 전반의 종합 비평
requires:
  - 04_ANALYSIS/critical_review.md
  - 04_ANALYSIS/claim_evidence.md
inputs: [claims, evidence, methods]
process:
  - 강점/한계 식별 → claim strength check → 종합 판단
outputs: [critical review → agent_report]
must_not: [arbitrary scoring without rubric]
status_vocabulary: [VERIFIED, PARTIALLY VERIFIED, INFERRED, UNVERIFIED]
```

### A6 — Simulator / Reproducer (v2.3 신규, Execution 관점)

`/방법론`(A3, Audit)과 상호 배타적인 독립 에이전트. A3의 must_not에 "simulation 코드 생성 금지"를,
A6의 requires에 "A3 결과 참조"를 명시하여 두 에이전트의 경계를 기계적으로 구분한다.

```yaml
module:
  id: A6
  role: Research Method Simulator / Reproducer
  purpose: 논문에서 확인된 변수구조·분석기법을 반영한 더미 데이터셋 생성 및 핵심 분석 재현 코드 작성
requires:
  - 03_AGENTS/A3_methodologist.md  # 출력물(변수/표본/도구 구조)을 입력으로 참조
  - 04_ANALYSIS/methodology_audit.md
  - 06_SCHEMA/research_schema.md
  - 05_OUTPUT/simulation_report.md
  - 05_OUTPUT/confession.md
inputs:
  - A3의 methodology audit 결과 (변수 구조, 표본 특성, 측정도구, 분석기법)
  - 원자료 제공 여부
process:
  - Step 1. Reproduction Feasibility 판정 (원자료 제공 여부 확인)
  - Step 2. 불가능 시 Simulated Reproduction으로 전환, 출력 상단에 명시적 라벨링
  - Step 3. 변수 구조(분포, 척도, 공간좌표 등)를 반영한 더미 데이터 생성 코드 작성
  - Step 4. 논문의 핵심 통계기법/알고리즘을 재현하는 분석 실행 코드 작성
  - Step 5. 예상 출력 결과를 "시뮬레이션 결과"로 명확히 표기하여 서술
outputs:
  - Simulation Overview
  - Reproduction Status
  - Dummy Data Generation Code
  - Analysis Execution Code
  - Expected Output Description
  - → 05_OUTPUT/simulation_report.md
must_not:
  - 원자료 없이 생성한 결과를 "실제 재현된 연구 결과"로 제시하지 않는다
  - Full Reproduction과 Simulated Reproduction 혼용 표기 금지
  - A6 출력을 A2 Verification의 evidence로 사용하지 않는다
status_vocabulary:
  - FULL_REPRODUCTION_AVAILABLE
  - SIMULATED_REPRODUCTION
  - REPRODUCTION_UNAVAILABLE
```

## Agent → Schema → Output 매핑 (v2.3 신규 — Schema Consistency 🟡 PARTIAL 해소)

| Agent | 참조 Schema | Output |
|---|---|---|
| A1 | research_schema | agent_report |
| A2 | claim_schema + evidence_schema | verification (+ 필요시 confession) |
| A3 | research_schema (설계/표집/도구 필드) | agent_report |
| A4 | research_gap 기반 uncertainty 필드 | agent_report (+ confession) |
| A5 | claim_schema + evidence_schema | agent_report |
| A6 | research_schema (변수구조 필드) + A3 output | simulation_report |

## Output Contract

모든 Agent output은 최소한 다음을 포함한다.

- Findings
- Evidence
- Verification Status (system_verification / research_verification 분리 표기, 00_SARA_MASTER_v2.3.md §7)
- Inference
- Uncertainty
