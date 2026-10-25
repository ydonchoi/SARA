"""CLI for SARA v3: one JSON dialogue-turn request in, one result out."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .runtime import process_turn_from_environment


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run one SARA v3 dialogue turn.")
    parser.add_argument("--request", default="-", help="JSON file path; '-' reads stdin")
    parser.add_argument("--timeout-seconds", type=float, default=15.0)
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.request == "-" else Path(args.request).read_text(encoding="utf-8")
        request = json.loads(raw)
        if not isinstance(request, dict):
            raise ValueError("V3_REQUEST_MUST_BE_OBJECT")
        result = process_turn_from_environment(request, timeout_seconds=args.timeout_seconds)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        error = type(exc).__name__.upper()
        print(json.dumps({
            "schema_version": "sara.dialogue-result.v3",
            "execution_status": "FAILED",
            "error_code": error,
            "verification_status": "UNVERIFIED",
            "truthfulness_status": "UNASSESSED",
            "claim_truth_assessed": False,
        }, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
