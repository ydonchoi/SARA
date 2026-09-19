# SARA v2.3 — Executive Synthesis Template

`/통합` 라우트의 최종 출력 템플릿이다. v2.2의 11개 섹션에 Reproduction/Simulation 섹션과
Verification Layer 구분을 추가했다.

## 템플릿

```markdown
# Executive Synthesis Template

## 1. Research at a Glance
(제목, taxonomy_mid/micro/sub, methodology/methodology_sub — research_schema_v2.3.md 참조)

## 2. Core Research Question

## 3. Main Claims
(claim_schema_v2.3.md 기준 정리 — inference_level, strength_alignment 포함)

## 4. Evidence Structure
(evidence_schema_v2.3.md 기준 정리 — evidence_strength 포함, simulated_reproduction 타입은 별도 표시)

## 5. Methodological Assessment (A3 — Audit 관점)
(연구설계·표집·분석기법 타당성, causal inference 강도 평가)

## 6. Reproduction / Simulation Summary (v2.3 신규, A6 실행 시)
- Reproduction Status: FULL_REPRODUCTION_AVAILABLE / SIMULATED_REPRODUCTION / REPRODUCTION_UNAVAILABLE
- 요약: (simulation_report.md 핵심 내용 요약, 코드 전문은 재수록하지 않고 링크만 참조)
- 본 섹션의 결과는 어떤 claim의 verification_status에도 영향을 주지 않음을 명시 (§8과 교차 확인)

## 7. Citation / Verification Findings
### 7a. Research Verification (research_verification 층위)
### 7b. External Citation Verification (claim_schema_v2.3.md 전용 필드, NOT_COMPLETED 허용)

## 8. Critical Issues (A5)
(strength_alignment: overreach로 판정된 claim 우선 기재)

## 9. Research Gaps (A4)

## 10. Follow-up Research Opportunities

## 11. Uncertainty Audit
(system_verification / research_verification 분리 표기 — 00_SARA_MASTER_v2.3.md §7)

## 12. Final Analytical Rationale
```

## Validation 연동

- `validation_rules_v2.3.md` §5 Output Consistency: `/통합` 라우트는 A6가 포함된 경우 반드시
  "6. Reproduction / Simulation Summary" 섹션을 채운다. A6 미포함 시 "N/A — 재현/시뮬레이션 미요청"으로 표기한다.
- `validation_rules_v2.3.md` §11: "7a"와 "7b"를 병합 표기하지 않는다.
- dependency_map_v2.3.md `/통합` route의 optional 항목(A6_simulator.md, simulation_report.md)이 로드된 경우에만
  6번 섹션을 실질적으로 채운다.
