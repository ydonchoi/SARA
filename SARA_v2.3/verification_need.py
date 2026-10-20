"""Rule-based verification-need triage for general conversational claims.

This module decides whether a claim should be sent to a verifier; it does not
establish truth, replace human judgment, or perform external retrieval itself.
The deterministic rules are intentionally inspectable and return reason codes.
"""
from __future__ import annotations

import re
from typing import Any, Mapping

RULESET_VERSION = "verification-need-rules-v1"

_EXPLICIT_VERIFY = re.compile(
    r"\b(verify|fact.?check|validate|source|citation|evidence)\b|"
    r"(검증|사실.?확인|출처|근거|팩트체크|확인해\s*줘|검토해\s*줘)",
    re.IGNORECASE,
)
_TIME_SENSITIVE = re.compile(
    r"(today|currently|latest|recent|now|this week|this month|as of|"
    r"오늘|현재|최신|최근|이번 주|이번달|지금|올해|내년|어제)",
    re.IGNORECASE,
)
_HIGH_STAKES = re.compile(
    r"(medical|medicine|diagnos|treatment|dosage|legal|lawsuit|"
    r"investment|stock|financial|tax|election|vote|emergency|safety|"
    r"의학|의료|진단|치료|복용량|법률|소송|투자|주식|금융|세금|"
    r"선거|투표|응급|안전|자해|위험)",
    re.IGNORECASE,
)
_CITATION_OR_URL = re.compile(r"https?://|\bdoi\s*:|\b10\.\d{4,9}/|\[[^\]]+\]\([^)]*\)", re.I)
_QUANTITATIVE = re.compile(r"(?<!\w)(?:\d+(?:[.,]\d+)*%?|\d{4}[-./]\d{1,2}(?:[-./]\d{1,2})?)(?!\w)")
_ASSERTIVE_CLAIM = re.compile(
    r"( is | are | was | were | has | have | causes? | means? | proves? | "
    r"equals? | increased | decreased | will | must | should )|"
    r"(이다|있다|없다|한다|된다|높인다|유발한다|보인다|작용한다|발생한다|포함한다|때문이다|증가했다|감소했다|예정이다|필수다|최초다|최고다)",
    re.IGNORECASE,
)


def assess_verification_need(
    text: str,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return an auditable triage decision; never label the claim as true/false."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("CLAIM_TEXT_REQUIRED")
    context = context or {}
    if not isinstance(context, Mapping):
        raise ValueError("CONTEXT_MUST_BE_OBJECT")

    reasons: list[str] = []
    if context.get("explicit_verification_request") is True or _EXPLICIT_VERIFY.search(text):
        reasons.append("EXPLICIT_VERIFICATION_REQUEST")
    if context.get("high_stakes") is True or _HIGH_STAKES.search(text):
        reasons.append("HIGH_STAKES_DOMAIN")
    factual_query = bool(re.search(
        r"(얼마|몇\s*(?:원|명|개|퍼센트|%|년|월|일)?|누구|언제|어디|무엇|어떤|왜|"
        r"how much|how many|what|who|when|where|rate|price|날씨|환율|기준금리|시세)",
        text,
        re.IGNORECASE,
    ))
    temporal_cue = bool(_TIME_SENSITIVE.search(text))
    if context.get("time_sensitive") is True or (
        temporal_cue and (
            factual_query
            or context.get("factual_query") is True
            or context.get("high_stakes") is True
            or context.get("quantitative_claim") is True
        )
    ):
        reasons.append("TIME_SENSITIVE_CLAIM")
    if context.get("contains_citation") is True or _CITATION_OR_URL.search(text):
        reasons.append("SOURCE_OR_CITATION_CHECK")
    if context.get("quantitative_claim") is True or _QUANTITATIVE.search(text):
        reasons.append("QUANTITATIVE_OR_DATE_CLAIM")
    if context.get("assertive_claim") is True or _ASSERTIVE_CLAIM.search(f" {text} "):
        reasons.append("FACTUAL_OR_CAUSAL_ASSERTION")

    required_reasons = {
        "EXPLICIT_VERIFICATION_REQUEST",
        "HIGH_STAKES_DOMAIN",
        "TIME_SENSITIVE_CLAIM",
        "SOURCE_OR_CITATION_CHECK",
        "QUANTITATIVE_OR_DATE_CLAIM",
    }
    required = any(reason in required_reasons for reason in reasons)
    if required:
        decision, external_check = "VERIFY", True
    elif "FACTUAL_OR_CAUSAL_ASSERTION" in reasons:
        decision, external_check = "REVIEW", False
    else:
        decision, external_check = "NO_AUTOMATIC_CHECK", False

    return {
        "decision": decision,
        "verification_required": required,
        "external_check_recommended": external_check,
        "reason_codes": reasons,
        "ruleset_version": RULESET_VERSION,
        "claim_text": text.strip(),
        "epistemic_boundary": (
            "Triage only: this result does not assess truth, source quality, "
            "or whether the claim is ultimately supported."
        ),
    }
