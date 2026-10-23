# SARA Runtime and Verification Provider Integration

**Status:** Implemented on the feature branch; live deployment verification remains environment-dependent.  
**Canonical baseline:** SARA v2.4 remains unchanged and canonical.

## Default provider

The callable runtime now defaults to `sara_crossref_provider:verify`. The provider uses the public Crossref REST API to resolve a DOI and confirm DOI identity and bibliographic metadata. No API key is required. Optionally set `CROSSREF_MAILTO` to identify the client to Crossref.

Example request:

```json
{
  "request_id": "demo-001",
  "capability": "verify_claim",
  "claim": {
    "id": "C1",
    "text": "A claim that should be checked against a cited source.",
    "inference_level": "FACT",
    "evidence_ids": ["E1"]
  },
  "evidence": [
    {
      "id": "E1",
      "doi": "10.xxxx/example-doi",
      "supports_claims": ["C1"],
      "evidence_type": "published_source",
      "verification_layer": "research_verification"
    }
  ],
  "provenance_ids": ["INPUT-001"],
  "adapter_revision": "runtime-provider-v1",
  "requested_at": "2026-10-24T00:00:00Z",
  "environment": {"deployment": "local"}
}
```

Run from the repository root:

```bash
python sara_runtime.py --request request.json
```

A custom provider remains supported:

```bash
python sara_runtime.py --provider package.module:verify --request request.json
```

Alternatively, send the request JSON to standard input by omitting `--request` or using `--request -`.

## Important verification boundary

Crossref registration confirms a DOI record and bibliographic metadata; it does **not** verify a substantive claim in the cited work. Therefore the integrated A2 pipeline marks the scope as `BIBLIOGRAPHIC_METADATA` and must keep the claim `UNVERIFIED`. The result's citation metadata status may be `VERIFIED` while the claim-level verification status remains `UNVERIFIED`. This is intentional and fail-closed.

The default provider requires the DOI evidence to be explicitly bound to the requested claim using `claim.evidence_ids` or `evidence.supports_claims`. Missing or unbound evidence is rejected. To verify substantive claims, a separate authorized full-text/content provider and a reviewed content-level evidence path are still required; Crossref metadata must never be promoted as article full text.

## Execution and verification status

- **Implemented:** default provider selection, Crossref DOI lookup, A2 pipeline wiring, and CLI request defaults.
- **Not implied:** successful live execution in every deployment, semantic claim verification, or v2.5 promotion.
- **Deployment requirements:** outbound HTTPS access to `api.crossref.org`; optional `CROSSREF_MAILTO`; appropriate source evidence and explicit claim binding.
- **Version boundary:** this entrypoint integrates the existing v2.3 execution facade and does not replace the v2.4 canonical verification baseline.
