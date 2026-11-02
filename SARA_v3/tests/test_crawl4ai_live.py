"""Opt-in live Crawl4AI integration test against the Scrape This Site demo."""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from SARA_v3.crawl4ai_adapter import Crawl4AIContentFetcher


LIVE_ENABLED = os.environ.get("SARA_CRAWL4AI_LIVE_TEST", "").strip() == "1"
pytestmark = pytest.mark.skipif(not LIVE_ENABLED, reason="set SARA_CRAWL4AI_LIVE_TEST=1 to enable public-network integration")


def test_live_javascript_page_is_rendered_and_captured(tmp_path: Path):
    domains = {item.strip().lower().strip(".") for item in
               os.environ.get("SARA_CRAWL4AI_ALLOWED_DOMAINS", "").split(",") if item.strip()}
    if "quotes.toscrape.com" not in domains:
        pytest.skip("allowlist must explicitly include quotes.toscrape.com")
    with Crawl4AIContentFetcher(
        allowed_domains=domains, storage_dir=tmp_path / "capture",
        timeout_seconds=25, max_pages=1,
    ) as fetcher:
        result = fetcher.fetch("https://quotes.toscrape.com/js/")
    assert result["retrieval_metadata"]["retrieval_status"] == "SUCCEEDED"
    assert result["retrieval_metadata"]["extraction_status"] == "COMPLETE"
    assert result["retrieval_metadata"]["completeness_status"] == "UNKNOWN"
    assert "The world as we have created it" in result["content"]
    assert result["retrieval_metadata"]["raw_content_ref"]
    assert result["retrieval_metadata"]["markdown_ref"]
