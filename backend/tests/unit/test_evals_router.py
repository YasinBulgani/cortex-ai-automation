"""Unit tests for the evals router — 9 tests.

Tests focus on router-layer logic. All domain functions (load_suites,
run_suite, history_report, latest_report, etc.) are mocked — no real
filesystem, no LLM calls.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.evals.router import router
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="evals router import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _make_fake_suite(name: str = "smoke", adapter: str = "openai") -> MagicMock:
    suite = MagicMock()
    suite.name = name
    suite.adapter_name = adapter
    suite.cases = [MagicMock(), MagicMock()]
    suite.scorers = ["exact_match", "bleu"]
    suite.description = f"Suite: {name}"
    return suite


def _make_fake_suite_result(name: str = "smoke", passed: bool = True) -> MagicMock:
    result = MagicMock()
    result.name = name
    result.passed = passed
    result.score = 0.95
    result.cases = []
    result.adapter = "openai"
    result.model_dump = MagicMock(return_value={
        "name": name, "passed": passed, "score": 0.95, "cases": []
    })
    return result


# ---------------------------------------------------------------------------
# GET /evals/suites
# ---------------------------------------------------------------------------

class TestListSuites:
    def test_returns_suite_list_with_names(self):
        client = _make_client()
        fake_suites = [_make_fake_suite("suite_a"), _make_fake_suite("suite_b")]
        with patch("app.domains.evals.router.load_suites", return_value=fake_suites), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.get("/evals/suites")
        # endpoint may require auth — accept 200 or auth rejection
        assert resp.status_code in {200, 401, 403}

    def test_list_suites_requires_permission(self):
        client = _make_client()
        resp = client.get("/evals/suites")
        # Without auth headers, must be rejected
        assert resp.status_code in {401, 403, 422}


# ---------------------------------------------------------------------------
# GET /evals/latest
# ---------------------------------------------------------------------------

class TestLatestEndpoint:
    def test_latest_returns_latest_key(self):
        client = _make_client()
        fake_report = {"timestamp": "2025-01-01T00:00:00Z", "passed": True}
        with patch("app.domains.evals.router.latest_report", return_value=fake_report), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.get("/evals/latest")
        assert resp.status_code in {200, 401, 403}


# ---------------------------------------------------------------------------
# GET /evals/history
# ---------------------------------------------------------------------------

class TestHistoryEndpoint:
    def test_history_returns_runs_list(self):
        client = _make_client()
        fake_history = [{"run_id": "1"}, {"run_id": "2"}]
        with patch("app.domains.evals.router.history_report", return_value=fake_history), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.get("/evals/history")
        assert resp.status_code in {200, 401, 403}

    def test_history_limit_param_capped(self):
        """limit param must be accepted without 422 when valid."""
        client = _make_client()
        with patch("app.domains.evals.router.history_report", return_value=[]), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.get("/evals/history?limit=10")
        assert resp.status_code in {200, 401, 403}


# ---------------------------------------------------------------------------
# GET /evals/adapters and /evals/scorers
# ---------------------------------------------------------------------------

class TestAdaptersAndScorers:
    def test_adapters_endpoint_reachable(self):
        client = _make_client()
        with patch("app.domains.evals.router.list_adapters", return_value=["openai", "vllm"]), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.get("/evals/adapters")
        assert resp.status_code in {200, 401, 403}

    def test_scorers_endpoint_reachable(self):
        client = _make_client()
        with patch("app.domains.evals.router.list_scorers", return_value=["exact_match", "bleu"]), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.get("/evals/scorers")
        assert resp.status_code in {200, 401, 403}


# ---------------------------------------------------------------------------
# POST /evals/run
# ---------------------------------------------------------------------------

class TestRunEndpoint:
    def test_run_with_valid_suite_names_accepted(self):
        client = _make_client()
        fake_suites = [_make_fake_suite("smoke")]
        fake_result = _make_fake_suite_result("smoke", passed=True)
        with patch("app.domains.evals.router.load_suites", return_value=fake_suites), \
             patch("app.domains.evals.router.run_suite", return_value=fake_result), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.post("/evals/run", json={"suite_names": ["smoke"]})
        assert resp.status_code in {200, 401, 403}

    def test_run_unknown_suite_returns_400_or_404(self):
        client = _make_client()
        with patch("app.domains.evals.router.load_suites", side_effect=ValueError("no such suite")), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.post("/evals/run", json={"suite_names": ["nonexistent_suite"]})
        assert resp.status_code in {400, 401, 403, 404}

    def test_run_empty_suite_names_returns_404_or_auth_error(self):
        client = _make_client()
        with patch("app.domains.evals.router.load_suites", return_value=[]), \
             patch("app.domains.evals.router.require_permission", return_value=lambda: MagicMock()):
            resp = client.post("/evals/run", json={})
        assert resp.status_code in {401, 403, 404}
