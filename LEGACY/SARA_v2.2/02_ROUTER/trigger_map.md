# Trigger Map

| Trigger | Route | Required Sources |
|---|---|---|
| /요약 | A1 | research_mapping + research_schema |
| /검증 | A2 | citation_audit + claim_evidence |
| /방법론 | A3 | methodology_audit + research_schema |
| /인사이트 | A4 | research_gap + uncertainty |
| /비평 | A5 | critical_review + claim_evidence |
| /통합 | Full Pipeline | 전체 관련 모듈 |

자연어 요청은 의미적으로 동일한 route를 사용한다.


## Dependency Resolution

라우팅 후 `07_SYSTEM/dependency_map.md`를 참조하여 route별 필수 모듈을 결정한다.
그 다음 `07_SYSTEM/loading_rules.md`에 따라 최소 충분 모듈만 로드한다.
