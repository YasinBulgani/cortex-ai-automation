"""
jira_bp route testleri.
20 test — tüm endpoint'ler kapsandı.
"""
import importlib
import sys
import types
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def jira_client(monkeypatch, tmp_path):
    """Minimal Flask app with only jira_bp; file I/O redirected to tmp_path."""

    # Redirect the config file path to a temp location
    config_path = tmp_path / "jira_config.json"

    # Remove cached module so patches take effect cleanly
    for key in list(sys.modules.keys()):
        if "jira_routes" in key:
            del sys.modules[key]

    import engine.routes.jira_routes as jr_mod  # type: ignore
    monkeypatch.setattr(jr_mod, "JIRA_CONFIG_PATH", config_path, raising=True)

    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(jr_mod.jira_bp)

    with app.test_client() as client:
        yield client, config_path, jr_mod


# ── GET /api/jira/config ──────────────────────────────────────────────────────

def test_get_config_empty(jira_client):
    """GET /api/jira/config with no config file returns empty dict."""
    client, _, _ = jira_client
    resp = client.get("/api/jira/config")
    assert resp.status_code == 200
    assert resp.get_json() == {}


def test_get_config_masks_token(jira_client):
    """GET /api/jira/config masks the token field."""
    client, cfg_path, _ = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "user@example.com",
        "token": "supersecretXYZ",
        "project_key": "PROJ",
    }))
    resp = client.get("/api/jira/config")
    data = resp.get_json()
    assert data["token"].startswith("***")
    # "supersecretXYZ" — last 4 chars are "tXYZ"
    assert data["token"].endswith("tXYZ")


def test_get_config_returns_url_and_email(jira_client):
    """GET /api/jira/config returns url and email as-is."""
    client, cfg_path, _ = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "qa@test.com",
        "token": "tok1234",
    }))
    data = client.get("/api/jira/config").get_json()
    assert data["url"] == "https://jira.example.com"
    assert data["email"] == "qa@test.com"


# ── POST /api/jira/config ─────────────────────────────────────────────────────

def test_save_config_success(jira_client):
    """POST /api/jira/config with valid data returns ok."""
    client, cfg_path, _ = jira_client
    resp = client.post(
        "/api/jira/config",
        json={"url": "https://jira.example.com", "email": "a@b.com", "token": "tok"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    saved = json.loads(cfg_path.read_text())
    assert saved["email"] == "a@b.com"


def test_save_config_missing_url_returns_400(jira_client):
    client, _, _ = jira_client
    resp = client.post(
        "/api/jira/config",
        json={"email": "a@b.com", "token": "tok"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_save_config_missing_email_returns_400(jira_client):
    client, _, _ = jira_client
    resp = client.post(
        "/api/jira/config",
        json={"url": "https://jira.example.com", "token": "tok"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_save_config_missing_token_returns_400(jira_client):
    client, _, _ = jira_client
    resp = client.post(
        "/api/jira/config",
        json={"url": "https://jira.example.com", "email": "a@b.com"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_save_config_strips_trailing_slash(jira_client):
    """URL trailing slash is stripped on save."""
    client, cfg_path, _ = jira_client
    client.post(
        "/api/jira/config",
        json={"url": "https://jira.example.com/", "email": "a@b.com", "token": "tok"},
        content_type="application/json",
    )
    saved = json.loads(cfg_path.read_text())
    assert not saved["url"].endswith("/")


# ── GET /api/jira/projects ────────────────────────────────────────────────────

def test_list_projects_no_config_returns_400(jira_client):
    """Without config, GET /api/jira/projects returns 400."""
    client, _, _ = jira_client
    resp = client.get("/api/jira/projects")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_list_projects_jira_not_installed_returns_400(jira_client, monkeypatch):
    """When jira library is not installed, projects endpoint returns error."""
    client, cfg_path, jr_mod = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "a@b.com",
        "token": "tok",
    }))

    def _raise_import(*args, **kwargs):
        raise ImportError("jira not installed")

    monkeypatch.setattr(jr_mod, "get_jira_client", lambda: (None, "jira kütüphanesi yüklü değil (pip install jira)"))
    resp = client.get("/api/jira/projects")
    assert resp.status_code == 400


def test_list_projects_success(jira_client, monkeypatch):
    """GET /api/jira/projects returns project list when jira client works."""
    client, cfg_path, jr_mod = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "a@b.com",
        "token": "tok",
    }))
    proj1 = MagicMock()
    proj1.key = "PROJ"
    proj1.name = "My Project"
    mock_jira = MagicMock()
    mock_jira.projects.return_value = [proj1]
    monkeypatch.setattr(jr_mod, "get_jira_client", lambda: (mock_jira, None))

    resp = client.get("/api/jira/projects")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]["key"] == "PROJ"


# ── POST /api/jira/bugs/<id>/push ─────────────────────────────────────────────

def test_push_bug_no_config_returns_400(jira_client):
    """Bug push without Jira config returns 400."""
    client, _, _ = jira_client
    resp = client.post("/api/jira/bugs/1/push", json={}, content_type="application/json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_push_bug_jira_not_installed(jira_client, monkeypatch):
    """Bug push when jira library missing returns 400."""
    client, cfg_path, jr_mod = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "a@b.com",
        "token": "tok",
    }))
    monkeypatch.setattr(jr_mod, "get_jira_client", lambda: (None, "jira kütüphanesi yüklü değil (pip install jira)"))
    resp = client.post("/api/jira/bugs/1/push", json={}, content_type="application/json")
    assert resp.status_code == 400


