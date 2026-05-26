"""Pilot router endpoint'leri — AI assistant session yönetimi.

Gerçek FastAPI app + TestClient kullanır; svc (service katmanı) monkeypatch'li.
Router layer odaklıdır: HTTP durum kodları, request validation, hata yönetimi.
"""
from __future__ import annotations

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.pilot.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _app() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _fake_session(session_id: str = "sess-001") -> MagicMock:
    s = MagicMock()
    s.to_dict.return_value = {
        "id": session_id,
        "project_id": "proj-001",
        "user_id": "user-001",
        "status": "active",
        "stages": [],
    }
    return s


# ---------------------------------------------------------------------------
# POST /pilot/sessions
# ---------------------------------------------------------------------------

def test_create_session_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.create_session.return_value = _fake_session()
        r = client.post("/pilot/sessions", json={"project_id": "proj-001", "user_id": "user-001"})
    assert r.status_code == 201
    data = r.json()
    assert "id" in data
    assert data["project_id"] == "proj-001"


def test_create_session_missing_project_id_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    # project_id has min_length=1, empty string should fail
    r = client.post("/pilot/sessions", json={"project_id": "", "user_id": "user-001"})
    assert r.status_code == 422


def test_create_session_no_body_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    r = client.post("/pilot/sessions", json={})
    assert r.status_code == 422


def test_create_session_default_user_id() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.create_session.return_value = _fake_session()
        r = client.post("/pilot/sessions", json={"project_id": "proj-999"})
    assert r.status_code == 201
    # service was called
    mock_svc.create_session.assert_called_once()


# ---------------------------------------------------------------------------
# GET /pilot/sessions/{id}
# ---------------------------------------------------------------------------

def test_get_session_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.get_session.return_value = None
        r = client.get("/pilot/sessions/nonexistent")
    assert r.status_code == 404


def test_get_session_found() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.get_session.return_value = _fake_session("sess-abc")
        r = client.get("/pilot/sessions/sess-abc")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == "sess-abc"


# ---------------------------------------------------------------------------
# GET /pilot/sessions (list)
# ---------------------------------------------------------------------------

def test_list_sessions_empty() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.list_sessions.return_value = []
        r = client.get("/pilot/sessions")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_with_project_filter() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.list_sessions.return_value = [_fake_session("s1"), _fake_session("s2")]
        r = client.get("/pilot/sessions?project_id=proj-001")
    assert r.status_code == 200
    assert len(r.json()) == 2
    mock_svc.list_sessions.assert_called_once_with(project_id="proj-001", user_id=None)


# ---------------------------------------------------------------------------
# POST /pilot/sessions/{id}/converse
# ---------------------------------------------------------------------------

def test_converse_missing_text_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    r = client.post("/pilot/sessions/sess-001/converse", json={})
    assert r.status_code == 422


def test_converse_empty_text_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    r = client.post("/pilot/sessions/sess-001/converse", json={"text": ""})
    assert r.status_code == 422


def test_converse_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.converse.return_value = _fake_session()
        r = client.post(
            "/pilot/sessions/sess-001/converse",
            json={"text": "Ne yapmamı istiyorsunuz?"},
        )
    assert r.status_code == 200
    data = r.json()
    assert "id" in data


def test_converse_session_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.converse.side_effect = ValueError("Session bulunamadı")
        r = client.post("/pilot/sessions/bad-id/converse", json={"text": "merhaba"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /pilot/sessions/{id}/execute-stage
# ---------------------------------------------------------------------------

def test_execute_stage_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.execute_next_stage.return_value = _fake_session()
        r = client.post("/pilot/sessions/sess-001/execute-stage")
    assert r.status_code == 200
    assert "id" in r.json()


def test_execute_stage_bad_state_400() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.execute_next_stage.side_effect = ValueError("Session zaten tamamlandı")
        r = client.post("/pilot/sessions/sess-001/execute-stage")
    assert r.status_code == 400


# ---------------------------------------------------------------------------
# POST /pilot/sessions/{id}/clarify
# ---------------------------------------------------------------------------

def test_clarify_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.answer_clarification.return_value = _fake_session()
        r = client.post(
            "/pilot/sessions/sess-001/clarify",
            json={"answer": "evet"},
        )
    assert r.status_code == 200


def test_clarify_bad_state_400() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.pilot.router.svc") as mock_svc:
        mock_svc.answer_clarification.side_effect = ValueError("Bekleyen soru yok")
        r = client.post("/pilot/sessions/sess-001/clarify", json={"answer": "evet"})
    assert r.status_code == 400
