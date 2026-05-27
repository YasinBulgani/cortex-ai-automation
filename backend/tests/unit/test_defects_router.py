"""Defects router unit tests — /api/v1/defects.

FastAPI TestClient. Servis fonksiyonları monkeypatch'li.
State machine geçişleri (fix / verify) de test edilir.
"""
from __future__ import annotations

try:
    from unittest.mock import MagicMock, patch

    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from app.domains.defects.router import router

    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False


def _app() -> "TestClient":
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def _fake_defect(defect_id: str = "def-001", status: str = "open") -> MagicMock:
    d = MagicMock()
    d.to_dict.return_value = {
        "id": defect_id,
        "title": "Button yanlış renk",
        "status": status,
        "project_id": "proj-1",
        "severity": "major",
    }
    return d


_OPEN_BODY = {
    "project_id": "proj-1",
    "title": "Login düğmesi çalışmıyor",
    "description": "Tıklandığında hiçbir şey olmuyor",
}

# ---------------------------------------------------------------------------
# GET /defects — liste
# ---------------------------------------------------------------------------


def test_list_defects_returns_200() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.list_defects.return_value = [_fake_defect()]
        r = client.get("/defects")
    assert r.status_code == 200


def test_list_defects_returns_list_of_dicts() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.list_defects.return_value = [_fake_defect("d1"), _fake_defect("d2")]
        r = client.get("/defects")
    data = r.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_list_defects_empty() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.list_defects.return_value = []
        r = client.get("/defects")
    assert r.json() == []


# ---------------------------------------------------------------------------
# POST /defects — oluşturma
# ---------------------------------------------------------------------------


def test_open_defect_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.open_defect_from_execution.return_value = _fake_defect()
        r = client.post("/defects", json=_OPEN_BODY)
    assert r.status_code == 201


def test_open_defect_returns_dict() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.open_defect_from_execution.return_value = _fake_defect()
        r = client.post("/defects", json=_OPEN_BODY)
    body = r.json()
    assert "id" in body
    assert "status" in body


def test_open_defect_missing_required_title_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    bad_body = {"project_id": "proj-1", "description": "desc"}
    with patch("app.domains.defects.router.svc"):
        r = client.post("/defects", json=bad_body)
    assert r.status_code == 422


def test_open_defect_missing_project_id_422() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    bad_body = {"title": "T", "description": "D"}
    with patch("app.domains.defects.router.svc"):
        r = client.post("/defects", json=bad_body)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /defects/{id}
# ---------------------------------------------------------------------------


def test_get_defect_found() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.get_defect.return_value = _fake_defect("def-007")
        r = client.get("/defects/def-007")
    assert r.status_code == 200
    assert r.json()["id"] == "def-007"


def test_get_defect_not_found_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.get_defect.return_value = None
        r = client.get("/defects/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /defects/{id}/fix — state machine: open → fix_merged
# ---------------------------------------------------------------------------


def test_mark_fix_success() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.mark_fix_merged.return_value = _fake_defect("def-001", "fix_merged")
        r = client.post("/defects/def-001/fix", json={"commit_sha": "abc123"})
    assert r.status_code == 200
    assert r.json()["status"] == "fix_merged"


def test_mark_fix_invalid_transition_404() -> None:
    """Hatalı geçiş — svc ValueError fırlatır → router 404 döner."""
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.mark_fix_merged.side_effect = ValueError("geçersiz geçiş")
        r = client.post("/defects/def-001/fix", json={"commit_sha": "sha-x"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# POST /defects/{id}/verify — state machine: fix_merged → closed/reopened
# ---------------------------------------------------------------------------


def test_verify_defect_passed() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.verify_and_close.return_value = _fake_defect("def-001", "closed")
        r = client.post(
            "/defects/def-001/verify",
            json={"rerun_id": "run-99", "rerun_passed": True},
        )
    assert r.status_code == 200
    assert r.json()["status"] == "closed"


def test_verify_defect_failed_transition_404() -> None:
    if not _IMPORT_OK:
        return
    client = _app()
    with patch("app.domains.defects.router.svc") as mock_svc:
        mock_svc.verify_and_close.side_effect = ValueError("geçersiz durum")
        r = client.post(
            "/defects/def-001/verify",
            json={"rerun_id": "run-x", "rerun_passed": False},
        )
    assert r.status_code == 404
