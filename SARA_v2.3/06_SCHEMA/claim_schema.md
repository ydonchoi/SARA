# SARA v2.3 — Claim Schema

## Purpose

A2(Investigator), A5(Reviewer)가 참조하는 claim 구조화 스키마다. v2.2 대비 3가지가 추가되었다:
(1) verification layer 명시, (2) INFERRED 근거 의무화, (3) Claim Strength Check 연동 필드,
(4) External Citation Verification 전용 필드(신규 상태값 포함).

## Schema

```yaml
claim:
  id:
  text:
  type:
  source:
  evidence_ids: []
  verification_status:            # VERIFIED / PARTIALLY VERIFIED / INFERRED / HYPOTHESIZED / UNVERIFIED / CONTRADICTED
  verification_layer: research_verification   # v2.3 신규 — 00_SARA_MASTER_v2.3.md §7 고정값, 항상 research_verification
  inference_level:                 # FACT / INFERENCE / HYPOTHESIS / SPECULATION
  inference_basis:                 # v2.3 신규 — inference_level != FACT 인 경우 필수. 어떤 근거로 이 추론에 도달했는지 서술
  strength_alignment:               # v2.3 신규 — aligned / overreach / underclaim (evidence_schema의 evidence_strength와 대조하여 판정)
  external_citation_verification:   # v2.3 신규, 전용 필드
    status:                        # VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / CONTRADICTED / NOT_COMPLETED
    note:                          # NOT_COMPLETED인 경우 사유 명시 (예: "외부 학술검색 미수행")
  uncertainty:
  scope:
```

## Inference Levels

FACT / INFERENCE / HYPOTHESIS / SPECULATION

## 필드별 v2.3 규칙 상세

### `verification_layer` (신규)

claim_schema가 다루는 검증은 항상 논문·연구내용에 대한 검증이므로 `research_verification`으로 고정한다.
`system_verification`(SARA 시스템 파일 접근 여부 등)과 혼동되지 않도록 값이 하드코딩된다.
(근거: 00_SARA_MASTER_v2.3.md §7 Verification Architecture, validation_rules_v2.3.md §11)

### `inference_basis` (신규, 조건부 필수)

`inference_level`이 `FACT`가 아닌 모든 claim은 `inference_basis`를 반드시 채운다.
비워두면 해당 claim은 스키마 위반으로 간주하고 `PARTIALLY VERIFIED` 이상으로 표시할 수 없다.

예시:
```yaml
inference_level: INFERENCE
inference_basis: "논문 3.2절의 표집 절차 기술로부터, 확률표집이 아닌 편의표집임을 추론함"
```

### `strength_alignment` (신규)

validation_rules_v2.3.md §8 Claim Strength Check를 기계적으로 수행하기 위한 필드다.
claim의 표현 강도(예: 인과적 단정 vs 상관적 서술)와 evidence_schema의 `evidence_strength`를 대조하여 판정한다.

| 값 | 의미 |
|---|---|
| `aligned` | claim의 강도가 evidence 강도와 부합 |
| `overreach` | claim이 evidence보다 강하게 표현됨 (예: 통제집단 없이 "효과가 있다"고 단정) |
| `underclaim` | claim이 evidence보다 과도하게 보수적으로 표현됨 |

A5(Reviewer)는 `overreach`로 판정된 claim을 critical review에서 반드시 지적한다.

### `external_citation_verification` (신규, 전용 필드 — status_vocabulary 확장은 이 필드 내로 한정)

논문 내부 주장 자체의 검증(`verification_status`)과, 논문이 인용한 **선행연구의 실존·서지정보** 검증은
서로 다른 성격이므로 별도 필드로 분리한다. 이 필드 안에서만 새 상태값 `NOT_COMPLETED`를 허용하며,
validation_rules_v2.3.md §6(핵심 6개 상태값 고정)이 규정하는 `verification_status`의 vocabulary는
변경하지 않는다.

```yaml
external_citation_verification:
  status: NOT_COMPLETED
  note: "외부 학술검색을 수행하지 않아 인용문헌의 실존·서지정보를 확인하지 않음"
```

외부 검색을 수행한 경우:
```yaml
external_citation_verification:
  status: VERIFIED
  note: "학술 DB 검색을 통해 인용문헌의 존재 및 서지정보 확인함"
```

## Validation 연동

- `validation_rules_v2.3.md` §4 Schema Consistency: `verification_layer`가 `research_verification`으로
  고정되어 있는지 검사한다.
- `validation_rules_v2.3.md` §6 Evidence Status Consistency: `verification_status`는 6개 핵심값만 허용,
  `external_citation_verification.status`는 6개값 + `NOT_COMPLETED`를 별도로 허용한다 (필드 범위 한정).
- `validation_rules_v2.3.md` §8 Claim Strength Check: `strength_alignment` 필드값을 근거로 판정한다.
- MASTER v2.3 §8 Inference Control: `inference_basis` 누락 시 스키마 위반으로 처리한다.
