from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "SARA_v2.5"))

from promotion_gate import REQUIRED_CI_SUITES


def test_required_ci_suites_match_workflow_steps_and_promotion_schema():
    workflow = (ROOT / ".github/workflows/contract-tests.yml").read_text(
        encoding="utf-8"
    )
    schema = (ROOT / "SARA_v2.5/schemas/canonical_promotion_gate_schema.yaml").read_text(
        encoding="utf-8"
    )
    workflow_suites = set(re.findall(r"^\s+- id: ([a-z0-9_]+)\s*$", workflow, re.M))
    required_block = re.search(
        r"^  required_suites:\s*\n((?:^    - [a-z0-9_]+\s*\n)+)",
        schema,
        re.M,
    )
    assert required_block is not None
    schema_suites = set(re.findall(r"^    - ([a-z0-9_]+)\s*$", required_block.group(1), re.M))

    assert REQUIRED_CI_SUITES == workflow_suites
    assert REQUIRED_CI_SUITES == schema_suites
