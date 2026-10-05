from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "SARA_v2.3"
sys.path.insert(0, str(ROOT))

from crossref_content_accessor import CrossrefContentAccessor


def test_content_access_exposes_retrieved_payload():
    class Response:
        headers = {"Content-Type": "application/json"}
        def read(self):
            return b'{\"title\":[\"Measured measurement\"]}'
        def __enter__(self): return self
        def __exit__(self, *args): return False

    result = CrossrefContentAccessor(transport=lambda request, timeout=20: Response()).fetch(
        "https://api.crossref.org/works/10.1038/nphys1170"
    )
    assert result.status == "RETRIEVED"
    assert result.byte_length > 0
    assert "Measured measurement" in result.content
