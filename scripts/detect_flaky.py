#!/usr/bin/env python3
"""Detect flaky tests by running them multiple times.

Pre-commit hook to catch intermittent test failures before they land.
Runs each changed test 3 times and reports if results vary.

Usage:
  python3 scripts/detect_flaky.py --run-count 3

Integration (pre-commit hook):
  entry: python3 scripts/detect_flaky.py --run-count 3
  files: ^backend/tests/.*\.py$

Exit code:
  0 = all tests stable
  1 = flaky test(s) detected
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any


def get_changed_tests() -> list[str]:
    """Get test files changed in git staging area."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    tests = [
        f
        for f in result.stdout.split("\n")
        if f.startswith("backend/tests/") and f.endswith(".py") and f.strip()
    ]
    return tests


def run_test_multiple_times(
    test_file: str, run_count: int = 3
) -> tuple[list[bool], list[str]]:
    """Run test file N times, track pass/fail results.

    Returns: (list of pass/fail bools, list of stderr outputs)
    """
    results = []
    outputs = []

    for run in range(run_count):
        result = subprocess.run(
            ["pytest", test_file, "-q", "--tb=line", "-x"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent / "backend",
        )
        results.append(result.returncode == 0)
        outputs.append(result.stderr)

    return results, outputs


def detect_flaky(run_count: int = 3) -> int:
    """Detect flaky tests by running them multiple times.

    Returns: 0 if stable, 1 if flaky detected
    """
    changed_tests = get_changed_tests()

    if not changed_tests:
        print("✓ No test file changes detected")
        return 0

    flaky_tests = []

    print(f"Checking {len(changed_tests)} test file(s) for flakiness ({run_count} runs each)...")

    for test_file in changed_tests:
        results, outputs = run_test_multiple_times(test_file, run_count)

        # Flaky if: not all results are the same
        # (i.e., passed some runs but failed others)
        all_same = all(results) or not any(results)
        if not all_same:
            pass_count = sum(results)
            fail_count = run_count - pass_count

            flaky_tests.append(
                {
                    "file": test_file,
                    "passes": pass_count,
                    "failures": fail_count,
                    "flakiness": f"{fail_count}/{run_count}",
                    "stderr": outputs[0],
                }
            )
            print(f"  ⚠️  FLAKY: {test_file}")
        else:
            status = "✓ PASS" if all(results) else "✗ FAIL"
            print(f"  {status} (stable): {test_file}")

    if flaky_tests:
        print("\n" + "=" * 70)
        print("❌ FLAKY TESTS DETECTED")
        print("=" * 70)

        for test in flaky_tests:
            print(f"\n  File: {test['file']}")
            print(f"  Flakiness: {test['flakiness']} runs failed")
            print(f"  Results: {test['passes']} pass, {test['failures']} fail")

            if test["stderr"]:
                print(f"  Error sample: {test['stderr'][:200]}")

            print(
                f"\n  How to fix:"
            )
            print(f"    1. Add clean_event_loop fixture to test functions")
            print(f"    2. Check for async event-loop pollution (ADR-0013)")
            print(f"    3. Increase timeout if timing-dependent")
            print(f"    4. Use pytest --count=10 to verify fix locally")

        return 1

    print(
        f"\n✅ All {len(changed_tests)} test file(s) passed {run_count} consecutive runs"
    )
    return 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Detect flaky tests by running them multiple times"
    )
    parser.add_argument(
        "--run-count",
        type=int,
        default=3,
        help="Number of times to run each test (default: 3)",
    )

    args = parser.parse_args()
    sys.exit(detect_flaky(run_count=args.run_count))
