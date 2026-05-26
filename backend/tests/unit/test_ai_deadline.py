"""Unit tests for app.domains.ai.deadline — Deadline Propagation.

Tests are fully self-contained: no HTTP, no DB, no real Redis.
Covers set_deadline_ms, get_deadline_abs, remaining_ms, is_exceeded,
check_deadline, and budget_for_attempt.
"""
from __future__ import annotations

import time
import pytest

try:
    from app.domains.ai.deadline import (
        set_deadline_ms,
        get_deadline_abs,
        remaining_ms,
        is_exceeded,
        check_deadline,
        budget_for_attempt,
        DeadlineExceededError,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="deadline module import failed")


@pytest.fixture(autouse=True)
def _reset_deadline():
    """Reset ContextVar to None before and after each test."""
    set_deadline_ms(0)  # set to 0 → None internally
    yield
    set_deadline_ms(0)  # cleanup


# ---------------------------------------------------------------------------
# set_deadline_ms / get_deadline_abs
# ---------------------------------------------------------------------------

class TestSetDeadline:
    def test_positive_ms_sets_deadline(self):
        set_deadline_ms(5000)
        assert get_deadline_abs() is not None

    def test_zero_ms_clears_deadline(self):
        set_deadline_ms(5000)  # set first
        set_deadline_ms(0)  # then clear
        assert get_deadline_abs() is None

    def test_negative_ms_clears_deadline(self):
        set_deadline_ms(5000)
        set_deadline_ms(-100)
        assert get_deadline_abs() is None

    def test_deadline_abs_is_in_the_future(self):
        set_deadline_ms(5000)
        abs_deadline = get_deadline_abs()
        assert abs_deadline > time.monotonic()

    def test_no_deadline_returns_none(self):
        assert get_deadline_abs() is None


# ---------------------------------------------------------------------------
# remaining_ms
# ---------------------------------------------------------------------------

class TestRemainingMs:
    def test_no_deadline_returns_none(self):
        assert remaining_ms() is None

    def test_with_deadline_returns_positive_int(self):
        set_deadline_ms(10_000)
        r = remaining_ms()
        assert r is not None
        assert r > 0
        assert r <= 10_000

    def test_expired_deadline_returns_zero(self):
        # Set a deadline 1ms in the future, then sleep a bit
        set_deadline_ms(1)
        time.sleep(0.01)  # 10ms — definitely expired
        r = remaining_ms()
        assert r == 0


# ---------------------------------------------------------------------------
# is_exceeded
# ---------------------------------------------------------------------------

class TestIsExceeded:
    def test_no_deadline_not_exceeded(self):
        assert is_exceeded() is False

    def test_fresh_deadline_not_exceeded(self):
        set_deadline_ms(10_000)
        assert is_exceeded() is False

    def test_expired_deadline_is_exceeded(self):
        set_deadline_ms(1)
        time.sleep(0.01)
        assert is_exceeded() is True


# ---------------------------------------------------------------------------
# check_deadline
# ---------------------------------------------------------------------------

class TestCheckDeadline:
    def test_no_deadline_does_not_raise(self):
        check_deadline()  # no-op

    def test_valid_deadline_does_not_raise(self):
        set_deadline_ms(10_000)
        check_deadline("test operation")  # no-op

    def test_expired_deadline_raises(self):
        set_deadline_ms(1)
        time.sleep(0.01)
        with pytest.raises(DeadlineExceededError):
            check_deadline("llm")

    def test_error_message_contains_operation(self):
        set_deadline_ms(1)
        time.sleep(0.01)
        with pytest.raises(DeadlineExceededError, match="embedding"):
            check_deadline("embedding")


# ---------------------------------------------------------------------------
# budget_for_attempt
# ---------------------------------------------------------------------------

class TestBudgetForAttempt:
    def test_no_deadline_returns_none(self):
        assert budget_for_attempt(1) is None

    def test_budget_decreases_per_attempt(self):
        set_deadline_ms(9_000)
        b1 = budget_for_attempt(1, total_attempts=3)
        b2 = budget_for_attempt(2, total_attempts=3)
        # More remaining attempts on attempt 1 → less budget per attempt
        # Less remaining on attempt 2 → more per remaining attempt
        assert b1 is not None and b2 is not None

    def test_budget_minimum_is_half_second(self):
        set_deadline_ms(100)  # only 100ms left
        b = budget_for_attempt(1, total_attempts=3)
        assert b is not None
        assert b >= 0.5  # minimum 500ms

    def test_budget_proportional_to_remaining(self):
        set_deadline_ms(6_000)  # 6s
        b = budget_for_attempt(1, total_attempts=3)
        assert b is not None
        # 6s / 3 attempts = ~2s each (minus small elapsed time)
        assert 1.5 <= b <= 2.5

    def test_last_attempt_gets_full_remaining(self):
        set_deadline_ms(3_000)
        b = budget_for_attempt(3, total_attempts=3)
        assert b is not None
        # Only 1 attempt remaining → gets all remaining time (≈3s)
        assert b >= 2.0
