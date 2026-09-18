# SARA v2.1 — Evidence-Centered Research Analysis System

## Purpose

SARA v2.1은 하나의 거대한 Master Prompt 대신 **Master + Core + Router + Agents + Analysis + Schema + Output**으로 분리된 계층형 연구 분석 시스템이다.

핵심 구조:

> **Claim → Evidence → Method → Verification → Inference → Uncertainty**

## Directory

```text
SARA_v2.1/
├─ 00_MASTER/
├─ 01_CORE/
├─ 02_ROUTER/
├─ 03_AGENTS/
├─ 04_ANALYSIS/
├─ 05_OUTPUT/
└─ 06_SCHEMA/
```

## 사용 순서

1. `00_MASTER/00_SARA_MASTER.md`를 기본 지침으로 사용
2. 사용자 요청을 `02_ROUTER/trigger_map.md`에 따라 라우팅
3. 해당 Agent와 Analysis/Schema 파일만 로드
4. 결과를 Output template에 맞춰 생성
5. 필요할 때만 전체 pipeline 실행

## 권장 명령

- `/요약`
- `/검증`
- `/방법론`
- `/인사이트`
- `/비평`
- `/통합`

## 설계 원칙

- 모든 파일을 매번 읽지 않는다.
- 확인되지 않은 내용을 채우지 않는다.
- 원문 주장과 SARA의 해석을 구분한다.
- 내부 Chain-of-Thought는 출력하지 않는다.
- 실제 재현과 시뮬레이션을 구분한다.
- 연구 유형에 맞지 않는 변수를 강제하지 않는다.
- 정량 점수와 백분율을 근거 없이 생성하지 않는다.
