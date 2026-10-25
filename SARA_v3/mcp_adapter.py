"""Allowlisted bridge to a host-owned MCP client (read-only source tools)."""
from __future__ import annotations

import json
from typing import Any, Callable, Mapping
from urllib.parse import urlparse


class MCPAdapterError(RuntimeError):
    """Sanitized MCP bridge/configuration error."""


class MCPSourceAdapter:
    """Wrap a host's MCP client; only named search and fetch tools are callable."""
    def __init__(self, call_tool: Callable[[str, Mapping[str, Any]], Any], *,
                 search_tool: str | None = None, fetch_tool: str | None = None,
                 allowed_tools: set[str] | None = None,
                 fetch_allowed_domains: set[str] | None = None) -> None:
        if not callable(call_tool):
            raise MCPAdapterError("MCP_CALL_TOOL_REQUIRED")
        self._call_tool = call_tool
        self.search_tool, self.fetch_tool = search_tool, fetch_tool
        self.allowed_tools = set(allowed_tools or set())
        self.fetch_allowed_domains = {d.lower().strip(".") for d in (fetch_allowed_domains or set())}
        for tool in (search_tool, fetch_tool):
            if tool and tool not in self.allowed_tools:
                raise MCPAdapterError("MCP_TOOL_NOT_ALLOWLISTED")
        if fetch_tool and not self.fetch_allowed_domains:
            raise MCPAdapterError("MCP_FETCH_DOMAIN_ALLOWLIST_REQUIRED")

    @staticmethod
    def _structured(result: Any) -> Mapping[str, Any]:
        if not isinstance(result, Mapping):
            raise MCPAdapterError("MCP_RESULT_MUST_BE_MAPPING")
        if result.get("isError") is True or result.get("is_error") is True:
            raise MCPAdapterError("MCP_TOOL_CALL_FAILED")
        structured = result.get("structuredContent", result.get("structured_content"))
        if isinstance(structured, Mapping):
            return structured
        content = result.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, Mapping) and block.get("type") == "text" and isinstance(block.get("text"), str):
                    try:
                        decoded = json.loads(block["text"])
                    except json.JSONDecodeError:
                        continue
                    if isinstance(decoded, Mapping):
                        return decoded
        raise MCPAdapterError("MCP_STRUCTURED_RESULT_REQUIRED")

    def search(self, query: str) -> list[dict[str, Any]]:
        if not self.search_tool:
            return []
        result = self._structured(self._call_tool(self.search_tool, {"query": query}))
        items = result.get("results")
        if not isinstance(items, list):
            raise MCPAdapterError("MCP_SEARCH_RESULTS_REQUIRED")
        return [dict(item, source_type="MCP_SEARCH_RESULT", provenance={"provider": "mcp", "tool": self.search_tool})
                for item in items if isinstance(item, Mapping)]

    def fetch(self, url: str) -> dict[str, Any] | None:
        if not self.fetch_tool:
            return None
        try:
            parsed = urlparse(url)
            hostname = (parsed.hostname or "").lower().strip(".")
        except ValueError as exc:
            raise MCPAdapterError("MCP_FETCH_URL_INVALID") from exc
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or not any(hostname == d or hostname.endswith("." + d) for d in self.fetch_allowed_domains)):
            raise MCPAdapterError("MCP_FETCH_URL_OUTSIDE_DOMAIN_ALLOWLIST")
        result = self._structured(self._call_tool(self.fetch_tool, {"url": url}))
        if result.get("url", url) != url:
            raise MCPAdapterError("MCP_FETCH_URL_MISMATCH")
        content = result.get("content")
        if not isinstance(content, str) or not content.strip():
            raise MCPAdapterError("MCP_FETCH_CONTENT_REQUIRED")
        return {
            "evidence_id": result.get("evidence_id"), "url": url,
            "title": result.get("title", url), "publisher": result.get("publisher", "UNKNOWN"),
            "published_at": result.get("published_at"),
            "access_level": "FULL_TEXT" if result.get("content_scope") == "FULL_TEXT" else "ABSTRACT",
            "source_type": "MCP_RETRIEVED_CONTENT", "content": content[:100_000],
            "snippet": result.get("snippet", ""),
            "provenance": {"provider": "mcp", "tool": self.fetch_tool},
        }