def test_push_bug_success(jira_client, monkeypatch):
    """Bug push with valid config and mock client returns ok + jira_key."""
    client, cfg_path, jr_mod = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "a@b.com",
        "token": "tok",
        "project_key": "PROJ",
    }))

    mock_issue = MagicMock()
    mock_issue.key = "PROJ-42"
    mock_jira = MagicMock()
    mock_jira.create_issue.return_value = mock_issue
    monkeypatch.setattr(jr_mod, "get_jira_client", lambda: (mock_jira, None))
    monkeypatch.setattr(jr_mod, "get_bugs", lambda: [{"id": 1, "title": "Login crash", "severity": "High"}], raising=False)
    monkeypatch.setattr(jr_mod, "update_bug_jira_key", lambda bug_id, key: None, raising=False)

    # Patch the inline imports inside the route function
    import core.db as core_db_mod  # noqa: ensure importable
    monkeypatch.setattr("core.db.get_bugs", lambda: [{"id": 1, "title": "Login crash", "severity": "High"}], raising=False)
    monkeypatch.setattr("core.db.update_bug_jira_key", lambda bug_id, key: None, raising=False)

    resp = client.post("/api/jira/bugs/1/push", json={"project_key": "PROJ"}, content_type="application/json")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["jira_key"] == "PROJ-42"


# ── POST /api/jira/testcases/<id>/link ───────────────────────────────────────

def test_link_testcase_missing_jira_key_returns_400(jira_client):
    """Linking without a jira_key returns 400."""
    client, _, _ = jira_client
    resp = client.post("/api/jira/testcases/1/link", json={}, content_type="application/json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_link_testcase_no_config_returns_400(jira_client):
    """Linking when Jira not configured returns 400."""
    client, _, _ = jira_client
    resp = client.post(
        "/api/jira/testcases/1/link",
        json={"jira_key": "PROJ-10"},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_link_testcase_success(jira_client, monkeypatch):
    """Linking a test case to a Jira issue succeeds when client + TC found."""
    client, cfg_path, jr_mod = jira_client
    cfg_path.write_text(json.dumps({
        "url": "https://jira.example.com",
        "email": "a@b.com",
        "token": "tok",
    }))

    mock_jira = MagicMock()
    monkeypatch.setattr(jr_mod, "get_jira_client", lambda: (mock_jira, None))
    monkeypatch.setattr(
        "core.db.get_test_case",
        lambda tc_id: {"id": tc_id, "title": "Login TC", "priority": "P1", "steps": [
            {"action": "Open app", "expected": "App opens"}
        ]},
        raising=False,
    )

    resp = client.post(
        "/api/jira/testcases/1/link",
        json={"jira_key": "PROJ-10"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["jira_key"] == "PROJ-10"


# ── POST /api/jira/test-connection ────────────────────────────────────────────

def test_test_connection_no_config_returns_400(jira_client):
    """POST /api/jira/test-connection without config returns 400."""
    client, _, _ = jira_client
    resp = client.post("/api/jira/test-connection", json={}, content_type="application/json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()
