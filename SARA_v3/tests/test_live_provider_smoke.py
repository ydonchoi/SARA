"""Opt-in G2 live provider smoke test (docs/v3-promotion-status.md).

Run once per provider listed as supported, with the provider's credentials in the
host environment:

    SARA_V3_LIVE_SMOKE=1 SARA_LLM_PROVIDER=... SARA_LLM_MODEL=... SARA_LLM_API_KEY=...
    BRAVE_SEARCH_API_KEY=... python -m pytest -q SARA_v3/tests/test_live_provider_smoke.py

Set SARA_V3_LIVE_SMOKE_REPORT to a JSON path to keep the sanitized result as
evidence. The report never includes credentials; bind it to the candidate commit.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess

import pytest

from SARA_v3.runtime import process_turn_from_environment
from SARA_v3.verification import verify_claim_from_sources
from SARA_v3.web_search import web_search_from_environment

LIVE_ENABLED = os.environ.get("SARA_V3_LIVE_SMOKE", "").strip() == "1"
pytestmark = pytest.mark.skipif(not LIVE_ENABLED, reason="set SARA_V3_LIVE_SMOKE=1 to call live providers")

FROZEN_TURN = {
    "request_id": "LIVE-SMOKE-1", "conversation_id": "LIVE-SMOKE", "turn_id": "TURN-1",
    "content": "Sales rose after the campaign, therefore the campaign caused the increase.",
    "claim_candidates": [{"id": "C-1", "text": "The campaign caused the increase."}],
    "evidence": [], "provenance_ids": ["LIVE-SMOKE-INPUT"],
}
SECRET_ENV = ("SARA_LLM_API_KEY", "SARA_RELATION_LLM_API_KEY", "SARA_RESPONSE_LLM_API_KEY", "BRAVE_SEARCH_API_KEY")


def _candidate_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True,
                              cwd=Path(__file__).resolve().parents[2], check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNKNOWN"


def _report(name: str, result: dict) -> None:
    serialized = json.dumps(result, ensure_ascii=False, default=str)
    for var in SECRET_ENV:
        secret = os.environ.get(var, "").strip()
        assert not secret or secret not in serialized, f"{var} leaked into the result"
    path = os.environ.get("SARA_V3_LIVE_SMOKE_REPORT", "").strip()
    if not path:
        return
    report_path = Path(path)
    existing = json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else []
    existing.append({
        "check": name, "recorded_at": datetime.now(timezone.utc).isoformat(),
        "candidate_commit": _candidate_commit(),
        "provider": os.environ.get("SARA_LLM_PROVIDER"), "model": os.environ.get("SARA_LLM_MODEL"),
        "web_search_provider": os.environ.get("SARA_WEB_SEARCH_PROVIDER", "brave"),
        "result": result,
    })
    report_path.write_text(json.dumps(existing, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def test_live_judgment_and_response_providers_meet_v3_contract():
    if not os.environ.get("SARA_LLM_PROVIDER"):
        pytest.skip("SARA_LLM_PROVIDER is not configured")
    result = process_turn_from_environment(dict(FROZEN_TURN), timeout_seconds=60)
    _report("judgment_and_response", result)

    assert result["schema_version"] == "sara.dialogue-result.v3"
    assert result["judgment"]["execution_status"] == "SUCCEEDED", result["judgment"]
    assert result["judgment"]["judgment_status"] in {"INFERENCE_PRESENT", "NO_INFERENCE_DETECTED", "AMBIGUOUS"}
    assert result["truthfulness_status"] == "UNASSESSED"
    assert result["is_evidence"] is False
    response = result["external_llm_response"]
    assert response is not None and response["execution_status"] == "SUCCEEDED", response
    for envelope in result["assessment_envelopes"]:
        assert envelope["workflow_status"] == "PROPOSED"


def test_live_web_search_snippets_never_verify():
    if not os.environ.get("BRAVE_SEARCH_API_KEY"):
        pytest.skip("BRAVE_SEARCH_API_KEY is not configured")
    search = web_search_from_environment()
    results = search.search("WHO malaria fact sheet", count=3)
    assert results and all(item["url"].startswith("https://") for item in results)

    def assessor(_claim, evidence, _timeout):
        return {"evidence_id": evidence["evidence_id"], "relation": "SUPPORTS",
                "rationale": "Smoke test forces SUPPORTS on the snippet.",
                "support_spans": [evidence["snippet"][:40]] if evidence["snippet"].strip() else []}

    outcome = verify_claim_from_sources(
        {"claim": {"id": "C-1", "text": "Malaria is caused by Plasmodium parasites."}},
        search_provider=search, mcp_source=None, relation_assessor=assessor,
        trusted_source_domains={item["url"].split("/")[2] for item in results},
    )
    _report("web_search_snippet_boundary", {k: outcome[k] for k in ("status", "verification_status", "findings")})
    assert outcome["status"] == "SUCCEEDED"
    assert outcome["verification_status"] == "UNVERIFIED"
    assert "FULL_TEXT_NOT_ACCESSED" in outcome["findings"]
