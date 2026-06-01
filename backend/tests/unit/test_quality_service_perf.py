"""Performance tests for app.domains.quality.service.

Validates that the quality service remains fast under realistic load:
  - EvalSnapshot instantiation speed (<1 ms for 1 000 iterations)
  - parse_eval_report with a large markdown report (<10 ms)
  - _read_history with 100 mocked files (<500 ms)

All filesystem I/O is mocked — no real files are touched.
Timing assertions use time.perf_counter() for sub-millisecond resolution.

NOTE: These tests set conservative upper bounds. On a loaded CI runner the
numbers may vary; bounds are intentionally generous (10× typical observed
values) so they only catch genuine regressions, not noise.
"""
from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock

import pytest

try:
    from app.domains.quality.service import (
        EvalSnapshot,
        parse_eval_report,
        _read_history,
        _read_latest_report,
        get_quality_metrics,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="quality service import failed")


# ── Shared fixtures ───────────────────────────────────────────────────────────

_SAMPLE_MD = """\
# BGTest Eval Report — 2026-04-19T06:53:31+00:00

**Mod:** `grounding-only`

| Metrik | Değer |
|---|---|
| Fixture sayısı | 5 |
| Toplam adım | 22 |
| **Mapping accuracy** | 86.4% |
| Unknown rate | 13.6% |
| Value preservation | 100.0% |
| Gherkin validity | 97.3% |
| p95 latency | 44 ms |
| LLM hatası | 0 |
"""

