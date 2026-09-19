# SARA v2.3 — Evidence Schema

## Purpose

A2(Investigator)가 참조하는 evidence 구조화 스키마다. v2.2 대비 2가지가 추가되었다:
(1) verification layer 명시, (2) `evidence_strength` 필드, (3) **A6(Simulator) 출력의 evidence 자격 완전 차단**.

## Schema

```yaml
evidence:
  id:
  description:
  source:
  source_level:                    # Level 1~4 (00_SARA_MASTER_v2.3.md §4 Source Hierarchy)
  evidence_type:                   # 아래 Evidence Types 참조
  method:
  supports_claims: []
  verification:                    # VERIFIED / PARTIALLY VERIFIED / INFERRED / HYPOTHESIZED / UNVERIFIED / CONTRADICTED
  verification_layer: research_verification   # v2.3 신규 — claim_schema_v2.3.md와 동일 원칙, 항상 research_verification 고정
  evidence_strength:               # v2.3 신규 — strong / moderate / weak (claim_schema의 strength_alignment 판정에 사용)
  usable_as_verification_evidence: true   # v2.3 신규 — 기본값 true, simulated_reproduction 타입은 강제로 false
  limitations:
```

## Evidence Types

- empirical data
- statistical result
- qualitative quotation
- observation
- theoretical argument
- prior research
- official statistic
- methodological documentation
- **simulated_reproduction** ← v2.3 신규 (A6 Simulator/Reproducer의 출력 전용 타입)

## 필드별 v2.3 규칙 상세

### `verification_layer` (신규)

claim_schema_v2.3.md와 동일하게 `research_verification`으로 고정한다. evidence 자체의 "존재·접근 가능성"을
다루는 것이지 SARA 시스템 파일의 `system_verification`과는 무관하다.

### `evidence_strength` (신규)

| 값 | 판정 기준 |
|---|---|
| `strong` | 직접 관찰·통계적으로 유의한 정량적 결과·원자료 기반 |
| `moderate` | 간접적이거나 단일 사례·소규모 표본 기반 |
| `weak` | 이론적 주장이나 서술적 관찰에 그침, 통계적 뒷받침 없음 |

이 값은 claim_schema_v2.3.md의 `strength_alignment` 판정(aligned/overreach/underclaim)에 직접 사용된다.

### `usable_as_verification_evidence` (신규 — A6 방화벽 규칙, 완전 차단 확정)

기본값은 `true`다. 단, `evidence_type: simulated_reproduction`인 evidence 항목은 **예외 없이**
`usable_as_verification_evidence: false`로 고정한다. 이는 A6_simulator.md의 must_not 규칙
("A6 출력을 A2 Verification의 evidence로 사용하지 않는다")을 스키마 레벨에서 강제하는 장치다.

```yaml
evidence:
  id: EV-SIM-01
  description: "논문의 변수 구조를 반영한 더미 데이터 기반 회귀분석 재현 결과"
  source: "A6 Simulator output (simulation_report.md)"
  source_level: null              # Source Hierarchy(Level 1~4) 대상 아님 — 가상 데이터이므로 등급 부여하지 않음
  evidence_type: simulated_reproduction
  method: "Simulated Reproduction"
  supports_claims: []             # 항상 빈 배열 — 어떤 claim의 verification에도 연결되지 않음
  verification: UNVERIFIED        # 재현물 자체는 "검증된 사실"이 아니므로 UNVERIFIED 고정
  verification_layer: research_verification
  evidence_strength: null         # 강도 판정 대상 아님
  usable_as_verification_evidence: false   # 고정, 변경 불가
  limitations: "원자료가 아닌 가상 데이터 기반 시뮬레이션 결과이므로 논문 결론의 검증 근거로 사용할 수 없음"
```

A2의 검증 프로세스(Existence → Bibliographic Accuracy → Content → Citation Fit → Evidence Strength)는
`supports_claims`를 채우려는 시도가 있어도 `usable_as_verification_evidence: false`인 evidence는
자동으로 제외하고 `verification_status` 계산에 포함하지 않는다.

## Validation 연동

- `validation_rules_v2.3.md` §4 Schema Consistency: `verification_layer` 고정값 검사.
- `validation_rules_v2.3.md` §8 Claim Strength Check: `evidence_strength` ↔ claim의 `strength_alignment` 대조.
- `validation_rules_v2.3.md` §11 Verification Layer Separation: `simulated_reproduction` 타입 evidence는
  `research_verification.reproduction_status`(00_SARA_MASTER_v2.3.md §7)에만 반영되고,
  일반 claim의 `verification_status`에는 어떤 경우에도 영향을 주지 않는다.
- module_contracts_v2.3.md A6 must_not 규칙과 1:1 대응.
