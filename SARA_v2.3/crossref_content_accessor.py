"""Bounded Crossref content-access capability for P8.

This module records retrieval only; it never establishes claim truth.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class ContentAccessResult:
    status: str
    url: str
    content_type: str | None
    byte_length: int
    findings: tuple[str, ...]
    content: str


class CrossrefContentAccessor:
    def __init__(self, transport=urlopen):
        self._transport = transport

    def fetch(self, url: str) -> ContentAccessResult:
        if not url:
            raise ValueError("CONTENT_URL_REQUIRED")

        request = Request(
            url,
            headers={"User-Agent": "SARA-P8-ContentAccess/0.1"},
        )
        with self._transport(request, timeout=20) as response:
            body = response.read()
            content_type = response.headers.get("Content-Type")

        return ContentAccessResult(
            status="RETRIEVED",
            url=url,
            content_type=content_type,
            byte_length=len(body),
            findings=("CONTENT_ACCESS_COMPLETED",),
            content=body.decode("utf-8", errors="replace"),
        )
