# SARA v2.3 — Verification Report Template

A2(Investigator)의 기본 출력 템플릿이다. v2.2 대비 External Citation Verification 행,
Evidence Strength 열, Reproducibility 섹션의 상태값을 v2.3 vocabulary로 갱신했다.

## 템플릿

```markdown
# Verification Report

## Verification Summary

| Category | Result | Evidence | Evidence Strength |
|---|---|---|---|
| Bibliographic | | | |
| Citation Content | | | |
| Methodology | | | |
| Claim–Evidence Fit | | | |
| External Facts | | | |

`Result` 열은 validation_rules_v2.3.md §6의 6개 핵심 상태값만 사용한다:
VERIFIED / PARTIALLY VERIFIED / INFERRED / HYPOTHESIZED / UNVERIFIED / CONTRADICTED.
`Evidence Strength` 열은 evidence_schema_v2.3.md의 strong / moderate / weak를 사용한다.

## External Citation Verification (v2.3 신규 섹션)

claim_schema_v2.3.md의 `external_citation_verification` 필드를 인용문헌 단위로 표로 정리한다.

| 인용 문헌 | Status | Note |
|---|---|---|
| (예시) Author (Year) | NOT_COMPLETED | 외부 학술검색 미수행 |

`Status`는 VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / CONTRADICTED / **NOT_COMPLETED** 중 하나이며,
`NOT_COMPLETED`는 이 필드에서만 허용되는 v2.3 신규 상태값이다 (핵심 verification_status 6개값과 별개).

## Quantitative Metrics

정량적 검증 실험이나 명시적 계산 방법이 존재할 때만 백분율을 제시한다. 그렇지 않은 경우:
High / Medium / Low / Not Determinable 을 사용한다.

## Reproducibility (v2.3 갱신)

문헌의 실제 재현 가능성을 아래 3개 상태값으로 평가하며, "다른 대화에서 같은 답이 나올 확률"과
혼동하지 않는다. A6(Simulator)가 실행된 경우 이 섹션은 `simulation_report.md`의
Reproduction Status와 반드시 일치해야 한다 (불일치 시 validation_rules_v2.3.md §5 Output Consistency 위반).

- FULL_REPRODUCTION_AVAILABLE
- SIMULATED_REPRODUCTION
- REPRODUCTION_UNAVAILABLE

## Claim Strength 요약 (v2.3 신규)

A5로 넘겨질 `strength_alignment`(aligned/overreach/underclaim) 판정이 있는 claim만 요약한다.
overreach로 판정된 claim은 반드시 여기 기재한다.
```

## Validation 연동

- `validation_rules_v2.3.md` §6: `Result` 열과 `External Citation Verification.Status` 열의 vocabulary 범위가 다름을 명확히 구분한다.
- `validation_rules_v2.3.md` §11: 본 문서는 research_verification 층위 전용이며, system_verification 실패 여부는 별도 agent_report_v2.3.md 섹션에 기재하고 여기에 병합하지 않는다.
