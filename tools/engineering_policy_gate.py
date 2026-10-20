"""Executable engineering-policy gate for a Git diff.

Usage: python tools/engineering_policy_gate.py --base origin/main
Use --run-tests to execute the repository test suite after preflight checks.
The gate enforces observable checks and reports, rather than pretending to
automatically judge every architectural or semantic trade-off.
"""
from __future__ import annotations

import argparse
import json
import py_compile
import subprocess
import sys
from pathlib import Path
from typing import Sequence


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], cwd=root, text=True, capture_output=True, check=False
    )


def evaluate_change(changed_paths: Sequence[str], diff_text: str) -> list[dict[str, str]]:
    """Return deterministic policy findings for a changed-file list and diff."""
    findings: list[dict[str, str]] = []
    paths = set(changed_paths)
    source_paths = {
        p for p in paths
        if p.endswith(".py")
        and not p.startswith("tests/")
        and not Path(p).name.startswith("test_")
    }
    test_paths = {
        p for p in paths
        if p.startswith("tests/") or Path(p).name.startswith("test_")
    }

    if source_paths and not test_paths:
        findings.append({
            "severity": "BLOCK",
            "code": "SOURCE_CHANGE_WITHOUT_TEST_CHANGE",
            "message": "Executable Python changes require relevant tests or an explicit reviewed exception.",
        })

    removed_assertions = [
        line for line in diff_text.splitlines()
        if line.startswith("-") and not line.startswith("---")
        and ("assert " in line or "pytest.raises(" in line or "unittest.TestCase" in line)
    ]
    added_skips = [
        line for line in diff_text.splitlines()
        if line.startswith("+") and not line.startswith("+++")
        and ("pytest.skip(" in line or "@pytest.mark.skip" in line or "unittest.skip(" in line)
    ]
    if removed_assertions and added_skips:
        findings.append({
            "severity": "BLOCK",
            "code": "POSSIBLE_TEST_WEAKENING",
            "message": "The diff both removes assertion/exception checks and adds test skipping; review the root cause rather than suppressing failure.",
        })

    if not findings:
        findings.append({
            "severity": "REVIEW",
            "code": "STATIC_PREFLIGHT_ONLY",
            "message": "Static policy preflight has no blocking finding; architecture, semantics, and regression adequacy still require review.",
        })
    return findings


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", default="origin/main", help="Base git ref for the comparison.")
    parser.add_argument("--head", default="HEAD", help="Head git ref (default: HEAD).")
    parser.add_argument("--run-tests", action="store_true", help="Run python -m pytest -q after preflight.")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]

    diff = _git(root, "diff", "--check", f"{args.base}...{args.head}")
    if diff.returncode != 0:
        print(json.dumps({"status": "BLOCKED", "stage": "git_diff_check", "stderr": diff.stderr.strip()}))
        return 2

    names = _git(root, "diff", "--name-only", f"{args.base}...{args.head}")
    if names.returncode != 0:
        print(json.dumps({"status": "BLOCKED", "stage": "changed_files", "stderr": names.stderr.strip()}))
        return 2
    changed = [line for line in names.stdout.splitlines() if line]
    full_diff = _git(root, "diff", "--unified=0", f"{args.base}...{args.head}")
    if full_diff.returncode != 0:
        print(json.dumps({"status": "BLOCKED", "stage": "diff_read", "stderr": full_diff.stderr.strip()}))
        return 2

    findings = evaluate_change(changed, full_diff.stdout)
    compile_errors: list[str] = []
    for rel in changed:
        if rel.endswith(".py"):
            path = root / rel
            if path.is_file():
                try:
                    py_compile.compile(str(path), doraise=True)
                except py_compile.PyCompileError as exc:
                    compile_errors.append(f"{rel}: {exc.msg}")
    if compile_errors:
        findings.append({
            "severity": "BLOCK",
            "code": "PYTHON_SYNTAX_ERROR",
            "message": "; ".join(compile_errors),
        })

    test_result = None
    if args.run_tests and not any(f["severity"] == "BLOCK" for f in findings):
        test_result = subprocess.run(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=root, text=True, capture_output=True, check=False,
        )
        if test_result.returncode != 0:
            findings.append({
                "severity": "BLOCK",
                "code": "TEST_SUITE_FAILED",
                "message": (test_result.stdout + "\n" + test_result.stderr).strip()[-4000:],
            })

    blocked = any(f["severity"] == "BLOCK" for f in findings)
    result = {
        "status": "BLOCKED" if blocked else "PREFLIGHT_PASSED_REVIEW_REQUIRED",
        "base": args.base,
        "head": args.head,
        "changed_paths": changed,
        "findings": findings,
        "tests_executed": bool(args.run_tests and test_result is not None),
        "test_return_code": test_result.returncode if test_result is not None else None,
        "limitations": [
            "Static checks cannot establish semantic correctness or fully judge root cause.",
            "A non-blocking result is not a Verified status; human review and proportionate regression/integration evidence remain required.",
        ],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
