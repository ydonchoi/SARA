# 05_OUTPUT — simulation_report.md (A6 Output Template)

A6(Simulator/Reproducer)의 모든 출력은 이 템플릿을 따른다. Obsidian-compatible Markdown 형식이며,
사용자가 제공한 논문 스키밍 프롬프트의 "6. 연구 재현 시뮬레이션" 섹션 구조를 기반으로 한다.

---

## 템플릿

```markdown
# 🧪 연구 재현 시뮬레이션 (Reproduction Simulation)

## Reproduction Status
- 판정: (FULL_REPRODUCTION_AVAILABLE / SIMULATED_REPRODUCTION / REPRODUCTION_UNAVAILABLE)
- 판정 근거: (원자료·전체 데이터셋·실제 코드 제공 여부를 근거로 서술)

> [!info] Reproduction ≠ Simulation
>
> 본 섹션은 논문에 기술된 변수 구조를 바탕으로 한 가상 시뮬레이션이며,
> 논문의 실제 결과를 검증하거나 재현한 것이 아닙니다.

---

## 개요 (Overview)
(이 논문의 분석 논리를 재현해볼 '가상 시뮬레이션 실습'의 주제와 목적을 간략히 안내)

---

## 더미 데이터 생성 (Dummy Data Generation)

- 반영 대상 변수 구조: (A3 methodology audit에서 확인된 변수/표본/척도)
- 데이터 특성: (정규분포 여부, 범주형/연속형, 공간좌표 등)

\`\`\`python
# Dummy Data Generation
# (pandas, numpy, geopandas 등 활용 — 논문의 변수 구조를 반영한 가상 데이터셋 생성 코드)
\`\`\`

---

## 분석 실행 코드 (Analysis Execution)

- 재현 대상 기법: (논문에서 사용된 핵심 통계기법 또는 알고리즘)

\`\`\`python
# Analysis Execution
# (statsmodels, scikit-learn, geopandas 등 활용 — 더미 데이터에 대해 논문의 분석 기법을 재현)
\`\`\`

### 예상 출력 결과 (Expected Output)
(코드 실행 시 예상되는 출력 형태를 서술. 실제 수치가 아니라 "구조적으로 유사한 결과"임을 명시)

---

## Uncertainty / Limitation
- (더미 데이터 기반 결과와 논문의 실제 결과가 다를 수 있는 지점)
- (원자료 미제공으로 Full Reproduction이 불가능한 부분)
- (전문 SW로만 정확히 재현 가능한 부분이 있다면 명시 — 예: GIS 공간분석, NVivo 코딩 등)

---

## [Confession 연동]
중요한 uncertainty가 있는 경우 `confession.md`에 다음 형식으로 함께 기록한다.

- Inferred: (A6가 변수 구조로부터 합리적으로 추론한 가정)
- Unverified: (원자료 부재로 확인 불가능한 부분)
- Largest Uncertainty: (시뮬레이션 결과와 실제 논문 결과 간 괴리 가능성 중 가장 큰 것)
```

---

## Schema 연동

A6는 `06_SCHEMA/research_schema.md`의 변수구조 필드(methodology, methodology_sub, main_tools, main_technique)와
A3(`03_AGENTS/A3_methodologist.md`) 출력을 입력으로 받아 위 템플릿을 채운다
(module_contracts_v2.3.md의 "Agent → Schema → Output 매핑" 참조).

## Validation 연동

- `validation_rules_v2.3.md` §5 Output Consistency: `/재현` 라우트는 반드시 본 템플릿으로 종료되어야 한다.
- `validation_rules_v2.3.md` §11: 본 출력의 Reproduction Status는 `research_verification.reproduction_status`
  필드에 해당하며, `system_verification` 실패 여부와 독립적으로 판정한다.
