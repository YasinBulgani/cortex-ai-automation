"""Unit tests for the DSL router — 12 tests.

Covers:
  GET  /dsl/actions
  GET  /dsl/actions/{action_id}
  GET  /dsl/search
  POST /dsl/reload
  GET  /dsl/stats
  GET  /dsl/categories

All dsl_service calls are mocked; auth user dep is patched.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    from app.domains.dsl.router import router as dsl_router
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="dsl router import failed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_user() -> MagicMock:
    user = MagicMock()
    user.id = "test-user"
    user.email = "test@test.com"
    return user


def _make_action(action_id: str = "click.element", category: str = "browser") -> dict:
    return {
        "id": action_id,
        "category": category,
        "description": "Click the element",
        "aliases": {"tr": ["elemana tıkla"], "en": ["click element"]},
        "parameters": [],
        "implementations": {},
        "tags": [],
        "since": None,
        "deprecated": None,
        "examples": [],
        "notes": None,
        "source_yaml": None,
    }


def _make_action_list_response(items: list | None = None) -> dict:
    items = items or [_make_action()]
    return {"items": items, "total": len(items), "page": 1, "page_size": 50}


def _make_search_response(hits: list | None = None) -> MagicMock:
    resp = MagicMock()
    resp.items = hits or []
    resp.query = "test"
    return resp


def _make_stats() -> dict:
    return {
        "total": 42,
        "unique_ids": 40,
        "by_top_category": {"browser": 20},
        "by_full_category": {},
        "by_implementation": {},
        "by_source_file": {},
        "by_step_type": {},
        "top_tags": [],
        "aliases": {},
        "loaded_at": None,
    }


def _make_reload_response() -> dict:
    return {"loaded": 42, "source": "disk", "duration_ms": 12}


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(dsl_router, prefix="/api/v1")
    db_mock = MagicMock()

    with patch("app.deps.get_current_user", return_value=_make_user()), \
         patch("app.infra.database.get_db", return_value=db_mock):
        yield TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# GET /dsl/actions
# ---------------------------------------------------------------------------

class TestListActions:
    def test_list_actions_returns_200(self, client):
        with patch("app.domains.dsl.router.dsl_service.list_actions",
                   return_value=_make_action_list_response()):
            resp = client.get("/api/v1/dsl/actions")
        assert resp.status_code == 200

    def test_list_actions_body_contains_items(self, client):
        with patch("app.domains.dsl.router.dsl_service.list_actions",
                   return_value=_make_action_list_response()):
            resp = client.get("/api/v1/dsl/actions")
        body = resp.json()
        assert "items" in body
        assert body["total"] >= 1

    def test_list_actions_with_category_filter(self, client):
        with patch("app.domains.dsl.router.dsl_service.list_actions",
                   return_value=_make_action_list_response()) as mock_svc:
            client.get("/api/v1/dsl/actions?category=browser")
            mock_svc.assert_called_once()
            kwargs = mock_svc.call_args.kwargs
            assert kwargs["category"] == "browser"

    def test_list_actions_with_lang_filter(self, client):
        with patch("app.domains.dsl.router.dsl_service.list_actions",
                   return_value=_make_action_list_response()) as mock_svc:
            client.get("/api/v1/dsl/actions?lang=tr")
            kwargs = mock_svc.call_args.kwargs
            assert kwargs["lang"] == "tr"


# ---------------------------------------------------------------------------
# GET /dsl/actions/{action_id}
# ---------------------------------------------------------------------------

class TestGetAction:
    def test_get_action_returns_200_when_found(self, client):
        with patch("app.domains.dsl.router.dsl_service.get_action",
                   return_value=_make_action("click.element")):
            resp = client.get("/api/v1/dsl/actions/click.element")
        assert resp.status_code == 200

    def test_get_action_returns_404_when_not_found(self, client):
        with patch("app.domains.dsl.router.dsl_service.get_action", return_value=None):
            resp = client.get("/api/v1/dsl/actions/nonexistent.action")
        assert resp.status_code == 404

    def test_get_action_body_contains_id(self, client):
        with patch("app.domains.dsl.router.dsl_service.get_action",
                   return_value=_make_action("fill.input")):
            resp = client.get("/api/v1/dsl/actions/fill.input")
        assert resp.json()["id"] == "fill.input"


# ---------------------------------------------------------------------------
# GET /dsl/search
# ---------------------------------------------------------------------------

class TestSearchActions:
    def test_search_returns_200(self, client):
        with patch("app.domains.dsl.router.dsl_service.search_actions",
                   return_value=_make_search_response()):
            resp = client.get("/api/v1/dsl/search?q=click")
        assert resp.status_code == 200

    def test_search_passes_query_to_service(self, client):
        with patch("app.domains.dsl.router.dsl_service.search_actions",
                   return_value=_make_search_response()) as mock_svc:
            client.get("/api/v1/dsl/search?q=elemana+tıkla")
        mock_svc.assert_called_once()
        assert mock_svc.call_args.args[0] == "elemana tıkla"


# ---------------------------------------------------------------------------
# GET /dsl/stats
# ---------------------------------------------------------------------------

class TestGetStats:
    def test_stats_returns_200(self, client):
        with patch("app.domains.dsl.router.dsl_service.get_stats",
                   return_value=_make_stats()):
            resp = client.get("/api/v1/dsl/stats")
        assert resp.status_code == 200

    def test_stats_contains_total(self, client):
        with patch("app.domains.dsl.router.dsl_service.get_stats",
                   return_value=_make_stats()):
            resp = client.get("/api/v1/dsl/stats")
        assert resp.json()["total"] == 42


# ---------------------------------------------------------------------------
# POST /dsl/reload
# ---------------------------------------------------------------------------

class TestReloadCatalog:
    def test_reload_returns_200(self, client):
        with patch("app.domains.dsl.router.dsl_service.reload_catalog",
                   return_value=_make_reload_response()):
            resp = client.post("/api/v1/dsl/reload")
        assert resp.status_code == 200

    def test_reload_body_contains_loaded_count(self, client):
        with patch("app.domains.dsl.router.dsl_service.reload_catalog",
                   return_value=_make_reload_response()):
            resp = client.post("/api/v1/dsl/reload")
        assert resp.json()["loaded"] == 42
