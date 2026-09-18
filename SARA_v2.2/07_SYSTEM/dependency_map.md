# SARA v2.2 — Dependency Map

## Purpose

모듈 간의 명시적 dependency를 정의한다.

## Global Dependency

모든 실행은 다음을 기본적으로 상속한다.

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

### /방법론

```yaml
route: /방법론
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 02_ROUTER/trigger_map.md
  - 03_AGENTS/A3_methodologist.md
  - 04_ANALYSIS/methodology_audit.md
  - 06_SCHEMA/research_schema.md
  - 05_OUTPUT/agent_report.md
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
```

### /통합

```yaml
route: /통합
requires:
  - 00_MASTER/00_SARA_MASTER.md
  - 01_CORE/*
  - 02_ROUTER/*
  - 03_AGENTS/*
  - 04_ANALYSIS/*
  - 06_SCHEMA/*
  - 05_OUTPUT/executive.md
  - 05_OUTPUT/verification.md
  - 05_OUTPUT/confession.md
```

## Dependency Direction

권장 방향:

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

하위 모듈이 상위 모듈의 원칙을 재정의하지 않는다.
