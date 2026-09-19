# SARA v2.3 — Validation Rules

## 1. Orphan Check

어떤 파일도 시스템에서 역할이 정의되지 않은 채 존재해서는 안 된다.

## 2. Circular Dependency Check

dependency graph에서 cycle을 허용하지 않는다.

```text
A → B → C → A
```

는 오류다. (SYSTEM은 방향성 그래프의 노드가 아니라 control layer이므로 이 검사 대상에서 제외 — dependency_map_v2.3.md 참조. 단, §12 규칙은 별도로 적용된다.)

## 3. Duplicate Rule Check

동일한 규칙이 여러 모듈에서 독립적으로 정의되어 서로 다른 의미를 만들지 않는지 확인한다. 공통 규칙은 CORE 또는 SYSTEM 중 **한 곳에만** 둔다 (v2.2에서 "Minimal Loading Principle"이 MASTER §12와 SYSTEM 양쪽에 중복 정의되었던 문제를 v2.3에서 SYSTEM 단일화로 해소 — loading_rules_v2.3.md §1 참조).

## 4. Schema Consistency

Agent output과 Schema가 일치하는지 검사한다. 검사 기준은 module_contracts_v2.3.md의 "Agent → Schema → Output 매핑" 표를 사용한다 (v2.2에서는 매핑 기준이 없어 🟡 PARTIAL 판정을 받았음).

## 5. Output Consistency

모든 route는 적절한 Output template으로 종료되어야 한다. A6(재현/시뮬레이션) 라우트는 `simulation_report.md`로 종료된다.

## 6. Evidence Status Consistency

허용 상태: VERIFIED / PARTIALLY VERIFIED / INFERRED / HYPOTHESIZED / UNVERIFIED / CONTRADICTED. 새로운 상태를 임의로 추가하지 않는다. (단, §11의 system_verification/research_verification은 상태값이 아니라 층위 구분 필드이므로 본 규칙과 충돌하지 않는다.)

## 7. Research-Type Consistency

연구 유형에 존재하지 않는 변수나 통계치를 강제하지 않는다.

## 8. Claim Strength Check

Conclusion의 강도가 Evidence의 강도를 초과하는지 검사한다. (예: causal 표현이 실제 연구설계 — 통제집단·사전사후비교 부재 등 — 보다 강한 경우 A3/A5가 이를 명시적으로 지적한다.)

## 9. Source Integrity

외부 자료를 사용했다면 출처와 검증 범위를 기록한다.

## 10. Confession Requirement

중요한 uncertainty 또는 unverified claim이 존재하면 `confession.md`에 기록한다. 이 규칙은 `/요약`, `/방법론`, `/비평` 라우트에도 조건부로 적용된다 (v2.3에서 dependency_map_v2.3.md에 conditional load로 명시 — v2.2의 커버리지 공백 해소).

## 11. Verification Layer Separation (v2.3 신규 — 최우선 수정사항)

`system_verification`과 `research_verification`을 병합하여 보고하지 않는다. 두 층위는 항상 분리 표기하며, system_verification의 실패가 research_verification 상태를 자동으로 하향 조정해서는 안 된다. (근거: 07_SYSTEM 접근 실패로 인해 논문 자체의 방법론 검증 결과가 부당하게 PARTIALLY VERIFIED로 오염되는 status propagation 오류 방지.)

## 12. Circular Dependency 재발 방지 (v2.3 신규)

SYSTEM 계층 파일(dependency_map, loading_rules, module_contracts, validation_rules)은 어떤 경우에도 `00_MASTER/00_SARA_MASTER.md`를 자신의 `requires` 목록 또는 "Always Load" 목록에 포함하지 않는다. 위반이 발견되면 Architecture Audit을 즉시 FAIL로 표시한다.
