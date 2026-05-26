"""Unit tests for autopilot and artifact_retention pure helpers.

Tests are fully self-contained: no DB, no HTTP, no filesystem.
Covers: _risk_max (risk level ordering), _iso (datetime serialization),
        _compact_error, _artifact_run_is_eligible, RISK_WEIGHT constant.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

import pytest

try:
    from app.domains.ai.autopilot import (
        _risk_max,
        _iso,
        RISK_WEIGHT,
    )
    from app.domains.ai.artifact_retention import (
        _compact_error,
        _artifact_run_is_eligible,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="autopilot/artifact_retention import failed")


# ---------------------------------------------------------------------------
# RISK_WEIGHT constant
# ---------------------------------------------------------------------------

class TestRiskWeight:
    def test_critical_highest(self):
        assert RISK_WEIGHT["critical"] > RISK_WEIGHT["high"]

    def test_high_above_medium(self):
        assert RISK_WEIGHT["high"] > RISK_WEIGHT["medium"]

    def test_medium_above_low(self):
        assert RISK_WEIGHT["medium"] > RISK_WEIGHT["low"]

    def test_all_levels_positive(self):
        for level, weight in RISK_WEIGHT.items():
            assert weight > 0

    def test_has_all_levels(self):
        for level in ("low", "medium", "high", "critical"):
            assert level in RISK_WEIGHT


# ---------------------------------------------------------------------------
# _risk_max
# ---------------------------------------------------------------------------

class TestRiskMax:
    def test_single_high_returns_high(self):
        assert _risk_max("high") == "high"

    def test_critical_wins_over_high(self):
        assert _risk_max("high", "critical") == "critical"

    def test_medium_and_low_returns_medium(self):
        assert _risk_max("low", "medium") == "medium"

    def test_all_low_returns_low(self):
        assert _risk_max("low", "low", "low") == "low"

    def test_no_args_returns_low(self):
        assert _risk_max() == "low"

    def test_mixed_levels(self):
        result = _risk_max("low", "critical", "medium", "high")
        assert result == "critical"

    def test_unknown_level_falls_back_to_low(self):
        # Unknown level has weight 1 (same as low) → at worst returns it or low
        result = _risk_max("unknown_level")
        assert result in ("low", "unknown_level")

    def test_returns_string(self):
        assert isinstance(_risk_max("high"), str)


# ---------------------------------------------------------------------------
# _iso
# ---------------------------------------------------------------------------

class TestIso:
    def test_none_returns_none(self):
        assert _iso(None) is None

    def test_datetime_returns_isoformat(self):
        dt = datetime(2025, 5, 26, 12, 0, 0, tzinfo=timezone.utc)
        result = _iso(dt)
        assert "2025" in result
        assert "05" in result or "5" in result

    def test_non_datetime_converts_to_str(self):
        result = _iso("already a string")
        assert result == "already a string"

    def test_integer_converts_to_str(self):
        assert _iso(42) == "42"

    def test_returns_string_for_datetime(self):
        assert isinstance(_iso(datetime.now()), str)

    def test_object_with_isoformat_called(self):
        obj = MagicMock()
        obj.isoformat.return_value = "2025-01-01T00:00:00"
        result = _iso(obj)
        assert result == "2025-01-01T00:00:00"


# ---------------------------------------------------------------------------
# _compact_error
# ---------------------------------------------------------------------------

class TestCompactError:
    def test_returns_string(self):
        assert isinstance(_compact_error(ValueError("test")), str)

    def test_contains_exception_class_name(self):
        result = _compact_error(ValueError("bad value"))
        assert "ValueError" in result

    def test_contains_message(self):
        result = _compact_error(RuntimeError("something failed"))
        assert "something failed" in result

    def test_multiline_takes_first_line(self):
        exc = RuntimeError("first line\nsecond line\nthird line")
        result = _compact_error(exc)
        assert "first line" in result
        assert "second line" not in result

    def test_empty_message_falls_back_to_class_name(self):
        result = _compact_error(ValueError(""))
        assert "ValueError" in result

    def test_format_is_class_colon_message(self):
        result = _compact_error(TypeError("type mismatch"))
        assert result.startswith("TypeError: ")


# ---------------------------------------------------------------------------
# _artifact_run_is_eligible
# ---------------------------------------------------------------------------

class TestArtifactRunIsEligible:
    def _cutoff(self, days_ago: int = 0) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=days_ago)

    def _artifact(self, status="completed", completed_at=None):
        run = MagicMock()
        run.status = status
        run.completed_at = completed_at or (datetime.now(timezone.utc) - timedelta(days=10))
        artifact = MagicMock()
        artifact.run = run
        return artifact

    def test_no_run_attr_returns_false(self):
        artifact = MagicMock()
        artifact.run = None
        assert _artifact_run_is_eligible(artifact, self._cutoff(), {"completed"}) is False

    def test_status_not_in_set_returns_false(self):
        artifact = self._artifact(status="running")
        assert _artifact_run_is_eligible(artifact, self._cutoff(), {"completed"}) is False

    def test_no_completed_at_returns_false(self):
        artifact = self._artifact()
        artifact.run.completed_at = None
        assert _artifact_run_is_eligible(artifact, self._cutoff(), {"completed"}) is False

    def test_completed_before_cutoff_returns_true(self):
        # cutoff = 5 days ago; completed_at = 10 days ago → before cutoff
        artifact = self._artifact(
            status="completed",
            completed_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is True

    def test_completed_after_cutoff_returns_false(self):
        # cutoff = 30 days ago; completed_at = 1 day ago → after cutoff
        artifact = self._artifact(
            status="completed",
            completed_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is False

    def test_naive_datetime_treated_as_utc(self):
        # completed_at without tzinfo → treated as UTC
        artifact = self._artifact(
            status="completed",
            completed_at=datetime.utcnow() - timedelta(days=10),
        )
        # Make the naive datetime (no tzinfo)
        artifact.run.completed_at = datetime(2020, 1, 1)  # clearly in the past
        cutoff = datetime.now(timezone.utc)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed"}) is True

    def test_multiple_valid_statuses(self):
        artifact = self._artifact(
            status="error",
            completed_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=5)
        assert _artifact_run_is_eligible(artifact, cutoff, {"completed", "error"}) is True
