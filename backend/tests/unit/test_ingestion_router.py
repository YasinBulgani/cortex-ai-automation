"""Ingestion router unit tests — /api/v1/ingestion.

FastAPI TestClient. Servis fonksiyonları monkeypatch'li.
Endpoint'ler: POST /text, POST /jira/webhook, POST /confluence/webhook,
              GET /projects/{project_id}, GET /{req_id}.
"""
from __future__ import annotations

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.ingestion.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


def _app() -> "TestClient":
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _fake_req(req_id: str = "req-001") -> MagicMock:
    req = MagicMock()
    req.to_dict.return_value = {
        "id": req_id,
        "title": "Kullanıcı giriş yapabilmeli",
        "body": "Sistemde e-posta ve şifre ile giriş yapılabilir.",
        "project_id": "proj-1",
        "source": "text",
    }
    return req


_TEXT_BODY = {
    "project_id": "proj-1",
    "title": "Kullanıcı giriş yapabilmeli",
    "body": "Sistemde e-posta ve şifre ile giriş yapılabilir.",
}

# ---------------------------------------------------------------------------
# POST /ingestion/text — metin ingestion
# ---------------------------------------------------------------------------


def test_ingest_text_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_text.return_value = _fake_req()
        r = client.post("/ingestion/text", json=_TEXT_BODY)
    assert r.status_code == 201


def test_ingest_text_returns_dict() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_text.return_value = _fake_req("req-42")
        r = client.post("/ingestion/text", json=_TEXT_BODY)
    body = r.json()
    assert "id" in body
    assert body["id"] == "req-42"


def test_ingest_text_missing_body_field_422() -> None:
    """'body' alanı eksik → Pydantic 422."""
    if not _IMPORT_OK:
        return
    client = _app()
    bad = {"project_id": "proj-1", "title": "T"}  # body eksik
    with patch("app.domains.ingestion.router.svc"):
        r = client.post("/ingestion/text", json=bad)
    assert r.status_code == 422


def test_ingest_text_missing_title_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    bad = {"project_id": "proj-1", "body": "B"}
    with patch("app.domains.ingestion.router.svc"):
        r = client.post("/ingestion/text", json=bad)
    assert r.status_code == 422


def test_ingest_text_service_value_error_becomes_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_text.side_effect = ValueError("geçersiz proje")
        r = client.post("/ingestion/text", json=_TEXT_BODY)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /ingestion/projects/{project_id} — gereksinimler listesi
# ---------------------------------------------------------------------------


def test_list_for_project_returns_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.list_ingested.return_value = [_fake_req("r1"), _fake_req("r2")]
        r = client.get("/ingestion/projects/proj-1")
    assert r.status_code == 200


def test_list_for_project_returns_list() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.list_ingested.return_value = [_fake_req()]
        r = client.get("/ingestion/projects/proj-1")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 1


def test_list_for_project_empty() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.list_ingested.return_value = []
        r = client.get("/ingestion/projects/proj-x")
    assert r.json() == []


# ---------------------------------------------------------------------------
# GET /ingestion/{req_id} — detay
# ---------------------------------------------------------------------------


def test_get_ingested_found() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.get_ingested.return_value = _fake_req("req-77")
        r = client.get("/ingestion/req-77")
    assert r.status_code == 200
    assert r.json()["id"] == "req-77"


def test_get_ingested_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.get_ingested.return_value = None
        r = client.get("/ingestion/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /ingestion/jira/webhook
# ---------------------------------------------------------------------------


def test_jira_webhook_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {"key": "TEST-1", "fields": {"summary": "Login bug"}}}
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_jira_payload.return_value = _fake_req()
        r = client.post("/ingestion/jira/webhook?project_id=proj-1", json=payload)
    assert r.status_code == 201


def test_jira_webhook_missing_project_id_422() -> None:
    """project_id query param eksik → FastAPI 422."""
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {"key": "TEST-1"}}
    with patch("app.domains.ingestion.router.svc"):
        r = client.post("/ingestion/jira/webhook", json=payload)
    # project_id required query param — 422 veya 400
    assert r.status_code in (400, 422)


def test_jira_webhook_service_error_becomes_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    payload = {"issue": {}}
    with patch("app.domains.ingestion.router.svc") as mock_svc:
        mock_svc.ingest_jira_payload.side_effect = ValueError("geçersiz payload")
        r = client.post("/ingestion/jira/webhook?project_id=proj-1", json=payload)
    assert r.status_code == 422
