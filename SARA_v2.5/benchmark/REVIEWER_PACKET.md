# SARA v2.5 Preflight — Reviewer Packet

**Version scope:** This packet evaluates only the v2.5 preflight fixture. The current integrated successor candidate is v3.0; its current status and release gates are tracked in the root README and `docs/v3-integration-design.md`.

## Purpose and status

This packet makes independent case adjudication operational. It does not mean review has begun or that the draft fixture is a gold benchmark. Do not report benchmark performance until the dataset and labels are frozen after adjudication.

## Before reviewing

1. The dataset coordinator freezes the exact `preflight_cases.json` file and records its SHA-256 digest, repository commit, and dataset version.
2. Each reviewer receives the same frozen fixture and a separate copy of `adjudication_record_template.json` for every case.
3. Reviewers must not exchange labels, rationales, or proposed corrections before both initial submissions are timestamped.
4. Reviewers assess the case specification and expected decision boundary, not whether the current prototype happens to produce the expected output.

## Per-case decision fields

- `review_disposition`: choose one of `CONFIRM_EXPECTED_LABEL`, `REVISE_EXPECTED_LABEL`, `UNASSESSABLE`, or `CASE_SPECIFICATION_DEFECT`.
- `expected_label_assessment`: `SUPPORTED`, `NOT_SUPPORTED`, or `NOT_REVIEWED`.
- `proposed_corrected_expected_label`: preserve the original expected field and provide the proposed replacement here; do not silently edit the source fixture.
- `issue_categories`: use the existing category vocabulary where applicable; explain any new category in the rationale.
- `confidence`: `LOW`, `MEDIUM`, or `HIGH`.
- `missing_context`: list information required to make the case assessable.
- `proposed_fixture_correction`: record a concrete change or use `null`.

## Reconciliation

1. Preserve both initial reviewer records unchanged.
2. Create a separate resolver record for each disagreement; record both original dispositions, the final disposition, rationale, resolver ID, and timestamp.
3. If the disagreement cannot be resolved, retain the case as unresolved and exclude it from gold-set performance calculations.
4. Log all accepted fixture corrections, increment the dataset version, recompute the fixture digest, and rerun fixture/schema tests.
5. Freeze the adjudicated dataset and label records before running the predeclared comparison. Store the evaluation outputs and environment/version details alongside the frozen dataset.

## Promotion boundary

Independent labels alone do not establish production readiness. Keep separate evidence for:
- dataset and label quality;
- comparative evaluation against the stated baselines;
- live dialogue-host/model/verifier integration;
- durable audit persistence, recovery, access control, and reviewer identity.

Until those gates are satisfied, SARA v2.4 remains canonical and SARA v2.5 remains a prototype.
