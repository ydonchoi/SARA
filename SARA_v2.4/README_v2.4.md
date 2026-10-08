# SARA
## Evidence-Centered Research Analysis & Epistemic Verification System

SARA (**Senior Academic Research Architect**)는 연구의 Claim → Premise → Evidence → Method → Verification → Inference → Uncertainty 구조를 추적하고, source provenance와 검증 상태를 분리하여 연구 판단을 지원한다.

현재 canonical architecture는 **v2.4**다. v2.3의 실행·검증 경계를 보존하면서 Co-thoughts v2.0의 source-grounded depth와 inference 생성 흐름을 지원한다.

## Version Overview

| Version | Focus |
|---|---|
| v1.0 | 초기 연구 분석 프레임워크 |
| v2.1 | 모듈화 |
| v2.2 | Dependency / Loading / Contract |
| v2.3 | Verification Layer Separation / Reproduction / Runtime Boundary |
| **v2.4** | **Co-thoughts Integration / Premise Evaluation / Provenance / Temporal & Interpretive Context** |

## v2.4 Architecture

~~~text
                 SARA v2.4
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
 Knowledge Gate  Thought Gate  System Gate
        │           │           │
     External     Dialogue     Runtime
     Evidence     Claims       Integrity
        │           │
        └──────┬────┘
               ▼
       Claim Evaluation State
               │
       ┌───────┼────────┐
       ▼       ▼        ▼
    Premise  Evidence  Provenance
    Eval     Alignment Lineage
       │       │        │
       └───────┼────────┘
               ▼
      Temporal / Interpretive
             Context
               │
               ▼
           Verification
               │
               ▼
            Revision
~~~

## 1. Knowledge Gate

외부 source, background knowledge, supporting/challenging evidence를 검토한다.

핵심 질문:

> 이 자료를 특정 Claim 또는 Premise의 근거로 사용할 수 있는가?

기존 verification sequence를 유지한다.

~~~text
Existence
 ↓
Bibliographic Accuracy
 ↓
Content
 ↓
Citation Fit
 ↓
Evidence Strength
~~~

## 2. Thought Gate

Co-thoughts 대화에서 생성된 Inference / New Claim / New Premise를 검증한다.

핵심 질문:

> 대화에서 생성된 이 주장을 현재 근거로 지식으로 승격할 수 있는가?

**대화에서 생성된 사실이 SARA에 입력되었다는 이유만으로 verification status가 상승하지 않는다.**

## 3. Claim Evaluation State v2.4

Claim과 Premise의 상태를 별도 객체로 관리한다.

~~~yaml
claim:
  id:
  text:
  type:
  verification_status:
  attribution_status:
  temporal_status:
  uncertainty:
  provenance_ids:

premises:
  - id:
    text:
    type:
    verification_status:
    provenance_ids:

evidence:
  - id:
    source_type:
    supports_claim:
    supports_premise:
    challenges_claim:
    challenges_premise:
    alignment_status:
    provenance_ids:
~~~

### Type
FACT / INTERPRETATION / INFERENCE / HYPOTHESIS / SIMULATION

### Verification
VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / CONTRADICTED

### Attribution
AUTHOR_EXPLICIT / AUTHOR_SUPPORTED / SOURCE_INFERRED / MODERN_INTERPRETATION / SPECULATIVE / UNKNOWN

### Temporal
HISTORICAL / POST_PUBLICATION / CONTEMPORARY

## 4. Premise Evaluation

v2.4는 Claim 자체뿐 아니라 Claim을 구성하는 결정적 Premise를 평가한다.

검토 항목:
- premise existence
- premise type
- premise evidence
- claim–premise dependency
- premise–evidence alignment
- contradiction
- boundary condition
- uncertainty

**Premise verification은 Claim verification과 동일하지 않다.**

## 5. Context Evidence Alignment

Background knowledge는 단순 관련성으로 승인하지 않는다.

각 context item은 다음 중 하나 이상의 관계를 가진다.

- SUPPORTING
- CHALLENGING
- NEUTRAL

그리고 구체적으로 어떤 Claim / Premise를 지지·반박하는지 기록한다.

## 6. Temporal & Interpretive Context

