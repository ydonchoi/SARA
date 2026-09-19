# SARA v2.3 — Dependency Map

## Purpose

모듈 간 명시적 dependency를 정의한다. v2.3에서는 SYSTEM 계층이 MASTER를 requires로 선언하지 않음으로써
v2.2에서 발견된 MASTER ↔ SYSTEM 순환 dependency(Architecture Audit 🔴 FAIL 항목)를 제거한다.

## SYSTEM Layer 위상 (변경)

SYSTEM(본 파일, loading_rules, module_contracts, validation_rules)은 **control authority**로서
MASTER 이하 모든 계층의 로드/충돌해결/검증 방식을 규정하는 meta layer이다.
SYSTEM 파일은 어떤 경우에도 `00_MASTER/00_SARA_MASTER.md`를 자신의 `requires` 목록에 포함하지 않는다.

```
                 SYSTEM (control authority)
        ┌───────────┼───────────┬───────────┐
   dependency    loading     validation   contract
        │
        ▼ (통제, requires 아님)
      MASTER (content authority)
        ↓
      CORE
        ↓
      ROUTER
        ↓
  AGENT / ANALYSIS
        ↓
      SCHEMA
        ↓
      OUTPUT
```

## Global Dependency (MASTER 이하 계층용)

```yaml
global:
  requires:
    - 00_MASTER/00_SARA_MASTER.md
    - 01_CORE/identity.md
    - 01_CORE/principles.md
    - 01_CORE/uncertainty.md
```

`source_policy.md`는 외부 검증 또는 source hierarchy 판단이 필요한 route에서 필수로 로드한다.

## Route Dependencies

### /요약
```yaml
route: /요약
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 03_AGENTS/A1_summarizer.md
  - 04_ANALYSIS/research_mapping.md
  - 06_SCHEMA/research_schema.md
  - 05_OUTPUT/agent_report.md
conditional:
  - 05_OUTPUT/confession.md  # 중요 unverified claim 발견 시
```

### /검증
```yaml
route: /검증
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 01_CORE/source_policy.md
  - 03_AGENTS/A2_investigator.md
  - 04_ANALYSIS/citation_audit.md
  - 04_ANALYSIS/claim_evidence.md
  - 06_SCHEMA/claim_schema.md
  - 06_SCHEMA/evidence_schema.md
  - 05_OUTPUT/verification.md
  - 05_OUTPUT/confession.md
```

### /방법론 (A3 — Audit 관점)
```yaml
route: /방법론
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 03_AGENTS/A3_methodologist.md
  - 04_ANALYSIS/methodology_audit.md
  - 06_SCHEMA/research_schema.md
  - 05_OUTPUT/agent_report.md
conditional:
  - 05_OUTPUT/confession.md  # 중요 unverified claim 발견 시
must_not_include:
  - 03_AGENTS/A6_simulator.md  # 실행/코드 생성은 A3 영역이 아님
```

### /재현 (A6 — Execution 관점, v2.3 신규)
```yaml
route: /재현
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 03_AGENTS/A3_methodologist.md  # 변수/표본/도구 구조를 입력으로 참조
  - 03_AGENTS/A6_simulator.md
  - 04_ANALYSIS/methodology_audit.md
  - 06_SCHEMA/research_schema.md
  - 05_OUTPUT/agent_report.md
  - 05_OUTPUT/simulation_report.md
  - 05_OUTPUT/confession.md
```

### /인사이트
```yaml
route: /인사이트
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 01_CORE/uncertainty.md
  - 03_AGENTS/A4_visionary.md
  - 04_ANALYSIS/research_gap.md
  - 05_OUTPUT/agent_report.md
  - 05_OUTPUT/confession.md
```

### /비평
```yaml
route: /비평
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 03_AGENTS/A5_reviewer.md
  - 04_ANALYSIS/critical_review.md
  - 04_ANALYSIS/claim_evidence.md
  - 05_OUTPUT/agent_report.md
conditional:
  - 05_OUTPUT/confession.md  # 중요 unverified claim 발견 시
```

### /통합 (wildcard 제거 — Architecture Audit 🟡 PARTIAL 항목 해결)

v2.2는 `02_ROUTER/*`, `03_AGENTS/*`, `04_ANALYSIS/*`, `06_SCHEMA/*` 형태의 wildcard를 사용하여
resolver 입장에서 closure가 불명확했다. v2.3은 Default Workflow 순서에 맞춘 명시적 목록을 사용한다.

```yaml
route: /통합
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 01_CORE/identity.md
  - 01_CORE/principles.md
  - 01_CORE/source_policy.md
  - 01_CORE/uncertainty.md
  - 02_ROUTER/trigger_map.md
  - 02_ROUTER/workflow.md
  - 03_AGENTS/A1_summarizer.md
  - 04_ANALYSIS/research_mapping.md
  - 03_AGENTS/A2_investigator.md
  - 04_ANALYSIS/citation_audit.md
  - 04_ANALYSIS/claim_evidence.md
  - 03_AGENTS/A3_methodologist.md
  - 04_ANALYSIS/methodology_audit.md
  - 03_AGENTS/A5_reviewer.md
  - 04_ANALYSIS/critical_review.md
  - 03_AGENTS/A4_visionary.md
  - 04_ANALYSIS/research_gap.md
  - 06_SCHEMA/research_schema.md
  - 06_SCHEMA/claim_schema.md
  - 06_SCHEMA/evidence_schema.md
  - 05_OUTPUT/executive.md
  - 05_OUTPUT/verification.md
  - 05_OUTPUT/confession.md
optional:
  - 03_AGENTS/A6_simulator.md      # 사용자가 재현/시뮬레이션을 별도 요청한 경우에만 추가
  - 05_OUTPUT/simulation_report.md
```

## Dependency Direction

권장 방향 (SYSTEM은 통제 계층으로 별도 취급, 화살표 방향의 일부가 아님):

```text
MASTER
  ↓
CORE
  ↓
ROUTER
  ↓
AGENT / ANALYSIS
  ↓
SCHEMA
  ↓
OUTPUT
```

하위 모듈이 상위 모듈의 원칙을 재정의하지 않는다. SYSTEM은 이 방향성 위에 존재하는 control layer이며 방향성 그래프의 노드가 아니다 (따라서 cycle 판정 대상에서 제외).