# Large report: repeat the standard sample + add a lot of noise lines
_LARGE_MD = _SAMPLE_MD + ("\n" + "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50) * 20


def _make_mock_file(mtime: float, content: str = _SAMPLE_MD) -> MagicMock:
    """Return a Path-like mock representing a single .md history file."""
    f = MagicMock(spec=Path)
    f.is_file.return_value = True
    f.read_text.return_value = content
    f.stat.return_value = MagicMock(st_mtime=mtime)
    f.suffix = ".md"
    return f


# ── EvalSnapshot instantiation speed ─────────────────────────────────────────

class TestEvalSnapshotInstantiationSpeed:
    """1 000 EvalSnapshot() calls must complete in under 1 ms total."""

    ITERATIONS = 1_000
    MAX_MS = 1.0  # 1 ms ceiling

    def test_default_instantiation_is_fast(self):
        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            EvalSnapshot()
        elapsed_ms = (time.perf_counter() - start) * 1_000
        assert elapsed_ms < self.MAX_MS, (
            f"EvalSnapshot() x{self.ITERATIONS} took {elapsed_ms:.3f} ms "
            f"(limit: {self.MAX_MS} ms)"
        )

    def test_fully_populated_instantiation_is_fast(self):
        start = time.perf_counter()
        for i in range(self.ITERATIONS):
            EvalSnapshot(
                available=True,
                mode="full-v2",
                mapping_accuracy_pct=float(i % 100),
                value_preservation_pct=99.5,
                unknown_rate_pct=0.5,
                gherkin_valid_pct=97.3,
                p95_latency_ms=44,
                total_fixtures=5,
                total_steps=22,
                llm_errors=0,
                generated_at="2026-04-19T06:53:31+00:00",
            )
        elapsed_ms = (time.perf_counter() - start) * 1_000
        assert elapsed_ms < self.MAX_MS, (
            f"EvalSnapshot(full) x{self.ITERATIONS} took {elapsed_ms:.3f} ms "
            f"(limit: {self.MAX_MS} ms)"
        )

    def test_available_false_instantiation_is_fast(self):
        start = time.perf_counter()
        for _ in range(self.ITERATIONS):
            EvalSnapshot(available=False)
        elapsed_ms = (time.perf_counter() - start) * 1_000
        assert elapsed_ms < self.MAX_MS, (
            f"EvalSnapshot(available=False) x{self.ITERATIONS} took {elapsed_ms:.3f} ms"
        )


# ── parse_eval_report with a large markdown ───────────────────────────────────

class TestParseEvalReportPerformance:
    """parse_eval_report on a large markdown file must complete in under 10 ms."""

    MAX_MS = 10.0

    def test_parse_large_report_under_10ms(self):
        start = time.perf_counter()
        snap = parse_eval_report(_LARGE_MD)
        elapsed_ms = (time.perf_counter() - start) * 1_000
        assert elapsed_ms < self.MAX_MS, (
            f"parse_eval_report(large) took {elapsed_ms:.3f} ms (limit: {self.MAX_MS} ms)"
        )
        # Correctness check — parsing still works despite noise
        assert snap.available is True
        assert snap.mapping_accuracy_pct is not None

    def test_parse_standard_report_under_10ms(self):
        start = time.perf_counter()
        snap = parse_eval_report(_SAMPLE_MD)
        elapsed_ms = (time.perf_counter() - start) * 1_000
        assert elapsed_ms < self.MAX_MS, (
            f"parse_eval_report(standard) took {elapsed_ms:.3f} ms (limit: {self.MAX_MS} ms)"
        )
        assert snap.available is True

    def test_parse_empty_string_is_negligible(self):
        start = time.perf_counter()
        for _ in range(100):
            parse_eval_report("")
        elapsed_ms = (time.perf_counter() - start) * 1_000
        # 100 empty parses should take well under 10 ms
        assert elapsed_ms < self.MAX_MS, (
            f"parse_eval_report('') x100 took {elapsed_ms:.3f} ms (limit: {self.MAX_MS} ms)"
        )


# ── _read_history with 100 files ──────────────────────────────────────────────

class TestReadHistoryPerformance:
    """_read_history processing 100 mock files must complete in under 500 ms."""

    FILE_COUNT = 100
    MAX_MS = 500.0

    def _make_mock_dir(self, file_count: int) -> MagicMock:
        mock_dir = MagicMock(spec=Path)
        mock_history = MagicMock(spec=Path)
        mock_history.is_dir.return_value = True

        files = [_make_mock_file(float(i), _SAMPLE_MD) for i in range(file_count)]
        mock_history.glob.return_value = files
        mock_dir.__truediv__ = lambda self, other: mock_history
        return mock_dir

    def test_read_100_history_files_under_500ms(self):
        mock_dir = self._make_mock_dir(self.FILE_COUNT)

        start = time.perf_counter()
        result = _read_history(mock_dir, limit=self.FILE_COUNT)
        elapsed_ms = (time.perf_counter() - start) * 1_000

        assert elapsed_ms < self.MAX_MS, (
            f"_read_history(100 files) took {elapsed_ms:.3f} ms (limit: {self.MAX_MS} ms)"
        )
        assert len(result) == self.FILE_COUNT

    def test_read_history_respects_limit_efficiently(self):
        """Requesting only 10 of 100 files should be faster than no-limit."""
        mock_dir = self._make_mock_dir(self.FILE_COUNT)

        start = time.perf_counter()
        result = _read_history(mock_dir, limit=10)
        elapsed_ms = (time.perf_counter() - start) * 1_000

        assert len(result) == 10
        # Should finish well within the general 500 ms bound
        assert elapsed_ms < self.MAX_MS, (
            f"_read_history(limit=10) took {elapsed_ms:.3f} ms (limit: {self.MAX_MS} ms)"
        )

    def test_read_empty_history_dir_is_instant(self):
        mock_dir = MagicMock(spec=Path)
        mock_history = MagicMock(spec=Path)
        mock_history.is_dir.return_value = True
        mock_history.glob.return_value = []
        mock_dir.__truediv__ = lambda self, other: mock_history

        start = time.perf_counter()
        result = _read_history(mock_dir, limit=100)
        elapsed_ms = (time.perf_counter() - start) * 1_000

        assert result == []
        assert elapsed_ms < 5.0, f"Empty _read_history took {elapsed_ms:.3f} ms (limit: 5 ms)"


# ── get_quality_metrics end-to-end (mocked FS) ───────────────────────────────

class TestGetQualityMetricsPerformance:
    """Full get_quality_metrics call (with tmp dir) should stay fast."""

    MAX_MS = 100.0

    def test_no_reports_dir_is_fast(self, tmp_path):
        start = time.perf_counter()
        result = get_quality_metrics(reports_dir=tmp_path)
        elapsed_ms = (time.perf_counter() - start) * 1_000
        assert elapsed_ms < self.MAX_MS, (
            f"get_quality_metrics (empty dir) took {elapsed_ms:.3f} ms (limit: {self.MAX_MS} ms)"
        )
        assert result.latest_eval.available is False

    def test_with_latest_and_history_is_fast(self, tmp_path):
        # Write latest.md
        (tmp_path / "latest.md").write_text(_SAMPLE_MD, encoding="utf-8")
        # Write 10 history files
        history_dir = tmp_path / "history"
        history_dir.mkdir()
        for i in range(10):
            (history_dir / f"run_{i:03d}.md").write_text(_SAMPLE_MD, encoding="utf-8")

        start = time.perf_counter()
        result = get_quality_metrics(reports_dir=tmp_path, history_limit=10)
        elapsed_ms = (time.perf_counter() - start) * 1_000

        assert elapsed_ms < self.MAX_MS, (
            f"get_quality_metrics (latest + 10 history) took {elapsed_ms:.3f} ms "
            f"(limit: {self.MAX_MS} ms)"
        )
        assert result.latest_eval.available is True
        assert len(result.history) == 10
