"""Compare direct HTTP and Crawl4AI latency for one explicitly allowed URL.

This is a smoke benchmark, not a representative throughput claim. It reports
cold/warm browser runs and direct HTTP response size for the supplied source.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
import ipaddress
import json
from pathlib import Path
import socket
import statistics
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.parse import urlsplit

from .crawl4ai_adapter import Crawl4AIAdapterError, Crawl4AIContentFetcher


class _VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() in {"script", "style", "template"}:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        if tag.lower() in {"script", "style", "template"} and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        if not self.hidden_depth:
            self.parts.append(data)


def _visible_text(html: str) -> str:
    parser = _VisibleTextParser()
    parser.feed(html)
    return " ".join(parser.parts)


def _check_benchmark_url(url: str, domains: set[str]) -> None:
    try:
        parsed = urlsplit(url)
        hostname = (parsed.hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
        port = parsed.port
    except (ValueError, UnicodeError):
        raise ValueError("BENCHMARK_URL_INVALID") from None
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        raise ValueError("BENCHMARK_IP_LITERAL_BLOCKED")
    if (parsed.scheme != "https" or not hostname or parsed.username or parsed.password
            or port not in (None, 443)
            or not any(hostname == domain or hostname.endswith("." + domain) for domain in domains)):
        raise ValueError("BENCHMARK_URL_OUTSIDE_ALLOWLIST")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)}
    except OSError:
        raise ValueError("BENCHMARK_DNS_FAILED") from None
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise ValueError("BENCHMARK_NON_PUBLIC_ADDRESS_BLOCKED")


def _direct_http(url: str, domains: set[str], timeout: float, max_bytes: int,
                 expected_marker: str | None = None) -> dict[str, Any]:
    class CheckedRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            _check_benchmark_url(newurl, domains)
            return super().redirect_request(req, fp, code, msg, headers, newurl)

    opener = build_opener(CheckedRedirect())
    started = time.perf_counter()
    status = None
    size = 0
    error = None
    marker_found = None
    visible = ""
    try:
        request = Request(url, headers={"User-Agent": "SARA-Crawl4AI-Benchmark/1.0"})
        with opener.open(request, timeout=timeout) as response:
            status = response.status
            data = response.read(max_bytes + 1)
            size = len(data)
            visible = _visible_text(data.decode("utf-8", errors="replace"))
            marker_found = expected_marker in visible if expected_marker else None
            if size > max_bytes:
                error = "RESPONSE_SIZE_LIMIT_EXCEEDED"
    except HTTPError as exc:
        status = exc.code
        error = "HTTP_ERROR"
    except (URLError, TimeoutError, OSError):
        error = "DIRECT_HTTP_FAILED"
    return {"elapsed_seconds": time.perf_counter() - started, "http_status": status,
            "bytes_read": size, "visible_chars": len(visible) if status is not None else 0,
            "error_code": error, "expected_marker_found": marker_found}


def run_benchmark(url: str, *, allowed_domains: set[str], store_dir: Path,
                  repetitions: int = 1, timeout_seconds: float = 20.0,
                  max_bytes: int = 2_000_000, expected_marker: str | None = None) -> dict[str, Any]:
    if not 1 <= repetitions <= 3:
        raise ValueError("BENCHMARK_REPETITIONS_OUT_OF_RANGE")
    _check_benchmark_url(url, allowed_domains)
    direct_runs = [_direct_http(url, allowed_domains, timeout_seconds, max_bytes, expected_marker)
                   for _ in range(repetitions)]
    fetcher = Crawl4AIContentFetcher(
        allowed_domains=allowed_domains, storage_dir=store_dir,
        timeout_seconds=timeout_seconds, max_stored_bytes=max_bytes,
        max_pages=repetitions,
    )
    crawl_runs = []
    try:
        for _ in range(repetitions):
            started = time.perf_counter()
            try:
                result = fetcher.fetch(url)
                metadata = result.get("retrieval_metadata", {})
                crawl_runs.append({
                    "elapsed_seconds": time.perf_counter() - started,
                    "http_status": metadata.get("http_status"),
                    "markdown_chars": len(result.get("content") or result.get("snippet") or ""),
                    "completeness_status": metadata.get("completeness_status"),
                    "error_code": None if metadata.get("retrieval_status") == "SUCCEEDED" else "CRAWL4AI_FETCH_FAILED",
                    "expected_marker_found": (expected_marker in (result.get("content", "") + result.get("snippet", "")))
                    if expected_marker else None,
                })
            except Crawl4AIAdapterError as exc:
                crawl_runs.append({"elapsed_seconds": time.perf_counter() - started,
                                   "http_status": None, "markdown_chars": 0,
                                   "completeness_status": "UNKNOWN", "error_code": str(exc),
                                   "expected_marker_found": False if expected_marker else None})
    finally:
        fetcher.close()
    direct_times = [run["elapsed_seconds"] for run in direct_runs]
    crawl_times = [run["elapsed_seconds"] for run in crawl_runs]
    return {
        "url": url,
        "repetitions": repetitions,
        "direct_http": {"runs": direct_runs, "median_seconds": statistics.median(direct_times)},
        "crawl4ai": {"runs": crawl_runs, "median_seconds": statistics.median(crawl_times)},
        "interpretation": "Per-URL smoke comparison only; browser and network startup, site behavior, and extraction quality affect results.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--allowed-domains", required=True, help="Comma-separated explicit domain allowlist")
    parser.add_argument("--store-dir", default=".sara-crawl4ai-benchmark")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-bytes", type=int, default=2_000_000)
    parser.add_argument("--expected-marker")
    args = parser.parse_args()
    domains = {value.strip().lower().strip(".") for value in args.allowed_domains.split(",") if value.strip()}
    result = run_benchmark(args.url, allowed_domains=domains, store_dir=Path(args.store_dir),
                           repetitions=args.repetitions, timeout_seconds=args.timeout_seconds,
                           max_bytes=args.max_bytes, expected_marker=args.expected_marker)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
