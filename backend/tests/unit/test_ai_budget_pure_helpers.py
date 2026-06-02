"""Unit tests for ai.budget pure helper functions.

All tests are self-contained: no DB, no HTTP.
Covers:
  - _today_utc_bounds: returns (start_of_day_utc, end_of_day_utc) tuple
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

try:
    from app.domains.ai.budget import _today_utc_bounds
    _BG_OK = True
except ImportError:
    _BG_OK = False


# ---------------------------------------------------------------------------
# _today_utc_bounds
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _BG_OK, reason="ai.budget import failed")
class TestTodayUtcBounds:
    def test_returns_tuple_of_two(self):
        result = _today_utc_bounds()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_both_are_datetime(self):
        start, end = _today_utc_bounds()
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_both_are_utc(self):
        start, end = _today_utc_bounds()
        assert start.tzinfo is not None
        assert end.tzinfo is not None

    def test_start_is_midnight(self):
        start, _ = _today_utc_bounds()
        assert start.hour == 0
        assert start.minute == 0
        assert start.second == 0
        assert start.microsecond == 0

    def test_end_is_next_midnight(self):
        _, end = _today_utc_bounds()
        assert end.hour == 0
        assert end.minute == 0
        assert end.second == 0
        assert end.microsecond == 0

    def test_end_is_24_hours_after_start(self):
        start, end = _today_utc_bounds()
        assert end - start == timedelta(days=1)

    def test_start_before_end(self):
        start, end = _today_utc_bounds()
        assert start < end

    def test_start_is_today_utc(self):
        start, _ = _today_utc_bounds()
        now = datetime.now(timezone.utc)
        assert start.date() == now.date()
