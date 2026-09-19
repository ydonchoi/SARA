# SARA v2.3 — Research Schema

## Purpose

A1(Summarizer), A3(Methodologist), A6(Simulator/Reproducer)가 공통으로 참조하는 연구 구조화 스키마다.
v2.3에서는 사용자가 제공한 Obsidian 논문 스키밍 프롬프트의 YAML 헤더 필드
(`taxonomy_mid`, `taxonomy_micro`, `taxonomy_sub`, `methodology_sub`, `main_tools`, `main_technique`)를
정식 필드로 편입하여, 기존 v2.2 필드(연구유형, 연구설계 등)와 함께 단일 스키마로 관리한다.

## Schema Fields

### 1. 식별 정보 (Identification)

| 필드 | 설명 | 근거 Agent |
|---|---|---|
| `title` | 논문의 전체 제목 | A1 |
| `source` | Primary Source 파일 링크 (예: `[[{{title}}.pdf]]`) | A1 |
| `연결노트` | 연동 노트 목록 (예: `(G)`, `(G) 연구방법론 심화`, `(G) 인사이트`, `(G) 논의`) | A1 |
| `status` | 분석 완료 여부 (boolean) | A1 |

### 2. 학문분류 (Discipline Taxonomy) — v2.3 신규 정식 필드

| 필드 | 설명 | Verification 상태 표기 |
|---|---|---|
| `taxonomy_mid` | 학문분류체계 중분류(mid-level) 명칭 | INFERRED 가능 (논문의 학회지·게재 학회 정보 근거) |
| `taxonomy_micro` | 학문분류체계 소분류(micro-level) 명칭 | INFERRED 가능 |
| `taxonomy_sub` | 한국 학문분류체계 세부분류(subcategory) 명칭 | INFERRED 가능 |

**표기 규칙**: 논문 자체에 학문분류가 명시되어 있지 않은 경우, 연구 주제·게재 학회지·연구방법을 근거로
A1이 `INFERRED`로 판정하여 채운다. 임의로 `VERIFIED`를 부여하지 않는다.

### 3. 연구 패러다임 및 방법론 (Paradigm & Methodology)

| 필드 | 설명 | 허용값 |
|---|---|---|
| `methodology` | 연구 패러다임 대분류 | 질적 연구 / 양적 연구 / 혼합 연구 |
| `methodology_sub` | 하위 방법론 — v2.3 신규 정식 필드 | 예: 사례 연구, 근거이론, 실험 설계, 설문 조사, 공간 분석, 구조방정식 모델링, Design-Based Research 등 (자유 기술, 임의 강제 없음) |

`methodology_sub`가 논문에 명시적으로 표현되지 않은 경우, A1/A3는 연구설계 기술 내용을 근거로
`INFERRED`로 표기하며 "논문 원문에 방법론 명칭이 직접 제시되지 않음"을 함께 기록한다.

### 4. 분석 도구 및 기법 (Tools & Techniques) — v2.3 신규 정식 필드

| 필드 | 설명 | 근거 Agent |
|---|---|---|
| `main_tools` | 주요 분석 도구 (예: Python, R, SPSS, ArcGIS, NVivo, MAXQDA 등) | A3 (methodology_audit 결과 기반) |
| `main_technique` | 주요 분석 기법 (예: 회귀분석, SEM, 근거이론 코딩, 공간분석 등) | A3 |

`main_tools`/`main_technique`는 A6(Simulator)가 더미 데이터 생성·분석 재현 코드를 작성할 때
`requires` 입력으로 직접 참조한다 (module_contracts_v2.3.md의 A6 requires 참조).

### 5. 연구 대상 및 표집 (Subjects & Sampling) — v2.2 유지

| 필드 | 설명 |
|---|---|
| `population` | 모집단 특성 (교육학: 학습자/교사/학교, 지리학: 지역/공간 단위 등) |
| `sample_size` | 표본 크기 |
| `sampling_strategy` | 표집 방식 (확률/비확률) 및 대표성 평가 |

### 6. 연구 설계 (Research Design) — v2.2 유지, A6 연동 확장

| 필드 | 설명 |
|---|---|
| `design_structure` | 독립변수-종속변수 관계 또는 연구 흐름 |
| `variables` | 측정도구, 관찰 프로토콜, 공간 데이터(GIS 레이어 등) 구성 |
| `variable_distribution` | v2.3 신규 — A6 더미 데이터 생성 시 필요한 변수 분포 특성 (정규분포 여부, 범주형/연속형, 공간좌표 등) |

### 7. 재현성 (Reproducibility) — v2.3 신규, A6 연동 전용

| 필드 | 설명 | 허용값 |
|---|---|---|
| `raw_data_available` | 원자료(활동지, 응답지, 관찰일지, 원본 데이터셋, 실제 코드 등) 제공 여부 | true / false / partial |
| `reproduction_status` | A6가 판정한 재현 가능성 | FULL_REPRODUCTION_AVAILABLE / SIMULATED_REPRODUCTION / REPRODUCTION_UNAVAILABLE |

## YAML 헤더 통합 예시 (Obsidian 노트 적용형)

```yaml
---
title: "{{title}}"
taxonomy_mid: ""
taxonomy_micro: ""
taxonomy_sub: ""
methodology: ""          # 질적 연구 / 양적 연구 / 혼합 연구
methodology_sub: ""
main_tools: ""
main_technique: ""
population: ""
sample_size: ""
sampling_strategy: ""
design_structure: ""
variables: ""
variable_distribution: ""
raw_data_available: false
reproduction_status: ""
source:
  - "[[{{title}}.pdf]]"
연결노트:
  - "[[{{title}} (G)]]"
  - "[[{{title}} (G) 연구방법론 심화]]"
  - "[[{{title}} (G) 인사이트]]"
  - "[[{{title}} (G) 논의]]"
status: false
---
```

## Agent 참조 규칙 (module_contracts_v2.3.md와 정합)

| Agent | 참조 필드 |
|---|---|
| A1 | title, taxonomy_mid/micro/sub, methodology, methodology_sub, 연결노트, status |
| A3 | population, sample_size, sampling_strategy, design_structure, variables, main_tools, main_technique |
| A6 | variable_distribution, main_tools, main_technique, raw_data_available, reproduction_status |

## Validation 연동

- `validation_rules_v2.3.md` §4 Schema Consistency: 위 "Agent 참조 규칙" 표를 판정 기준으로 사용한다.
- `validation_rules_v2.3.md` §7 Research-Type Consistency: `methodology`가 "양적 연구"가 아닌 경우
  `variable_distribution`처럼 통계적 분포를 전제로 하는 필드를 강제로 채우지 않는다 (질적/공간 데이터는
  해당 필드를 `N/A` 또는 정성적 서술로 대체).
- 모든 taxonomy/methodology_sub 필드가 `INFERRED` 상태일 때는 A1 출력에 근거(논문의 어떤 기술로부터
  추론했는지)를 함께 명시한다 — MASTER v2.3 §8 Inference Control 준수.
