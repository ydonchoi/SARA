"""Optional, bounded single-page Crawl4AI content fetcher for SARA v3.

The adapter is deliberately a fetch-only component. It does not search, assess
claims, or emit a verification status. Crawl4AI is imported lazily so the base
SARA runtime remains usable without the optional dependency.
"""
from __future__ import annotations

import asyncio
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone
from hashlib import sha256
import ipaddress
import os
from pathlib import Path
import socket
import threading
from typing import Any, Mapping
from urllib.parse import urlsplit


class Crawl4AIAdapterError(RuntimeError):
    """Sanitized, stable fetch errors; never includes page or credential data."""


class Crawl4AIContentFetcher:
    """Fetch one allowlisted HTTPS page and preserve raw/Markdown artifacts.

    A small worker event loop keeps one AsyncWebCrawler alive for the life of
    this adapter, allowing repeated calls in a dialogue turn to reuse Chromium.
    Call ``close`` (or use this object as a context manager) when finished.
    """

    extractor_version = "crawl4ai-0.9.5/sara-adapter-1"

    def __init__(self, *, allowed_domains: set[str], storage_dir: str | Path,
                 timeout_seconds: float = 20.0, max_stored_bytes: int = 2_000_000,
                 max_concurrency: int = 1, max_pages: int = 3) -> None:
        domains = {str(item).strip().lower().strip(".") for item in allowed_domains}
        if not domains or any(not item or "/" in item or ":" in item for item in domains):
            raise Crawl4AIAdapterError("CRAWL4AI_DOMAIN_ALLOWLIST_REQUIRED")
        if isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise Crawl4AIAdapterError("CRAWL4AI_TIMEOUT_INVALID")
        if not 1 <= max_concurrency <= 2:
            raise Crawl4AIAdapterError("CRAWL4AI_CONCURRENCY_OUT_OF_RANGE")
        if not 1 <= max_pages <= 3:
            raise Crawl4AIAdapterError("CRAWL4AI_PAGE_LIMIT_OUT_OF_RANGE")
        if max_stored_bytes < 1024:
            raise Crawl4AIAdapterError("CRAWL4AI_SIZE_LIMIT_INVALID")
        self.allowed_domains = domains
        self.storage_dir = Path(storage_dir).resolve()
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_seconds = float(timeout_seconds)
        self.max_stored_bytes = int(max_stored_bytes)
        self.max_concurrency = max_concurrency
        self.max_pages = max_pages
        self._fetch_count = 0
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._crawler: Any | None = None
        self._semaphore: asyncio.Semaphore | None = None
        self._lock = threading.RLock()
        self._closed = False

    @classmethod
    def from_environment(cls, *, base_dir: str | Path | None = None) -> "Crawl4AIContentFetcher | None":
        enabled = os.environ.get("SARA_CRAWL4AI_ENABLED", "").strip().lower()
        if enabled not in {"1", "true", "yes"}:
            return None
        domains = {item.strip().lower().strip(".") for item in
                   os.environ.get("SARA_CRAWL4AI_ALLOWED_DOMAINS", "").split(",") if item.strip()}
        if not domains:
            raise Crawl4AIAdapterError("CRAWL4AI_DOMAIN_ALLOWLIST_REQUIRED")
        root = Path(base_dir) if base_dir else Path(os.environ.get(
            "SARA_CRAWL4AI_STORE_DIR", ".sara-crawl4ai"))
        return cls(
            allowed_domains=domains,
            storage_dir=root,
            timeout_seconds=float(os.environ.get("SARA_CRAWL4AI_TIMEOUT_SECONDS", "20")),
            max_stored_bytes=int(os.environ.get("SARA_CRAWL4AI_MAX_STORED_BYTES", "2000000")),
            max_pages=int(os.environ.get("SARA_CRAWL4AI_MAX_PAGES", "3")),
        )

    def _validate_url(self, url: str) -> tuple[str, str]:
        if not isinstance(url, str) or not url or len(url) > 4096:
            raise Crawl4AIAdapterError("CRAWL4AI_URL_INVALID")
        try:
            parsed = urlsplit(url)
            hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
            port = parsed.port
        except (ValueError, UnicodeError):
            raise Crawl4AIAdapterError("CRAWL4AI_URL_INVALID") from None
        try:
            ipaddress.ip_address(hostname)
        except ValueError:
            pass
        else:
            raise Crawl4AIAdapterError("CRAWL4AI_IP_LITERAL_BLOCKED")
        if (parsed.scheme.lower() != "https" or not hostname or parsed.username or parsed.password
                or port not in (None, 443)
                or not any(hostname == domain or hostname.endswith("." + domain)
                           for domain in self.allowed_domains)):
            raise Crawl4AIAdapterError("CRAWL4AI_URL_OUTSIDE_POLICY")
        return hostname, parsed.path or "/"

    def _start_worker(self) -> asyncio.AbstractEventLoop:
        with self._lock:
            if self._closed:
                raise Crawl4AIAdapterError("CRAWL4AI_FETCHER_CLOSED")
            if self._thread and self._thread.is_alive() and self._loop:
                return self._loop
            ready = threading.Event()
            state: dict[str, Any] = {}

            def worker() -> None:
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    state["loop"] = loop
                    ready.set()
                    loop.run_forever()
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                    loop.close()
                except Exception:
                    state["error"] = "EVENT_LOOP_START_FAILED"
                    ready.set()

            self._thread = threading.Thread(target=worker, name="sara-crawl4ai", daemon=True)
            self._thread.start()
            ready.wait(min(self.timeout_seconds, 5.0))
            self._loop = state.get("loop")
            if self._loop is None:
                raise Crawl4AIAdapterError("CRAWL4AI_WORKER_START_FAILED")
            return self._loop

    async def _ensure_crawler(self) -> None:
        if self._crawler is not None:
            return
        runtime_dir = self.storage_dir / ".runtime"
        runtime_dir.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("CRAWL4_AI_BASE_DIRECTORY", str(runtime_dir))
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig
        except Exception:
            raise Crawl4AIAdapterError("CRAWL4AI_DEPENDENCY_UNAVAILABLE") from None
        crawler = AsyncWebCrawler(config=BrowserConfig(headless=True, verbose=False), verbose=False)
        try:
            await crawler.start()
            crawler.crawler_strategy.set_hook("on_page_context_created", self._install_route_guard)
        except Exception:
            try:
                await crawler.close()
            except Exception:
                pass
            raise Crawl4AIAdapterError("CRAWL4AI_BROWSER_START_FAILED") from None
        self._crawler = crawler
        self._semaphore = asyncio.Semaphore(self.max_concurrency)

    async def _resolve_public(self, hostname: str) -> bool:
        try:
            loop = asyncio.get_running_loop()
            records = await asyncio.wait_for(
                loop.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM), timeout=3.0,
            )
            return self._addresses_are_public(record[4][0] for record in records)
        except Exception:
            return False

    @staticmethod
    def _addresses_are_public(addresses: Any) -> bool:
        try:
            parsed = [ipaddress.ip_address(item) for item in addresses]
        except (TypeError, ValueError):
            return False
        return bool(parsed) and all(address.is_global for address in parsed)

    async def _install_route_guard(self, page: Any, context: Any, **_: Any) -> Any:
        async def guard(route: Any) -> None:
            request = route.request
            try:
                hostname, _path = self._validate_url(request.url)
                public = await self._resolve_public(hostname)
            except Crawl4AIAdapterError:
                public = False
            except Exception:
                public = False
            if not public:
                await route.abort()
            elif request.resource_type in {"image", "media", "font"}:
                await route.abort()
            else:
                await route.continue_()
        await context.route("**/*", guard)
        return page

    async def _fetch_async(self, url: str) -> dict[str, Any]:
        await self._ensure_crawler()
        from crawl4ai import CacheMode, CrawlerRunConfig
        assert self._crawler is not None and self._semaphore is not None
        async with self._semaphore:
            try:
                result = await asyncio.wait_for(
                    self._crawler.arun(
                        url=url,
                        config=CrawlerRunConfig(
                            cache_mode=CacheMode.BYPASS,
                            check_robots_txt=True,
                            page_timeout=int(self.timeout_seconds * 1000),
                            verbose=False,
                        ),
                    ),
                    timeout=self.timeout_seconds,
                )
            except asyncio.TimeoutError:
                raise Crawl4AIAdapterError("CRAWL4AI_TIMEOUT") from None
            except Exception:
                raise Crawl4AIAdapterError("CRAWL4AI_FETCH_FAILED") from None
        return self._result_to_evidence(url, result)

    def _result_to_evidence(self, url: str, result: Any) -> dict[str, Any]:
        final_url = getattr(result, "url", None) or url
        self._validate_url(final_url)
        raw_html = getattr(result, "html", None)
        if not isinstance(raw_html, str):
            raw_html = ""
        markdown_value = getattr(result, "markdown", None)
        markdown = getattr(markdown_value, "raw_markdown", markdown_value)
        if not isinstance(markdown, str):
            markdown = ""
        raw_bytes, markdown_bytes = raw_html.encode("utf-8"), markdown.encode("utf-8")
        retrieved_at = datetime.now(timezone.utc).isoformat()
        http_status = getattr(result, "redirected_status_code", None)
        if http_status is None:
            http_status = getattr(result, "status_code", None)
        source_id = "SRC-" + sha256(url.encode("utf-8")).hexdigest()[:24]
        raw_hash, markdown_hash = sha256(raw_bytes).hexdigest(), sha256(markdown_bytes).hexdigest()
        success = bool(getattr(result, "success", False)) and isinstance(http_status, int) and 200 <= http_status < 300
        retrieval_status = "SUCCEEDED" if success else "FAILED"
        extraction_status = "COMPLETE" if success and raw_bytes and markdown.strip() else (
            "PARTIAL" if raw_bytes or markdown.strip() else "EMPTY")
        # Crawl4AI reports that its extraction pipeline completed, not that the
        # publisher's entire scholarly source was represented in the page.
        completeness = "UNKNOWN" if extraction_status == "COMPLETE" else (
            "PARTIAL" if extraction_status == "PARTIAL" else "EMPTY")
        retrieval_error = None if success else ("HTTP_ERROR" if isinstance(http_status, int) else "CRAWL_FAILED")
        raw_ref = markdown_ref = None
        if max(len(raw_bytes), len(markdown_bytes)) > self.max_stored_bytes:
            completeness = "PARTIAL"
            extraction_status = "OVERSIZE"
            retrieval_error = "CONTENT_TOO_LARGE"
        elif raw_bytes and markdown_bytes:
            raw_ref = self._store("raw", raw_hash, ".html", raw_bytes)
            markdown_ref = self._store("markdown", markdown_hash, ".md", markdown_bytes)
        content = markdown if extraction_status == "COMPLETE" else ""
        snippet = "" if content else markdown[:8000]
        return {
            "evidence_id": source_id,
            "url": url,
            "title": getattr(result, "metadata", {}).get("title", "") if isinstance(getattr(result, "metadata", {}), Mapping) else "",
            "publisher": "UNKNOWN",
            "retrieved_at": retrieved_at,
            "access_level": "FULL_TEXT" if extraction_status == "COMPLETE" else "ABSTRACT",
            "source_type": "CRAWL4AI_RETRIEVED_CONTENT",
            "content": content,
            "snippet": snippet or ("Page content was empty or incomplete." if extraction_status != "COMPLETE" else ""),
            "provenance": {"provider": "crawl4ai", "extractor_version": self.extractor_version},
            "retrieval_metadata": {
                "source_id": source_id,
                "source_url": url,
                "final_url": final_url,
                "retrieved_at": retrieved_at,
                "http_status": http_status,
                "content_hash": raw_hash if raw_bytes else None,
                "markdown_hash": markdown_hash if markdown_bytes else None,
                "raw_content_ref": raw_ref,
                "markdown_ref": markdown_ref,
                "extractor_version": self.extractor_version,
                "retrieval_status": retrieval_status,
                "completeness_status": completeness,
                "extraction_status": extraction_status,
                "retrieval_error_code": retrieval_error,
            },
        }

    def _store(self, folder: str, digest: str, suffix: str, data: bytes) -> str:
        relative = Path(folder) / f"{digest}{suffix}"
        destination = (self.storage_dir / relative).resolve()
        if self.storage_dir not in destination.parents:
            raise Crawl4AIAdapterError("CRAWL4AI_STORAGE_PATH_INVALID")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(destination.suffix + ".tmp")
            temporary.write_bytes(data)
            temporary.replace(destination)
        return relative.as_posix()

    def fetch(self, url: str) -> dict[str, Any]:
        """Synchronously fetch one page for SARA's current sync provider API."""
        self._validate_url(url)
        with self._lock:
            if self._fetch_count >= self.max_pages:
                raise Crawl4AIAdapterError("CRAWL4AI_PAGE_LIMIT_REACHED")
            self._fetch_count += 1
        loop = self._start_worker()
        coroutine = self._fetch_async(url)
        try:
            future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        except Exception:
            coroutine.close()
            raise Crawl4AIAdapterError("CRAWL4AI_WORKER_START_FAILED") from None
        try:
            return future.result(timeout=self.timeout_seconds + 3.0)
        except FutureTimeout:
            future.cancel()
            raise Crawl4AIAdapterError("CRAWL4AI_TIMEOUT") from None
        except Crawl4AIAdapterError:
            raise
        except Exception:
            raise Crawl4AIAdapterError("CRAWL4AI_FETCH_FAILED") from None

    async def _close_async(self) -> None:
        if self._crawler is not None:
            crawler, self._crawler = self._crawler, None
            try:
                await crawler.close()
            except Exception:
                pass

    def close(self) -> None:
        with self._lock:
            if self._closed:
                return
            self._closed = True
            loop, thread = self._loop, self._thread
        if loop and thread and thread.is_alive():
            try:
                asyncio.run_coroutine_threadsafe(self._close_async(), loop).result(timeout=5)
            except Exception:
                pass
            loop.call_soon_threadsafe(loop.stop)
            thread.join(timeout=5)

    def __enter__(self) -> "Crawl4AIContentFetcher":
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()