SARA는 source의 역사적 시점과 현재의 해석을 분리한다.

### Temporal
- HISTORICAL
- POST_PUBLICATION
- CONTEMPORARY

### Interpretive
- AUTHOR_EXPLICIT
- SOURCE_GROUNDED
- FIELD_INTERPRETATION
- MODERN_INTERPRETATION
- SPECULATIVE

핵심 invariant:

> **MODERN_INTERPRETATION must not be promoted to AUTHOR_EXPLICIT without source evidence.**

후대의 evidence는 당시 저자가 이용 가능했던 evidence로 소급되지 않는다.

## 7. Attribution Firewall

다음 promotion을 기본적으로 차단한다.

~~~text
MODERN_INTERPRETATION
        X
        ↓
AUTHOR_EXPLICIT
~~~

또한:

~~~text
MODEL_INFERENCE
        X
        ↓
SOURCE_CLAIM
~~~

저자의 실제 주장으로 승격하려면 source-grounded evidence가 필요하다.

## 8. Provenance Event Ledger

검증 결과와 판단 상태의 출처를 이벤트 단위로 추적한다.

가능한 event source:
- SOURCE
- HUMAN
- MODEL
- DIALOGUE
- INFERENCE
- EXTERNAL_EVIDENCE
- VERIFICATION
- REVISION

목표:

> Claim / Premise가 어디에서 생성되어 어떤 evidence와 검증을 거쳐 현재 상태에 도달했는가?

를 재구성할 수 있게 하는 것이다.

## 9. Dual Verification Flow

~~~text
[Knowledge Gate]
External Source
 → Context Item
 → Claim/Premise Alignment
 → Verification
 → Co-thoughts

[Thought Gate]
Human ↔ Co-thoughts
 → Inference / New Claim / Premise
 → Verification
 → Epistemic State
 → Revision
~~~

두 흐름은 provenance와 event lineage를 공유하지만, origin은 혼동하지 않는다.

## 10. Existing v2.3 Safety Boundaries

v2.3의 다음 경계를 그대로 유지한다.

- System Verification ≠ Research Verification
- Execution success ≠ Research validity
- Simulation ≠ Reproduction
- Model output ≠ Evidence
- Evidence self-promotion = rejected
- Backend self-verification = rejected
- Fail-closed on verification execution failure
- Provider boundary and provenance retention remain mandatory

## 11. Jev Boundary

Jev는 deterministic verification을 대체하지 않는다.

Jev가 연결되는 경우:
- Claim classification
- Evidence status classification
- Review need judgment
- Contradiction detection
- Critical claim selection
- Confession candidate selection
- Rubric-based evaluation

Jev의 결과는 decision-support signal이며 research evidence가 아니다.

## 12. Co-thoughts Integration Contract

Co-thoughts는 다음 구조로 SARA를 호출할 수 있다.

~~~yaml
integration:
  source: co-thoughts
  operation: knowledge_gate | thought_gate
  claim_id:
  premise_ids:
  evidence_ids:
  source_ids:
  temporal_context:
  interpretive_context:
  attribution_status:
  provenance_ids:
  requested_capability:
~~~

SARA는 verification result와 provenance event를 반환한다.

Co-thoughts는 이를 사고 상태에 반영할 수 있지만 **verification result 자체를 새로운 evidence로 취급하지 않는다.**

## 13. Output Boundary

SARA는 다음을 구분한다.

- verification result
- evidence
- inference
- decision-support signal
- system execution status

이들은 서로 승격되지 않는다.

## 14. Migration from v2.3

v2.3:
- Claim → Evidence → Method → Verification → Inference → Uncertainty
- System / Research verification separation
- A6 Simulator/Reproducer
- Runtime execution boundary

v2.4 adds:
- Claim × Premise evaluation
- Knowledge Gate
- Thought Gate
- Context Evidence Alignment
- Temporal & Interpretive Context
- Attribution Firewall
- Provenance Event Ledger
- Co-thoughts integration contract

기존 v2.3 snapshot은 보존한다.

## 15. Current Status

**Version: v2.4**
**Status: ACTIVE / INTEGRATION BASELINE**

v2.4는 Co-thoughts v2.0과 연결되는 verification baseline이다.
