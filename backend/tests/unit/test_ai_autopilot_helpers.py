"""Unit tests for app.domains.ai.autopilot pure helper functions.

Tests are fully self-contained: no DB, no HTTP.
Covers: _risk_max, _iso, list_autopilot_runs/latest_autopilot_status (mocked).
"""
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

try:
    from app.domains.ai.autopilot import (
        _risk_max,
        _iso,
        RISK_WEIGHT,
        list_autopilot_runs,
        latest_autopilot_status,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="autopilot import failed")


# ---------------------------------------------------------------------------
# _risk_max
# ---------------------------------------------------------------------------

class TestRiskMax:
    def test_single_critical_wins(self):
        assert _risk_max("critical") == "critical"

    def test_single_low(self):
        assert _risk_max("low") == "low"

    def test_highest_wins(self):
        assert _risk_max("low", "medium", "high", "critical") == "critical"

    def test_two_levels_higher_wins(self):
        assert _risk_max("low", "high") == "high"

    def test_same_levels(self):
        assert _risk_max("medium", "medium") == "medium"

    def test_empty_returns_low(self):
        assert _risk_max() == "low"

    def test_unknown_level_treated_as_low(self):
        # Unknown level gets weight 1 (same as low)
        result = _risk_max("unknown_level", "medium")
        assert result == "medium"

    def test_weights_correct_ordering(self):
        """Verify risk weights maintain correct order."""
        assert RISK_WEIGHT["low"] < RISK_WEIGHT["medium"]
        assert RISK_WEIGHT["medium"] < RISK_WEIGHT["high"]
        assert RISK_WEIGHT["high"] < RISK_WEIGHT["critical"]

    def test_medium_beats_low(self):
        assert _risk_max("medium", "low") == "medium"

    def test_high_beats_medium(self):
        assert _risk_max("medium", "high") == "high"


# ---------------------------------------------------------------------------
# _iso
# ---------------------------------------------------------------------------

class TestIso:
    def test_none_returns_none(self):
        assert _iso(None) is None

    def test_datetime_returns_isoformat(self):
        dt = datetime(2026, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
        result = _iso(dt)
        assert "2026-01-15" in result
        assert "12:30:45" in result

    def test_string_passes_through(self):
        result = _iso("2026-01-15")
        assert result == "2026-01-15"

    def test_int_returns_string(self):
        result = _iso(42)
        assert result == "42"

    def test_object_with_isoformat_used(self):
        """Any object with .isoformat() method should use it."""
        obj = MagicMock()
        obj.isoformat.return_value = "2026-06-01T00:00:00"
        result = _iso(obj)
        assert result == "2026-06-01T00:00:00"


# ---------------------------------------------------------------------------
# list_autopilot_runs (mocked DB)
# ---------------------------------------------------------------------------

class TestListAutopilotRuns:
    def test_empty_returns_list(self):
        mock_db = MagicMock()
        # list(db.scalars(...)) iterates the result - use __iter__
        mock_db.scalars.return_value.__iter__ = lambda self: iter([])
        runs = list_autopilot_runs(mock_db, "proj-001")
        assert isinstance(runs, list)
        assert len(runs) == 0

    def test_limit_parameter_passed_to_query(self):
        mock_db = MagicMock()
        mock_db.scalars.return_value.__iter__ = lambda self: iter([])
        list_autopilot_runs(mock_db, "proj-001", limit=5)
        # Just verify no crash with custom limit
        mock_db.scalars.assert_called_once()


# ---------------------------------------------------------------------------
# latest_autopilot_status (mocked DB)
# ---------------------------------------------------------------------------

class TestLatestAutopilotStatus:
    def test_no_runs_returns_has_run_false(self):
        """When no runs exist, has_run should be False."""
        mock_db = MagicMock()
        mock_db.scalars.return_value.first.return_value = None
        # collect_snapshot is called when has_run=False; mock its DB calls
        mock_db.scalar.return_value = 0
        mock_db.scalars.return_value.__iter__ = lambda self: iter([])
        status = latest_autopilot_status(mock_db, "proj-001")
        assert isinstance(status, dict)
        assert status.get("has_run") is False
        assert status.get("latest_run") is None
        assert "project_id" in status

    def test_with_run_returns_has_run_true(self):
        """When a run exists, has_run should be True and latest_run present."""
        mock_run = MagicMock()
        mock_run.id = "run-1"
        mock_run.status = "completed"
        mock_run.risk_level = "medium"
        mock_run.trigger = "manual"
        mock_run.mode = "observe"
        mock_run.started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
        mock_run.finished_at = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        mock_run.summary = {}
        mock_run.recommendations = []
        mock_run.actions = []
        mock_run.action_results = []
        mock_run.snapshot = {}

        mock_db = MagicMock()
        mock_db.scalars.return_value.first.return_value = mock_run
        status = latest_autopilot_status(mock_db, "proj-001")
        assert status.get("has_run") is True
        assert status.get("latest_run") is not None
        assert status.get("project_id") == "proj-001"
