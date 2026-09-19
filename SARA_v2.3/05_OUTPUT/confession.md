# SARA v2.3 — Confession Report Template

v2.2의 8개 섹션 구조를 유지하되, System/Research Verification 분리와 Reproduction 관련 항목을
명시적으로 추가했다.

## 템플릿

```markdown
# Confession Report

## 1. Directly Verified
원문 또는 권위 있는 자료에서 직접 확인한 내용 (research_verification 층위).

## 1a. System Access Status (v2.3 신규)
07_SYSTEM 파일 접근·로딩과 관련해 확인되지 않은 부분이 있다면 여기에만 기록한다.
이 항목의 내용은 "1. Directly Verified" 및 "5. Unverified"(연구 내용 관련)와 절대 병합하지 않는다
(validation_rules_v2.3.md §11 Verification Layer Separation).

## 2. Externally Verified
외부 자료를 통해 추가 확인한 내용. 외부 검색을 수행하지 않은 인용문헌은 여기 기재하지 않고
verification_v2.3.md의 External Citation Verification 섹션(status: NOT_COMPLETED)에 기록한다.

## 3. Inferred
근거로부터 SARA가 추론한 내용. claim_schema_v2.3.md의 `inference_basis`가 채워진 항목만 여기 요약한다.

## 4. Hypothesized
추가 검증이 필요한 가설.

## 5. Unverified
확인하지 못한 연구 내용과 이유 (research_verification 층위 한정. 시스템 파일 접근 문제는 "1a"에 기재).

## 6. Missing Evidence
정확한 판단을 위해 필요한 추가 자료.

## 7. Reproduction Note (v2.3 신규 — A6 실행 시 필수)
- Reproduction Status: FULL_REPRODUCTION_AVAILABLE / SIMULATED_REPRODUCTION / REPRODUCTION_UNAVAILABLE
- Simulated Reproduction인 경우, 그 결과가 어떤 claim의 verification에도 사용되지 않았음을
  명시적으로 확인한다 (evidence_schema_v2.3.md `usable_as_verification_evidence: false` 준수 확인).

## 8. Largest Uncertainty
전체 분석에서 가장 중요한 불확실성. system 층위와 research 층위 중 어느 쪽 불확실성인지 명시한다.

## 9. Potential Failure Modes
분석이 틀릴 수 있는 주요 경로.
```

## Validation 연동

- `validation_rules_v2.3.md` §10 Confession Requirement: 중요한 uncertainty 또는 unverified claim 발견 시
  본 문서를 로드한다 (모든 라우트에 조건부 적용, dependency_map_v2.3.md 참조).
- `validation_rules_v2.3.md` §11: "1a. System Access Status"와 "5. Unverified"를 절대 하나로 합치지 않는다 —
  이는 v2.2에서 발견된 "시스템 파일 접근 실패가 연구결과 검증 상태를 오염시키는" 문제를 confession 단계에서도
  재발시키지 않기 위한 조치다.
