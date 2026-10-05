from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from crossref_content_accessor import CrossrefContentAccessor


class FakeResponse:
    def __init__(self, body=b"example", content_type="text/plain"):
        self._body = body
        self.headers = {"Content-Type": content_type}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


def test_content_accessor_records_retrieval_without_truthfulness():
    accessor = CrossrefContentAccessor(
        transport=lambda request, timeout: FakeResponse(b"content")
    )
    result = accessor.fetch("https://example.org/article")

    assert result.status == "RETRIEVED"
    assert result.byte_length == len(b"content")
    assert result.content_type == "text/plain"
    assert result.findings == ("CONTENT_ACCESS_COMPLETED",)


def test_content_accessor_rejects_missing_url():
    accessor = CrossrefContentAccessor()
    try:
        accessor.fetch("")
    except ValueError as exc:
        assert str(exc) == "CONTENT_URL_REQUIRED"
    else:
        raise AssertionError("missing URL must be rejected")
