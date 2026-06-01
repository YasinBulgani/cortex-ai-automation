"""Unit tests for app.domains.automation.service.

Mocks brain_service (AutomationBrainService) and AutomationRunCreate so these
tests run without DB, Redis, or any heavy infra dependency.
"""
from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

try:
    import app.domains.automation.service as automation_service
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="automation service import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_summary(**kwargs) -> MagicMock:
    summary = MagicMock()
    summary.dict.return_value = {
        "capabilities": kwargs.get("capabilities", ["playwright", "api"]),
        "total_runs": kwargs.get("total_runs", 10),
        "status": kwargs.get("status", "active"),
    }
    return summary


def _make_run(kind: str = "playwright") -> MagicMock:
    run = MagicMock()
    run.id = str(uuid.uuid4())
    run.kind = kind
    run.dict.return_value = {"id": run.id, "kind": kind, "status": "pending"}
    return run


def _make_db() -> MagicMock:
    return MagicMock()


# ---------------------------------------------------------------------------
# get_brain_summary
# ---------------------------------------------------------------------------

class TestGetBrainSummary:
    def test_returns_dict(self):
        db = _make_db()
        summary = _make_summary()
        with patch.object(automation_service.brain_service, "summary", return_value=summary):
            result = automation_service.get_brain_summary(db)
        assert isinstance(result, dict)

    def test_contains_expected_keys(self):
        db = _make_db()
        summary = _make_summary(capabilities=["api"], total_runs=5, status="idle")
        with patch.object(automation_service.brain_service, "summary", return_value=summary):
            result = automation_service.get_brain_summary(db)
        assert "capabilities" in result
        assert "status" in result

    def test_delegates_to_brain_service(self):
        db = _make_db()
        summary = _make_summary()
        with patch.object(automation_service.brain_service, "summary", return_value=summary) as mock_get:
            automation_service.get_brain_summary(db)
        mock_get.assert_called_once_with(db)


# ---------------------------------------------------------------------------
# list_runs
# ---------------------------------------------------------------------------

class TestListRuns:
    def test_returns_list(self):
        db = _make_db()
        run = _make_run()
        with patch.object(automation_service.brain_service, "list_runs", return_value=[run]):
            result = automation_service.list_runs(db)
        assert isinstance(result, list)
        assert len(result) == 1

    def test_empty_returns_empty_list(self):
        db = _make_db()
        with patch.object(automation_service.brain_service, "list_runs", return_value=[]):
            result = automation_service.list_runs(db)
        assert result == []

    def test_limit_capped_at_200(self):
        db = _make_db()
        with patch.object(automation_service.brain_service, "list_runs", return_value=[]) as mock_lr:
            automation_service.list_runs(db, limit=9999)
        _, kwargs = mock_lr.call_args
        assert kwargs.get("limit", 200) <= 200

    def test_each_item_is_dict(self):
        db = _make_db()
        runs = [_make_run("playwright"), _make_run("api")]
        with patch.object(automation_service.brain_service, "list_runs", return_value=runs):
            result = automation_service.list_runs(db)
        for item in result:
            assert isinstance(item, dict)


# ---------------------------------------------------------------------------
# create_run
# ---------------------------------------------------------------------------

class TestCreateRun:
    def test_create_run_returns_dict(self):
        db = _make_db()
        run = _make_run("api")

        fake_run_create = MagicMock()
        with patch.object(automation_service, "AutomationRunCreate", return_value=fake_run_create), \
             patch.object(automation_service.brain_service, "create_run", return_value=run):
            result = automation_service.create_run(db, config={"kind": "api"})

        assert isinstance(result, dict)
        assert "id" in result

    def test_create_run_missing_kind_raises_value_error(self):
        db = _make_db()
        with pytest.raises(ValueError, match="zorunludur"):
            automation_service.create_run(db, config={"name": "no-kind"})

    def test_create_run_empty_kind_raises_value_error(self):
        db = _make_db()
        with pytest.raises(ValueError):
            automation_service.create_run(db, config={"kind": ""})

    def test_create_run_delegates_to_brain_service(self):
        db = _make_db()
        run = _make_run("mobile")
        fake_run_create = MagicMock()
        with patch.object(automation_service, "AutomationRunCreate", return_value=fake_run_create), \
             patch.object(automation_service.brain_service, "create_run", return_value=run) as mock_create:
            automation_service.create_run(db, config={"kind": "mobile"})
        mock_create.assert_called_once_with(db, fake_run_create)
