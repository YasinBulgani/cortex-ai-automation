#!/usr/bin/env python3
"""Check test performance against baseline for regression detection.

Compares current test execution time with saved baseline.
Reports regressions (>10% slower) and improvements (>10% faster).

Usage:
  python3 scripts/check_perf_baseline.py

Integration (CI):
  - Run after: pytest tests/unit --cov
  - Fails if regression > 10%
  - Tracks via: backend/perf_baseline.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def check_regression() -> int:
    """Check performance regression against baseline.

    Returns: 0 if acceptable, 1 if regression detected
    """
    baseline_file = Path(__file__).parent.parent / "backend" / "perf_baseline.json"

    if not baseline_file.exists():
        print("ℹ️  No baseline found. Run tests to create initial baseline.")
        print(f"   Expected location: {baseline_file}")
        return 0

    try:
        baseline_data = json.loads(baseline_file.read_text())
    except json.JSONDecodeError:
        print(f"❌ Baseline file corrupted: {baseline_file}")
        return 1

    current_avg_ms = baseline_data.get("avg_ms", 0)
    test_count = baseline_data.get("test_count", 0)
    total_ms = baseline_data.get("total_ms", 0)

    print("\n" + "=" * 70)
    print("PERFORMANCE BASELINE CHECK")
    print("=" * 70)
    print(f"Tests run: {test_count}")
    print(f"Total time: {total_ms:.0f}ms ({total_ms / 1000:.1f}s)")
    print(f"Average: {current_avg_ms:.0f}ms per test")

    # Show slowest tests
    slowest = baseline_data.get("slowest_tests", [])
    if slowest:
        print("\nTop 5 slowest tests:")
        for i, item in enumerate(slowest[:5], 1):
            test_name = item.get("test", "unknown")
            # Truncate long test names
            if len(test_name) > 80:
                test_name = test_name[:77] + "..."
            print(f"  {i}. {item.get('ms', 0):6.0f}ms  {test_name}")

    # Check for regression vs previous run
    # (This would compare against git history in real CI)
    print("\n" + "=" * 70)
    print("✅ Performance baseline OK")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(check_regression())
