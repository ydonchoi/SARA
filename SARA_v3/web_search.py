"""Built-in Brave web-search adapter; results are snippets, never verification."""
from __future__ import annotations

import hashlib
import json
import os
import socket
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class WebSearchError(RuntimeError):
    """Sanitized web-search configuration or transport failure."""


Sender = Callable[[str, Mapping[str, str], float], bytes]


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _send(url: str, headers: Mapping[str, str], timeout: float) -> bytes:
    opener = build_opener(_NoRedirect(), ProxyHandler())
    try:
        with opener.open(Request(url, headers=dict(headers)), timeout=timeout) as response:
            body = response.read(2_000_001)
        if len(body) > 2_000_000:
            raise WebSearchError("WEB_SEARCH_RESPONSE_TOO_LARGE")
        return body
    except HTTPError as exc:
        raise WebSearchError(f"WEB_SEARCH_HTTP_ERROR_{exc.code}") from None
    except (socket.timeout, TimeoutError):
        raise TimeoutError("WEB_SEARCH_TIMEOUT") from None
    except URLError:
        raise WebSearchError("WEB_SEARCH_NETWORK_ERROR") from None
    except OSError:
        raise WebSearchError("WEB_SEARCH_NETWORK_ERROR") from None


class BraveWebSearchProvider:
    endpoint = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str | None = None, *, sender: Sender | None = None, timeout_seconds: float = 10.0):
        self.api_key = (api_key if api_key is not None else os.environ.get("BRAVE_SEARCH_API_KEY", "")).strip()
        self._sender = sender or _send
        self.timeout_seconds = timeout_seconds

    def search(self, query: str, *, count: int = 8, country: str = "US", search_lang: str = "en") -> list[dict[str, Any]]:
        if not self.api_key:
            raise WebSearchError("BRAVE_SEARCH_API_KEY_REQUIRED")
        if not isinstance(query, str) or not query.strip() or len(query) > 600 or len(query.split()) > 75:
            raise WebSearchError("WEB_SEARCH_QUERY_INVALID")
        if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 20:
            raise WebSearchError("WEB_SEARCH_COUNT_INVALID")
        params = urlencode({"q": query.strip(), "count": count, "country": country, "search_lang": search_lang})
        raw = self._sender(f"{self.endpoint}?{params}", {
            "Accept": "application/json", "X-Subscription-Token": self.api_key,
        }, self.timeout_seconds)
        if len(raw) > 2_000_000:
            raise WebSearchError("WEB_SEARCH_RESPONSE_TOO_LARGE")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WebSearchError("WEB_SEARCH_RESPONSE_INVALID_JSON") from exc
        web = payload.get("web") if isinstance(payload, Mapping) else None
        results = web.get("results") if isinstance(web, Mapping) else None
        if not isinstance(results, list):
            raise WebSearchError("WEB_SEARCH_RESULTS_MISSING")
        normalized = []
        for item in results[:count]:
            if not isinstance(item, Mapping):
                continue
            url, title, snippet = item.get("url"), item.get("title"), item.get("description", "")
            if not all(isinstance(value, str) and value.strip() for value in (url, title, snippet)):
                continue
            profile = item.get("profile")
            normalized.append({
                "evidence_id": "WEB-" + hashlib.sha256(url.encode("utf-8")).hexdigest()[:16],
                "url": url, "title": title,
                "publisher": profile.get("long_name", "UNKNOWN") if isinstance(profile, Mapping) else "UNKNOWN",
                "published_at": item.get("page_age"), "access_level": "SEARCH_SNIPPET",
                "source_type": "WEB_SEARCH_RESULT", "snippet": snippet, "content": "",
                "provenance": {"provider": "brave_web_search", "query": query.strip()},
            })
        return normalized


def web_search_from_environment() -> BraveWebSearchProvider:
    provider = os.environ.get("SARA_WEB_SEARCH_PROVIDER", "brave").strip().lower()
    if provider != "brave":
        raise WebSearchError("UNSUPPORTED_WEB_SEARCH_PROVIDER")
    return BraveWebSearchProvider()
