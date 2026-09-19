# SARA v2.3 — Agent Report Template

모든 Agent(A1~A6) 출력의 기본 템플릿이다. v2.2 대비 Verification Status를 2계층으로 분리하고,
A6가 관여한 경우의 Reproduction Status 섹션을 조건부로 추가했다.

## 템플릿

```markdown
# Agent Report

## Agent
(A1 / A2 / A3 / A4 / A5 / A6 중 실행된 agent)

## Task
(수행한 작업 요약)

## Scope
(분석 범위 — 라우트, 대상 논문/자료)

## Findings
(핵심 발견사항)

## Evidence
(evidence_schema_v2.3.md 형식을 따르는 근거 목록. evidence_type이 simulated_reproduction인 항목은
 반드시 usable_as_verification_evidence: false와 함께 별도 표시)

## Verification Status (v2.3 — 2계층 분리 필수)

| 층위 | 상태 | 근거 |
|---|---|---|
| system_verification | (dependency_resolution / module_access / loading_completeness / contract_compliance 중 해당 항목 상태) | |
| research_verification | (source_access / methodology_evidence / citation_verification / claim_evidence_fit / reproduction_status 중 해당 항목 상태) | |

> [!caution] 전파 금지
> system_verification의 실패가 research_verification 상태를 자동으로 낮추지 않는다
> (00_SARA_MASTER_v2.3.md §7, validation_rules_v2.3.md §11).

## Reproduction Status (A6 관여 시에만 작성)
- 판정: FULL_REPRODUCTION_AVAILABLE / SIMULATED_REPRODUCTION / REPRODUCTION_UNAVAILABLE
- 근거: (원자료 제공 여부)
- 상세 결과는 `simulation_report.md` 참조

## Inference
- inference_level: FACT / INFERENCE / HYPOTHESIS / SPECULATION
- inference_basis: (FACT가 아닌 경우 필수 기재, claim_schema_v2.3.md 규칙 준수)

## Strength Check (A3, A5 실행 시)
- strength_alignment: aligned / overreach / underclaim
- 근거: (claim 표현 강도 vs evidence_strength 대조)

## Uncertainty
(확인되지 않았거나 조건부인 부분)

## Analytical Rationale
- Evidence:
- Source:
- Method:
- Interpretation:
- Limitation:
```

## Validation 연동

- `validation_rules_v2.3.md` §5 Output Consistency: 모든 라우트는 본 템플릿(또는 `verification.md`/`executive.md`/`simulation_report.md`)으로 종료된다.
- `validation_rules_v2.3.md` §11: Verification Status 섹션은 반드시 2행(system/research)으로 분리 기재한다. 하나로 병합된 상태 표기는 스키마 위반으로 간주한다.
- A1, A4는 "Reproduction Status"와 "Strength Check" 섹션을 생략할 수 있다 (해당 없음, module_contracts_v2.3.md 참조).
