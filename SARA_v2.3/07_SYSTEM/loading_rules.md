# SARA v2.3 — Loading Rules

## 1. Minimal Loading Principle

요청에 필요한 최소한의 Source File만 로드한다. (본 원칙은 SYSTEM 계층에만 정의하며 MASTER §13에서는 참조만 한다 — v2.2의 중복 정의 제거.)

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
| 방법론 분석 (audit) | `methodology_audit.md` |
| 재현/시뮬레이션 요청 | `A6_simulator.md`, `simulation_report.md` (v2.3 신규) |
| 비평 | `critical_review.md` |
| 연구공백 | `research_gap.md` |
| 구조화된 연구정보 | `research_schema.md` |
| Claim 구조화 | `claim_schema.md` |
| Evidence 구조화 | `evidence_schema.md` |
| 중요 unverified claim 발견 (모든 라우트 공통, v2.3 신규) | `confession.md` |

## 4. Dependency Closure

모듈을 로드할 때 해당 모듈의 `requires`를 함께 확인한다. 필수 dependency가 누락된 상태에서는 해당 모듈을 정상 실행한 것으로 간주하지 않으며, 이 경우 `system_verification.dependency_resolution`을 실패로 기록한다 (00_SARA_MASTER_v2.3.md §7). 이 실패는 `research_verification` 상태에 자동 전파되지 않는다.

## 5. Conflict Resolution (v2.3 — MASTER §2와 단일화, v2.2 불일치 해소)

동일한 규칙이 여러 파일에서 발견되면 아래 순서로 우선한다 (00_SARA_MASTER_v2.3.md §2와 동일 순서):

1. SYSTEM (본 문서 포함 dependency_map / validation_rules / module_contracts)
2. MASTER
3. CORE
4. ROUTER
5. AGENT
6. ANALYSIS
7. SCHEMA
8. OUTPUT

단, 연구 내용 자체의 사실 판단에서는 Primary Source를 우선한다.

## 6. No Blind Loading

모든 Agent와 Analysis module을 매번 실행하지 않는다. A6(재현/시뮬레이션)은 사용자가 명시적으로 요청한 경우에만 로드한다.

## 7. Circular Dependency 방지 규칙 (v2.3 신규 — Architecture Audit 🔴 FAIL 대응)

본 문서를 포함한 07_SYSTEM 하위 모든 파일은 `00_MASTER/00_SARA_MASTER.md`를 자신의 `requires` 또는 "Always Load" 목록에 포함하지 않는다. SYSTEM은 MASTER 이하 계층을 통제하는 상위 규칙이며, 통제 대상을 스스로 의존성으로 선언하면 순환이 발생하기 때문이다. 이 규칙 위반은 validation_rules_v2.3.md §12에 따라 Architecture Audit FAIL로 즉시 판정한다.
