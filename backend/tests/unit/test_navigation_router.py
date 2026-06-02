"""Navigation router unit tests — /api/v1/navigation.

FastAPI TestClient. Service functions (get_nav_tree, get_user_bookmarks,
add_bookmark, remove_bookmark) are mocked via unittest.mock.patch.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.navigation.router import router as navigation_router

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(navigation_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


_SERVICE_MODULE = "app.domains.navigation.router"

_FAKE_TREE = [
    {"label": "Dashboard", "path": "/dashboard", "children": []},
    {"label": "Projects", "path": "/projects", "children": [
        {"label": "Overview", "path": "/projects/overview", "children": []}
    ]},
]


# ---------------------------------------------------------------------------
# GET /api/v1/navigation/tree
# ---------------------------------------------------------------------------


def test_nav_tree_returns_200() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.get_nav_tree", return_value=_FAKE_TREE):
        r = client.get("/api/v1/navigation/tree")
    assert r.status_code == 200


def test_nav_tree_returns_list() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.get_nav_tree", return_value=_FAKE_TREE):
        r = client.get("/api/v1/navigation/tree")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_nav_tree_empty() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.get_nav_tree", return_value=[]):
        r = client.get("/api/v1/navigation/tree")
    assert r.json() == []


def test_nav_tree_has_expected_keys() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.get_nav_tree", return_value=_FAKE_TREE):
        r = client.get("/api/v1/navigation/tree")
    first = r.json()[0]
    assert "label" in first
    assert "path" in first


# ---------------------------------------------------------------------------
# GET /api/v1/navigation/bookmarks/{user_id}
# ---------------------------------------------------------------------------


def test_get_bookmarks_returns_200() -> None:
    client = _app()
    with patch(
        f"{_SERVICE_MODULE}.get_user_bookmarks",
        return_value=["/dashboard", "/projects"],
    ):
        r = client.get("/api/v1/navigation/bookmarks/user-1")
    assert r.status_code == 200


def test_get_bookmarks_returns_list() -> None:
    client = _app()
    bookmarks = ["/dashboard", "/settings"]
    with patch(f"{_SERVICE_MODULE}.get_user_bookmarks", return_value=bookmarks):
        r = client.get("/api/v1/navigation/bookmarks/user-1")
    data = r.json()
    assert isinstance(data, list)
    assert data == bookmarks


def test_get_bookmarks_empty_for_new_user() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.get_user_bookmarks", return_value=[]):
        r = client.get("/api/v1/navigation/bookmarks/new-user")
    assert r.json() == []


# ---------------------------------------------------------------------------
# POST /api/v1/navigation/bookmarks/{user_id}
# ---------------------------------------------------------------------------


def test_add_bookmark_returns_ok_true() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.add_bookmark", return_value=None):
        r = client.post(
            "/api/v1/navigation/bookmarks/user-1",
            json={"path": "/dashboard"},
        )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_add_bookmark_invalid_path_raises_422() -> None:
    client = _app()
    with patch(
        f"{_SERVICE_MODULE}.add_bookmark",
        side_effect=ValueError("Invalid path: must start with /"),
    ):
        r = client.post(
            "/api/v1/navigation/bookmarks/user-1",
            json={"path": "invalid-no-slash"},
        )
    assert r.status_code == 422


def test_add_bookmark_missing_path_field_422() -> None:
    """Missing required field returns 422 from Pydantic validation."""
    client = _app()
    with patch(f"{_SERVICE_MODULE}.add_bookmark", return_value=None):
        r = client.post("/api/v1/navigation/bookmarks/user-1", json={})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/navigation/bookmarks/{user_id}/{path}
# ---------------------------------------------------------------------------


def test_delete_bookmark_returns_ok_true() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.remove_bookmark", return_value=None):
        r = client.delete("/api/v1/navigation/bookmarks/user-1/dashboard")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_delete_bookmark_not_found_404() -> None:
    client = _app()
    with patch(
        f"{_SERVICE_MODULE}.remove_bookmark",
        side_effect=KeyError("Bookmark not found: /ghost"),
    ):
        r = client.delete("/api/v1/navigation/bookmarks/user-1/ghost")
    assert r.status_code == 404
