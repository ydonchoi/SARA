# SARA v2.2 — Architecture Audit

## Audit Checklist

### Hierarchy
- [ ] MASTER가 최상위 규칙인가?
- [ ] CORE가 공통 원칙을 담당하는가?
- [ ] ROUTER가 실행 경로를 결정하는가?
- [ ] AGENT가 역할을 수행하는가?
- [ ] ANALYSIS가 분석 절차를 정의하는가?
- [ ] SCHEMA가 데이터 구조를 정의하는가?
- [ ] OUTPUT이 결과 표현을 담당하는가?

### Dependency
- [ ] 각 Agent의 필수 dependency가 선언되어 있는가?
- [ ] 각 route의 loading set이 정의되어 있는가?
- [ ] 순환 dependency가 없는가?
- [ ] orphan module이 없는가?

### Consistency
- [ ] 동일 규칙이 서로 다르게 정의되지 않았는가?
- [ ] Agent output과 Schema가 일치하는가?
- [ ] Verification vocabulary가 일관적인가?
- [ ] Research-type policy가 일관적인가?

### Epistemic Control
- [ ] FACT와 INFERENCE가 구분되는가?
- [ ] HYPOTHESIS와 SPECULATION이 구분되는가?
- [ ] UNVERIFIED 정보가 사실처럼 표현되지 않는가?
- [ ] Primary Source와 external evidence가 구분되는가?

### Efficiency
- [ ] 불필요한 module을 로드하지 않는가?
- [ ] `/통합`에서만 전체 pipeline을 사용하는가?
