"""Pytest plugin for tracking test execution time.

Captures per-test timing, identifies slow tests (>500ms), and saves
performance baseline for regression detection.

Usage: Automatically registered in pytest.ini
Output: Printed to stdout, saved to perf_baseline.json

Related: scripts/check_perf_baseline.py
"""
from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PERF_BASELINE_FILE = Path(__file__).parent.parent / "perf_baseline.json"


class PerformanceTracker:
    """Track and report test performance metrics."""

    def __init__(self) -> None:
        self.test_times: dict[str, float] = {}
        self.fixture_times: dict[str, float] = {}
        self.test_start_time: float | None = None

    def pytest_runtest_setup(self, item: Any) -> None:
        """Mark start of test execution."""
        self.test_start_time = time.time()

    def pytest_runtest_teardown(self, item: Any, nextitem: Any = None) -> None:
        """Record test duration."""
        if self.test_start_time is not None:
            duration_sec = time.time() - self.test_start_time
            duration_ms = duration_sec * 1000
            self.test_times[item.nodeid] = duration_ms

            # Log slow tests (>500ms) for visibility
            if duration_ms > 500:
                print(f"\n  ⏱️  SLOW TEST ({duration_ms:.0f}ms): {item.nodeid}")

    def pytest_sessionfinish(self, session: Any) -> None:
        """Save performance baseline at end of test session."""
        if not self.test_times:
            return

        # Calculate statistics
        total_ms = sum(self.test_times.values())
        avg_ms = total_ms / len(self.test_times) if self.test_times else 0
        slowest = sorted(
            self.test_times.items(), key=lambda x: x[1], reverse=True
        )[:10]

        baseline = {
            "date": datetime.now().isoformat(),
            "total_ms": int(total_ms),
            "avg_ms": int(avg_ms),
            "test_count": len(self.test_times),
            "slowest_tests": [{"test": name, "ms": int(ms)} for name, ms in slowest],
        }

        # Save to file
        PERF_BASELINE_FILE.write_text(json.dumps(baseline, indent=2))

        # Print summary
        print("\n" + "=" * 60)
        print("PERFORMANCE SUMMARY:")
        print(f"  Total tests: {len(self.test_times)}")
        print(f"  Total time: {total_ms:.0f}ms ({total_ms / 1000:.1f}s)")
        print(f"  Average: {avg_ms:.0f}ms per test")
        print("\nSLOWEST TESTS (top 10):")
        for i, (test, duration_ms) in enumerate(slowest, 1):
            print(f"  {i:2}. {duration_ms:6.0f}ms  {test}")
        print("=" * 60)

        # Compare with previous baseline
        if PERF_BASELINE_FILE.exists():
            try:
                prev_data = json.loads(PERF_BASELINE_FILE.read_text())
                prev_avg = prev_data.get("avg_ms", 0)
                if prev_avg > 0:
                    diff_pct = ((avg_ms - prev_avg) / prev_avg) * 100
                    if diff_pct > 10:
                        print(
                            f"\n⚠️  PERFORMANCE REGRESSION: {diff_pct:+.1f}% "
                            f"({avg_ms:.0f}ms vs {prev_avg:.0f}ms baseline)"
                        )
                    elif diff_pct < -10:
                        print(
                            f"\n✅ PERFORMANCE IMPROVEMENT: {diff_pct:+.1f}% "
                            f"({avg_ms:.0f}ms vs {prev_avg:.0f}ms baseline)"
                        )
            except Exception:
                pass


# Global instance
_tracker = PerformanceTracker()


def pytest_configure(config: Any) -> None:
    """Register performance tracker plugin."""
    config.pluginmanager.register(_tracker)
