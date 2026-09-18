# SARA v2.2 — Evidence-Centered Research Analysis System

SARA v2.2는 v2.1의 모듈식 구조에 **Dependency & Loading Architecture**를 추가한 버전이다.

## Architecture

```text
SARA_v2.2/
├─ 00_MASTER/
├─ 01_CORE/
├─ 02_ROUTER/
├─ 03_AGENTS/
├─ 04_ANALYSIS/
├─ 05_OUTPUT/
├─ 06_SCHEMA/
└─ 07_SYSTEM/
   ├─ dependency_map.md
   ├─ loading_rules.md
   ├─ module_contracts.md
   ├─ validation_rules.md
   └─ architecture_audit.md
```

## v2.1 → v2.2

### v2.1
모듈의 논리적 분리.

### v2.2
모듈의 **실행 관계까지 명시**.

핵심 추가 요소:

1. Dependency Map
2. Loading Rules
3. Module Contracts
4. Validation Rules
5. Architecture Audit

## 실행 개념

```text
User Request
    ↓
MASTER
    ↓
ROUTER
    ↓
Dependency Resolution
    ↓
Minimal Loading
    ↓
Agent + Analysis
    ↓
Schema Validation
    ↓
Output
    ↓
Uncertainty / Confession
```

## 핵심 원칙

> **파일이 존재하는 것과 시스템이 파일을 사용할 수 있는 것은 다르다.**

v2.2는 두 번째 문제까지 다룬다.
