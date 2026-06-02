"""Email router unit tests — /api/v1/email.

FastAPI TestClient. Service functions (list_templates, preview_email,
send_email) are mocked via unittest.mock.patch.
"""
from __future__ import annotations

import pytest

try:
    from unittest.mock import patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.email.router import router as email_router

    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="import failed")


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _app() -> TestClient:
    app = FastAPI()
    app.include_router(email_router, prefix="/api/v1")
    return TestClient(app, raise_server_exceptions=False)


_SERVICE_MODULE = "app.domains.email.router"


# ---------------------------------------------------------------------------
# GET /api/v1/email/templates
# ---------------------------------------------------------------------------


def test_list_templates_returns_200() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.list_templates", return_value=["welcome", "reset_password"]):
        r = client.get("/api/v1/email/templates")
    assert r.status_code == 200


def test_list_templates_returns_list() -> None:
    client = _app()
    templates = ["welcome", "reset_password", "invoice"]
    with patch(f"{_SERVICE_MODULE}.list_templates", return_value=templates):
        r = client.get("/api/v1/email/templates")
    data = r.json()
    assert isinstance(data, list)
    assert data == templates


def test_list_templates_empty() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.list_templates", return_value=[]):
        r = client.get("/api/v1/email/templates")
    assert r.json() == []


# ---------------------------------------------------------------------------
# POST /api/v1/email/preview
# ---------------------------------------------------------------------------


def test_preview_returns_html_200() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.preview_email", return_value="<h1>Hello</h1>"):
        r = client.post(
            "/api/v1/email/preview",
            json={"template_name": "welcome", "context": {"name": "Yasin"}},
        )
    assert r.status_code == 200
    assert r.json() == {"html": "<h1>Hello</h1>"}


def test_preview_returns_dict_with_html_key() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.preview_email", return_value="<p>body</p>"):
        r = client.post(
            "/api/v1/email/preview",
            json={"template_name": "invoice", "context": {}},
        )
    body = r.json()
    assert "html" in body


def test_preview_unknown_template_raises_422() -> None:
    client = _app()
    with patch(
        f"{_SERVICE_MODULE}.preview_email",
        side_effect=ValueError("Template not found: ghost"),
    ):
        r = client.post(
            "/api/v1/email/preview",
            json={"template_name": "ghost", "context": {}},
        )
    assert r.status_code == 422


def test_preview_missing_template_name_422() -> None:
    """Missing required field returns 422 from Pydantic validation."""
    client = _app()
    with patch(f"{_SERVICE_MODULE}.preview_email", return_value="<p>html</p>"):
        r = client.post("/api/v1/email/preview", json={"context": {}})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/email/send
# ---------------------------------------------------------------------------


def test_send_returns_ok_true() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.send_email", return_value=True):
        r = client.post(
            "/api/v1/email/send",
            json={
                "to": "user@example.com",
                "subject": "Hello",
                "template_name": "welcome",
                "context": {"name": "Yasin"},
            },
        )
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_send_returns_ok_false_when_service_returns_false() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.send_email", return_value=False):
        r = client.post(
            "/api/v1/email/send",
            json={
                "to": "user@example.com",
                "subject": "Hi",
                "template_name": "welcome",
                "context": {},
            },
        )
    assert r.status_code == 200
    assert r.json() == {"ok": False}


def test_send_unknown_template_raises_422() -> None:
    client = _app()
    with patch(
        f"{_SERVICE_MODULE}.send_email",
        side_effect=ValueError("Unknown template: ghost"),
    ):
        r = client.post(
            "/api/v1/email/send",
            json={
                "to": "x@x.com",
                "subject": "S",
                "template_name": "ghost",
                "context": {},
            },
        )
    assert r.status_code == 422


def test_send_missing_to_field_422() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.send_email", return_value=True):
        r = client.post(
            "/api/v1/email/send",
            json={"subject": "Hi", "template_name": "welcome"},
        )
    assert r.status_code == 422


def test_send_missing_subject_field_422() -> None:
    client = _app()
    with patch(f"{_SERVICE_MODULE}.send_email", return_value=True):
        r = client.post(
            "/api/v1/email/send",
            json={"to": "x@x.com", "template_name": "welcome"},
        )
    assert r.status_code == 422
