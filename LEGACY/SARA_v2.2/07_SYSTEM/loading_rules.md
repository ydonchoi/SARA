# SARA v2.2 — Loading Rules

## 1. Minimal Loading Principle

요청에 필요한 최소한의 Source File만 로드한다.

## 2. Always Load

- `00_MASTER/00_SARA_MASTER.md`
- `01_CORE/identity.md`
- `01_CORE/principles.md`
- `01_CORE/uncertainty.md`

## 3. Conditional Loading

| 조건 | 로드 |
|---|---|
| 외부 검증 | `source_policy.md` |
| citation 검증 | `citation_audit.md` |
| claim 분석 | `claim_evidence.md` |
| 방법론 분석 | `methodology_audit.md` |
| 비평 | `critical_review.md` |
| 연구공백 | `research_gap.md` |
| 구조화된 연구정보 | `research_schema.md` |
| Claim 구조화 | `claim_schema.md` |
| Evidence 구조화 | `evidence_schema.md` |

## 4. Dependency Closure

모듈을 로드할 때 해당 모듈의 `requires`를 함께 확인한다.

필수 dependency가 누락된 상태에서는 해당 모듈을 정상 실행한 것으로 간주하지 않는다.

## 5. Conflict Resolution

동일한 규칙이 여러 파일에서 발견되면:

1. MASTER
2. CORE
3. SYSTEM validation rules
4. ROUTER
5. AGENT
6. ANALYSIS
7. OUTPUT
8. SCHEMA

순으로 우선한다.

단, 연구 내용 자체의 사실 판단에서는 Primary Source를 우선한다.

## 6. No Blind Loading

모든 Agent와 Analysis module을 매번 실행하지 않는다.
