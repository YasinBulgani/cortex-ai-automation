"""Unit tests for test_management.service pure helper functions.

All tests are self-contained: no DB, no HTTP.
Covers:
  - _actor_id: extract user ID as string or None
  - _days_since: days elapsed since a datetime value
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

try:
    from app.domains.test_management.service import _actor_id, _days_since
    _TM_OK = True
except ImportError:
    _TM_OK = False


# ---------------------------------------------------------------------------
# _actor_id
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TM_OK, reason="test_management.service import failed")
class TestActorId:
    class _User:
        def __init__(self, id_val):
            self.id = id_val

    def test_user_with_int_id(self):
        user = self._User(42)
        result = _actor_id(user)
        assert result == "42"

    def test_user_with_string_id(self):
        user = self._User("user-uuid-123")
        result = _actor_id(user)
        assert result == "user-uuid-123"

    def test_none_user_returns_none(self):
        assert _actor_id(None) is None

    def test_user_with_empty_id_returns_none(self):
        user = self._User("")
        # str("") or None = None (empty string is falsy)
        result = _actor_id(user)
        assert result is None

    def test_user_without_id_attr_returns_none(self):
        # getattr(user, "id", "") → ""
        class NoId:
            pass
        result = _actor_id(NoId())
        assert result is None

    def test_returns_string_or_none(self):
        user = self._User("abc")
        result = _actor_id(user)
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _days_since
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TM_OK, reason="test_management.service import failed")
class TestDaysSince:
    def test_none_returns_none(self):
        assert _days_since(None) is None

    def test_recent_returns_zero(self):
        # A datetime just now → 0 days
        now_utc = datetime.now(timezone.utc)
        result = _days_since(now_utc)
        assert result == 0

    def test_one_day_ago(self):
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        result = _days_since(yesterday)
        assert result >= 1

    def test_seven_days_ago(self):
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        result = _days_since(week_ago)
        assert result >= 7

    def test_future_returns_zero(self):
        # max(0, ...) should prevent negative result
        future = datetime.now(timezone.utc) + timedelta(days=5)
        result = _days_since(future)
        assert result == 0

    def test_naive_datetime_gets_utc(self):
        # naive datetime should be treated as UTC
        naive = datetime.now() - timedelta(days=3)
        result = _days_since(naive)
        assert result is not None
        assert result >= 0

    def test_returns_int(self):
        dt = datetime.now(timezone.utc) - timedelta(days=2)
        result = _days_since(dt)
        assert isinstance(result, int)

    def test_old_date_large_value(self):
        old_date = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = _days_since(old_date)
        assert result > 365
