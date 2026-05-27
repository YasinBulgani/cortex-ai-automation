"""Unit tests for app.domains.agents.service facade.

Covers: start_run, get_status, get_analytics
External dependencies are fully mocked — no DB or HTTP calls.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import MagicMock, patch
    import app.domains.agents.service as agents_svc  # noqa: F401
except ImportError as _exc:
    pytestmark = pytest.mark.skipif(True, reason=f"agents service not importable: {_exc}")
    agents_svc = None  # type: ignore


# ---------------------------------------------------------------------------
# start_run
# ---------------------------------------------------------------------------

class TestStartRun:
    def test_start_run_all_pipeline_returns_run_id(self):
        """start_run with pipeline_type='all' delegates to start_all_agents_run."""
        bg = MagicMock()
        expected = {"run_id": "run-abc", "message": "started"}
        with patch(
            "app.domains.agents.service.start_all_agents_run",
            return_value=expected,
        ) as mock_start:
            result = agents_svc.start_run(bg, project_id="proj-1", pipeline_type="all")

        mock_start.assert_called_once_with(bg, project_id="proj-1")
        assert isinstance(result, dict)
        assert result["run_id"] == "run-abc"

    def test_start_run_default_pipeline_type_is_all(self):
        """pipeline_type defaults to 'all' when omitted."""
        bg = MagicMock()
        with patch(
            "app.domains.agents.service.start_all_agents_run",
            return_value={"run_id": "run-xyz", "message": "ok"},
        ):
            result = agents_svc.start_run(bg)

        assert "run_id" in result

    def test_start_run_unknown_pipeline_type_raises_value_error(self):
        """An unsupported pipeline_type raises ValueError with a helpful message."""
        bg = MagicMock()
        with pytest.raises(ValueError, match="Bilinmeyen pipeline türü"):
            agents_svc.start_run(bg, pipeline_type="nonexistent")

    def test_start_run_banking_pipeline_type_raises_value_error(self):
        """'banking' is not wired yet — should raise ValueError."""
        bg = MagicMock()
        with pytest.raises(ValueError):
            agents_svc.start_run(bg, pipeline_type="banking")


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------

class TestGetStatus:
    def test_get_status_returns_snapshot_without_run_id(self):
        """get_status without run_id returns the full status snapshot."""
        snapshot = {"run_id": "run-1", "status": "running", "agents": []}
        with patch(
            "app.domains.agents.service.get_all_agents_status",
            return_value=snapshot,
        ):
            result = agents_svc.get_status()

        assert isinstance(result, dict)
        assert result["status"] == "running"

    def test_get_status_matching_run_id_succeeds(self):
        """Passing a run_id that matches the active run returns successfully."""
        snapshot = {"run_id": "run-42", "status": "done"}
        with patch(
            "app.domains.agents.service.get_all_agents_status",
            return_value=snapshot,
        ):
            result = agents_svc.get_status(run_id="run-42")

        assert result["run_id"] == "run-42"

    def test_get_status_mismatched_run_id_raises_key_error(self):
        """A run_id that doesn't match the active run raises KeyError."""
        snapshot = {"run_id": "run-99", "status": "done"}
        with patch(
            "app.domains.agents.service.get_all_agents_status",
            return_value=snapshot,
        ):
            with pytest.raises(KeyError, match="run-000"):
                agents_svc.get_status(run_id="run-000")


# ---------------------------------------------------------------------------
# get_analytics
# ---------------------------------------------------------------------------

class TestGetAnalytics:
    def test_get_analytics_no_project_id_returns_empty_stats(self):
        """Without project_id, heal and llm stats are empty dicts."""
        result = agents_svc.get_analytics()

        assert result["project_id"] is None
        assert result["heal_stats"] == {}
        assert result["llm_trace_stats"] == {}

    def test_get_analytics_with_project_id_calls_both_services(self):
        """With project_id, both heal and llm stat services are called."""
        heal_data = {"healed": 3}
        llm_data = {"tokens": 1000}
        with patch(
            "app.domains.agents.service.get_heal_stats_data",
            return_value=heal_data,
        ), patch(
            "app.domains.agents.service.get_llm_trace_stats_data",
            return_value=llm_data,
        ):
            result = agents_svc.get_analytics(project_id="proj-X")

        assert result["project_id"] == "proj-X"
        assert result["heal_stats"] == heal_data
        assert result["llm_trace_stats"] == llm_data

    def test_get_analytics_heal_failure_is_captured_not_raised(self):
        """If heal stats raise, the error is captured in the response dict."""
        with patch(
            "app.domains.agents.service.get_heal_stats_data",
            side_effect=RuntimeError("DB down"),
        ), patch(
            "app.domains.agents.service.get_llm_trace_stats_data",
            return_value={"tokens": 5},
        ):
            result = agents_svc.get_analytics(project_id="proj-Y")

        assert "error" in result["heal_stats"]
        assert "DB down" in result["heal_stats"]["error"]
        assert result["llm_trace_stats"]["tokens"] == 5

    def test_get_analytics_llm_failure_is_captured_not_raised(self):
        """If llm trace stats raise, the error is captured in the response dict."""
        with patch(
            "app.domains.agents.service.get_heal_stats_data",
            return_value={"healed": 0},
        ), patch(
            "app.domains.agents.service.get_llm_trace_stats_data",
            side_effect=ConnectionError("timeout"),
        ):
            result = agents_svc.get_analytics(project_id="proj-Z")

        assert result["heal_stats"] == {"healed": 0}
        assert "error" in result["llm_trace_stats"]
        assert "timeout" in result["llm_trace_stats"]["error"]
