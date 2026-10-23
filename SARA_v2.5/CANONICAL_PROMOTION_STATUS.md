# SARA v2.5 Operational Trial Status

**Decision: USER-LED TRIAL APPROVED; PRODUCTION READINESS UNVERIFIED.**

The repository's v2.5 runtime and dialogue route are being promoted to the main branch so the maintainer can exercise them in real usage and report observed failures for targeted fixes. This is an operational trial decision, not a claim that every promotion-evidence gate has passed.

## Trial policy

1. Do not make the full automated test suite a precondition for this user-led trial.
2. Preserve existing v2.4 components and regression assets; v2.4 remains the rollback/comparison baseline.
3. Record errors observed during actual use with the input shape, runtime path, exception/failure output, relevant commit, and expected behavior.
4. Fix issues from observed evidence, then run targeted checks only when needed to reproduce or confirm a fix.
5. Keep provider/model configuration, host dialogue-loop integration, durable provenance storage, independent benchmark adjudication, and comparative evaluation explicitly marked unverified until evidence is supplied.
6. Do not represent an injected provider fixture, code presence, or successful import as proof of live external-provider integration or semantic claim verification.

## Current status

- User-led trial: **APPROVED**
- Main-branch promotion: pending merge of the integration PR
- Automated tests in this promotion step: intentionally not run per maintainer decision
- Live host dialogue/model/verifier integration: **UNVERIFIED**
- Independent Preflight adjudication and comparative benchmark: **NOT COMPLETED**
- Production readiness: **UNVERIFIED**
- Rollback/comparison baseline: **SARA v2.4**

This status supersedes the earlier blanket `PROMOTION_BLOCKED` label only for the limited purpose of a user-led trial. It does not waive or claim completion of production-release evidence.
