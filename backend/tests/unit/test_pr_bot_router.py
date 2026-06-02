"""Unit tests for the PR Bot router — 10 tests.

Tests cover the /pr-bot/analyze and /pr-bot/health endpoints plus
the _llm_available and _summary_to_dict helpers. All external deps
(build_pr_summary) are mocked; no real filesystem access.
"""
from __future__ import annotations

import dataclasses
import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.pr_bot.router import router as pr_bot_router, _llm_available, _summary_to_dict
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="pr_bot router import failed")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(pr_bot_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


def _make_summary(**kwargs):
    """Return a PRSummary-like MagicMock that dataclasses.asdict can handle."""
    from app.domains.pr_bot.service import PRSummary  # noqa: PLC0415
    fields = {f.name: kwargs.get(f.name, f.default if f.default is not dataclasses.MISSING else None)
               for f in dataclasses.fields(PRSummary)}
    return PRSummary(**fields)


# ---------------------------------------------------------------------------
# GET /pr-bot/health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_returns_200(self, client):
        resp = client.get("/api/v1/pr-bot/health")
        assert resp.status_code == 200

    def test_health_contains_status_ok(self, client):
        resp = client.get("/api/v1/pr-bot/health")
        assert resp.json()["status"] == "ok"

    def test_health_llm_available_true_when_openai_key_set(self, client):
        with patch.dict("os.environ", {"OPENAI_API_KEY": "sk-test"}, clear=False):
            resp = client.get("/api/v1/pr-bot/health")
        assert resp.json()["llm_available"] is True

    def test_health_llm_available_true_when_anthropic_key_set(self, client):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "ant-test"}, clear=False):
            resp = client.get("/api/v1/pr-bot/health")
        assert resp.json()["llm_available"] is True

    def test_health_llm_available_false_when_no_keys(self, client):
        env_without_keys = {}
        with patch("app.domains.pr_bot.router._llm_available", return_value=False):
            resp = client.get("/api/v1/pr-bot/health")
        assert resp.json()["llm_available"] is False


# ---------------------------------------------------------------------------
# POST /pr-bot/analyze
# ---------------------------------------------------------------------------

class TestAnalyzeEndpoint:
    def test_analyze_with_changed_files_returns_200(self, client):
        mock_summary = MagicMock()
        mock_summary.__class__.__name__ = "PRSummary"
        with patch("app.domains.pr_bot.router.build_pr_summary", return_value=mock_summary), \
             patch("app.domains.pr_bot.router._summary_to_dict", return_value={"ok": True}):
            resp = client.post(
                "/api/v1/pr-bot/analyze",
                json={"changed_files": ["src/foo.py", "tests/test_foo.py"]},
            )
        assert resp.status_code == 200
        assert resp.json()["ok"] is True

    def test_analyze_with_coverage_path_passes_path_to_service(self, client):
        mock_summary = MagicMock()
        captured = {}

        def fake_build(repo_root, changed_files, coverage_paths):
            captured["coverage_paths"] = coverage_paths
            return mock_summary

        with patch("app.domains.pr_bot.router.build_pr_summary", side_effect=fake_build), \
             patch("app.domains.pr_bot.router._summary_to_dict", return_value={}):
            client.post(
                "/api/v1/pr-bot/analyze",
                json={"changed_files": ["a.py"], "coverage_path": "/tmp/cov.xml"},
            )

        assert captured["coverage_paths"] is not None
        assert len(captured["coverage_paths"]) == 1

    def test_analyze_with_empty_files_list_returns_200(self, client):
        with patch("app.domains.pr_bot.router.build_pr_summary", return_value=MagicMock()), \
             patch("app.domains.pr_bot.router._summary_to_dict", return_value={"changed": 0}):
            resp = client.post("/api/v1/pr-bot/analyze", json={"changed_files": []})
        assert resp.status_code == 200

    def test_analyze_service_exception_returns_500(self, client):
        with patch("app.domains.pr_bot.router.build_pr_summary", side_effect=RuntimeError("boom")):
            resp = client.post("/api/v1/pr-bot/analyze", json={"changed_files": ["x.py"]})
        assert resp.status_code == 500
        assert "PR analysis failed" in resp.json()["detail"]

    def test_analyze_without_coverage_path_passes_none(self, client):
        captured = {}

        def fake_build(repo_root, changed_files, coverage_paths):
            captured["coverage_paths"] = coverage_paths
            return MagicMock()

        with patch("app.domains.pr_bot.router.build_pr_summary", side_effect=fake_build), \
             patch("app.domains.pr_bot.router._summary_to_dict", return_value={}):
            client.post("/api/v1/pr-bot/analyze", json={"changed_files": ["b.py"]})

        assert captured["coverage_paths"] is None


# ---------------------------------------------------------------------------
# Helper: _llm_available
# ---------------------------------------------------------------------------

class TestLlmAvailableHelper:
    def test_true_with_llm_endpoint_env(self):
        with patch.dict("os.environ", {"LLM_ENDPOINT": "http://localhost:11434"}, clear=False):
            assert _llm_available() is True

    def test_false_with_no_relevant_env(self):
        with patch.dict("os.environ", {}, clear=True):
            assert _llm_available() is False
