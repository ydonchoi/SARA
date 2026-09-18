# SARA v2.2 — Validation Rules

## 1. Orphan Check

어떤 파일도 시스템에서 역할이 정의되지 않은 채 존재해서는 안 된다.

## 2. Circular Dependency Check

dependency graph에서 cycle을 허용하지 않는다.

예:

```text
A → B → C → A
```

는 오류다.

## 3. Duplicate Rule Check

동일한 규칙이 여러 모듈에서 독립적으로 정의되어 서로 다른 의미를 만들지 않는지 확인한다.

공통 규칙은 CORE 또는 SYSTEM에 둔다.

## 4. Schema Consistency

Agent output과 Schema가 일치하는지 검사한다.

## 5. Output Consistency

모든 route는 적절한 Output template으로 종료되어야 한다.

## 6. Evidence Status Consistency

허용 상태:

- VERIFIED
- PARTIALLY VERIFIED
- INFERRED
- HYPOTHESIZED
- UNVERIFIED
- CONTRADICTED

새로운 상태를 임의로 추가하지 않는다.

## 7. Research-Type Consistency

연구 유형에 존재하지 않는 변수나 통계치를 강제하지 않는다.

## 8. Claim Strength Check

Conclusion의 강도가 Evidence의 강도를 초과하는지 검사한다.

## 9. Source Integrity

외부 자료를 사용했다면 출처와 검증 범위를 기록한다.

## 10. Confession Requirement

중요한 uncertainty 또는 unverified claim이 존재하면 `confession.md`에 기록한다.
