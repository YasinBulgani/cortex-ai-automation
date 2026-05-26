"""
lifecycle_bp route testleri.
14 test — tüm endpoint'ler kapsandı.
"""
import sys
import types
import json
import pytest
from unittest.mock import MagicMock


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def lifecycle_client(monkeypatch):
    """Minimal Flask app with only lifecycle_bp; AIClient is stubbed."""

    # Stub core.ai_client before blueprint import
    mock_ai_instance = MagicMock()
    mock_ai_instance.ask.return_value = json.dumps({
        "summary": "Test özeti",
        "steps": ["Adım 1", "Adım 2"],
    })

    mock_ai_class = MagicMock(return_value=mock_ai_instance)

    core_mod = types.ModuleType("core")
    core_ai_mod = types.ModuleType("core.ai_client")
    core_ai_mod.AIClient = mock_ai_class
    sys.modules.setdefault("core", core_mod)
    sys.modules["core.ai_client"] = core_ai_mod

    # Remove cached module so the stub above is picked up
    for key in list(sys.modules.keys()):
        if "lifecycle_routes" in key:
            del sys.modules[key]

    import engine.routes.lifecycle_routes as lc_mod  # type: ignore

    # Replace the module-level ai_client instance with our mock
    monkeypatch.setattr(lc_mod, "ai_client", mock_ai_instance, raising=True)

    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(lc_mod.lifecycle_bp)

    with app.test_client() as client:
        yield client, mock_ai_instance


# ── POST /api/lifecycle/process-analyst ──────────────────────────────────────

def test_process_analyst_no_text_returns_400(lifecycle_client):
    """Missing text field → 400."""
    client, _ = lifecycle_client
    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_process_analyst_empty_text_returns_400(lifecycle_client):
    """Empty string text → 400."""
    client, _ = lifecycle_client
    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_process_analyst_valid_text_returns_200(lifecycle_client):
    """Valid text → 200 with summary and steps."""
    client, _ = lifecycle_client
    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Kullanıcı sisteme giriş yapmalı"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "summary" in data
    assert "steps" in data


def test_process_analyst_returns_json_content_type(lifecycle_client):
    client, _ = lifecycle_client
    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Some analysis text"},
        content_type="application/json",
    )
    assert "application/json" in resp.content_type


def test_process_analyst_steps_is_list(lifecycle_client):
    client, _ = lifecycle_client
    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Login flow analysis"},
        content_type="application/json",
    )
    data = resp.get_json()
    assert isinstance(data["steps"], list)


def test_process_analyst_ai_called_with_prompt(lifecycle_client):
    """Confirms that ai_client.ask() is called when text is provided."""
    client, mock_ai = lifecycle_client
    client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Test metin"},
        content_type="application/json",
    )
    mock_ai.ask.assert_called_once()


def test_process_analyst_markdown_wrapped_json(lifecycle_client, monkeypatch):
    """AI response wrapped in ```json ... ``` fences is unwrapped correctly."""
    client, mock_ai = lifecycle_client
    wrapped = '```json\n{"summary": "Wrapped", "steps": ["S1"]}\n```'
    mock_ai.ask.return_value = wrapped

    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Some text"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"] == "Wrapped"
    assert data["steps"] == ["S1"]


def test_process_analyst_plain_fenced_json(lifecycle_client):
    """AI response wrapped in plain ``` fences is unwrapped correctly."""
    client, mock_ai = lifecycle_client
    wrapped = '```\n{"summary": "Plain fence", "steps": ["P1"]}\n```'
    mock_ai.ask.return_value = wrapped

    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Any text"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["summary"] == "Plain fence"


def test_process_analyst_ai_exception_fallback(lifecycle_client):
    """When AI raises an exception the endpoint returns a fallback response (200)."""
    client, mock_ai = lifecycle_client
    mock_ai.ask.side_effect = Exception("AI unavailable")

    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "Some text"},
        content_type="application/json",
    )
    # The route catches all exceptions and returns a fallback dict — no 500
    assert resp.status_code == 200
    data = resp.get_json()
    assert "summary" in data
    assert "steps" in data
    # Fallback summary indicates an error occurred
    assert "Hata" in data["summary"] or len(data["steps"]) > 0


def test_process_analyst_invalid_json_from_ai_fallback(lifecycle_client):
    """When AI returns invalid JSON the route falls back gracefully."""
    client, mock_ai = lifecycle_client
    mock_ai.ask.return_value = "This is NOT json at all"

    resp = client.post(
        "/api/lifecycle/process-analyst",
        json={"text": "trigger invalid"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "summary" in data
    assert "steps" in data


# ── POST /api/lifecycle/save ──────────────────────────────────────────────────

def test_save_flow_returns_200(lifecycle_client):
    """POST /api/lifecycle/save returns 200."""
    client, _ = lifecycle_client
    resp = client.post("/api/lifecycle/save", json={}, content_type="application/json")
    assert resp.status_code == 200


def test_save_flow_returns_status_ok(lifecycle_client):
    """POST /api/lifecycle/save returns status=ok."""
    client, _ = lifecycle_client
    data = client.post("/api/lifecycle/save", json={}, content_type="application/json").get_json()
    assert data["status"] == "ok"


def test_save_flow_returns_message(lifecycle_client):
    """POST /api/lifecycle/save response includes a message field."""
    client, _ = lifecycle_client
    data = client.post("/api/lifecycle/save", json={}, content_type="application/json").get_json()
    assert "message" in data


def test_save_flow_no_body_still_200(lifecycle_client):
    """POST /api/lifecycle/save with no body returns 200."""
    client, _ = lifecycle_client
    resp = client.post("/api/lifecycle/save")
    assert resp.status_code == 200
