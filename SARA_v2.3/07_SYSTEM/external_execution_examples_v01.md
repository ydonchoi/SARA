# SARA v2.3 — External Execution Examples v0.1

## Python-shaped conceptual interface

```python
response = sara.verify_claim(request)
```

The callable name is illustrative, not a committed SDK API. An implementation must conform to external_execution_contract_v01.md.

## Required behavior

- Return request identity unchanged.
- Return explicit execution status.
- Preserve external result identity and provenance.
- Preserve SARA research-verification status separately from structural validity and truthfulness.
- Reject malformed or unsupported requests explicitly.
- Never promote simulated reproduction to verification evidence.
