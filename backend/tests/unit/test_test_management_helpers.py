"""Unit tests for test_management/service.py pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/test_management/service.py:
    _actor_id, _days_since
"""

from __future__ import annotations

import types
from datetime import datetime, timedelta, timezone

import pytest

from app.domains.test_management.service import _actor_id, _days_since


# ── _actor_id ─────────────────────────────────────────────────────────────────


class TestActorId:
    def test_returns_user_id_as_string(self) -> None:
        user = types.SimpleNamespace(id="user-123")
        assert _actor_id(user) == "user-123"

    def test_none_user_returns_none(self) -> None:
        assert _actor_id(None) is None

    def test_converts_int_id_to_string(self) -> None:
        user = types.SimpleNamespace(id=42)
        result = _actor_id(user)
        assert result == "42"

    def test_empty_id_returns_none(self) -> None:
        # getattr returns "" for empty id, "or None" returns None
        user = types.SimpleNamespace(id="")
        assert _actor_id(user) is None

    def test_missing_id_attr_returns_none(self) -> None:
        # User without id attribute
        user = types.SimpleNamespace()
        result = _actor_id(user)
        # getattr(user, "id", "") returns ""
        assert result is None

    def test_returns_string_type(self) -> None:
        user = types.SimpleNamespace(id="abc")
        result = _actor_id(user)
        assert isinstance(result, str)


# ── _days_since ───────────────────────────────────────────────────────────────


class TestDaysSince:
    def test_none_returns_none(self) -> None:
        assert _days_since(None) is None

    def test_today_returns_zero(self) -> None:
        now = datetime.now(timezone.utc)
        result = _days_since(now)
        assert result == 0

    def test_one_day_ago_returns_one(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=1)
        result = _days_since(past)
        assert result == 1

    def test_five_days_ago(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=5)
        result = _days_since(past)
        assert result == 5

    def test_naive_datetime_treated_as_utc(self) -> None:
        past = datetime.now() - timedelta(days=3)  # naive
        result = _days_since(past)
        # Timezone offset can cause ±1 day difference
        assert 2 <= result <= 4

    def test_future_date_returns_zero(self) -> None:
        future = datetime.now(timezone.utc) + timedelta(days=5)
        result = _days_since(future)
        # max(0, ...) prevents negative
        assert result == 0

    def test_returns_int(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=2)
        assert isinstance(_days_since(past), int)

    def test_non_negative(self) -> None:
        past = datetime.now(timezone.utc) - timedelta(days=100)
        assert _days_since(past) >= 0
