# Explanation Output Protocol — SARA v0.1

**Status:** Active documentation guidance / design-level  
**Applies to:** SARA v3.0.0 documentation, assessment explanations, research-analysis reports, and human-facing review artifacts  
**Does not change:** Runtime schemas, verification states, evidence contracts, provider permissions, or commit gates.

## 1. Purpose

SARA may explain its analysis through structured text, diagrams, charts, annotated images, interactive pages, animations, or explainer videos when the selected format materially improves understanding.

The format is a presentation layer. It must not change the underlying claim, evidence, provenance, uncertainty, verification status, or workflow status.

## 2. Format Selection

| Information to communicate | Preferred representation |
|---|---|
| Claim definition, scope, qualification | Structured text |
| Claim-premise-evidence relationships | Claim-evidence graph or table |
| Evidence support/challenge/mixed relations | Evidence alignment diagram plus source spans |
| Workflow and status transitions | State-transition diagram |
| System components and interfaces | Architecture and data-flow diagrams |
| Quantitative evidence | Charts with units, denominators, time range, and source |
| Temporal or causal mechanism | Sequence diagram or carefully qualified animation |
| Alternative assumptions and outcomes | Scenario table or explicitly labeled simulation |
| Reviewer exploration | Interactive evidence browser, if available |

Use the simplest format that preserves all material information. A visual artifact is optional; it is not a required output for every assessment.

## 3. Epistemic and Status Invariants

1. VERIFIED, PARTIALLY_VERIFIED, UNVERIFIED, and other SARA statuses must retain their exact meaning and scope.
2. PROPOSED and committed workflow states must remain distinct.
3. truthfulness_status=UNASSESSED must not be visually implied to mean verified or false.
4. A model judgment, source relation proposal, chart, or diagram is not itself evidence.
5. Agreement between models or reviewers does not promote a claim's verification status.
6. Missing, conflicting, stale, inaccessible, or out-of-scope evidence must remain visible.
7. Visual emphasis must not overstate confidence. Use explicit labels and textual qualifiers.
8. A generated illustration or simulation must never be presented as source material or an observed event.

## 4. Evidence Traceability for Visual Outputs

For each material claim shown in a chart, graph, diagram, or interactive view, preserve links or identifiers to:

- claim_id, claim_revision_id, and claim scope
- evidence_id and source URL/identifier
- Exact supporting or challenging source span, where available
- Source access level (SEARCH_SNIPPET, METADATA, ABSTRACT, FULL_TEXT, or UNAVAILABLE)
- Retrieval/check timestamp
- Evidence relation proposal and its status
- Known conflicts, limitations, and uncertainty

For quantitative charts, also preserve metric definition, unit, denominator, population, time range, transformations, missing-data treatment, and source. Do not infer values from visual appearance.

## 5. Diagram and Chart Rules

- Use arrows only for a defined relationship or direction of flow.
- Distinguish temporal order, causal claims, logical dependency, and simple association.
- Label hypothetical or inferred edges.
- Show relevant denominators, units, axes, time ranges, and uncertainty.
- Do not hide contradictory evidence or material outliers merely to simplify a chart.
- If data are illustrative or synthetic, label them prominently.
- Keep a text equivalent for diagrams and charts when practical.

## 6. Interactive and Video Artifacts

Interactive pages must state their inputs, transformations, outputs, and assumptions. They must not allow user interaction to silently alter SARA's canonical verification state or durable ledger. Any state-changing action remains subject to the existing host authorization and review/commit contracts.

Animations and videos may explain a workflow or concept. They must not fabricate source excerpts, evidence, experimental observations, or actual runtime behavior. Provide a transcript or scene outline and identify illustrative sequences.

## 7. Technical Explanation Style

For complex technical or operational explanations, use concise, controlled language inspired by aircraft maintenance documentation and ASD-STE100:

- One main idea per sentence.
- Define terms and use them consistently.
- Separate facts, assumptions, inferences, and recommendations.
- Explain inputs, operations, outputs, decision criteria, exceptions, and failure paths.
- Preserve important qualifications and technical details.

This is an editorial reference, not a claim of formal ASD-STE100 compliance.

## 8. Output and Verification Reporting

When a visual or interactive artifact is produced, report its status accurately:

- Selected: format chosen
- Generated: artifact created
- Rendered: rendering checked
- Functionally tested: interaction tested
- Source verified: underlying source data checked
- Unverified / Blocked: checks not performed and why

Do not claim that an artifact is integrated into the SARA runtime unless an implementation and integration test demonstrate that behavior. Documentation-level adoption does not implement automatic visualization.

## 9. Compatibility

This protocol supplements the SARA v3 contracts and engineering principles. It does not authorize:

- Changes to assessment schemas or verification-state semantics
- Promotion of a claim based on visual presentation
- Treating retrieval or rendering success as evidence verification
- Bypassing provenance, reviewer, or commit requirements
- Sending evidence or user content to an external service without existing authorization

The canonical SARA v3 runtime and its verification boundaries remain authoritative.
