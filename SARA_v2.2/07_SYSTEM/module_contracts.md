# SARA v2.2 — Module Contracts

## Contract

각 module은 다음 interface를 준수한다.

```yaml
module:
  id:
  role:
  purpose:

requires: []

inputs: []

process: []

outputs: []

must_not: []

status_vocabulary: []
```

## Agent Contracts

### A1
- input: primary research document
- output: structural research summary
- must_not: unsupported inference

### A2
- input: citations, claims, external sources when required
- output: verification report
- must_not: claim verification without evidence

### A3
- input: research design and methods
- output: methodology audit
- must_not: call simulation reproduction

### A4
- input: limitations, gaps, evidence
- output: research vision
- must_not: present speculation as established finding

### A5
- input: claims, evidence, methods
- output: critical review
- must_not: arbitrary scoring without rubric

## Output Contract

모든 Agent output은 최소한 다음을 포함한다.

- Findings
- Evidence
- Verification Status
- Inference
- Uncertainty
