"""
ai_healing_routes blueprint testleri — 16 test.

Kapsanan endpoint'ler:
  POST /api/ai/self-heal
  POST /api/ai/find-element
  GET  /api/ai/healing-log
"""
from __future__ import annotations

import json
import sys
import types
import pytest
from unittest.mock import MagicMock
from flask import Flask


# ---------------------------------------------------------------------------
# sys.modules stubs — blueprint import edilmeden ÖNCE kurulmalı
# ---------------------------------------------------------------------------

def _make_service_stubs(is_feature_enabled_return=True, llm_available=True):
    """services paketi ve alt modülleri için stub'lar üretir."""

    # ---- services (top-level) ----
    svc = types.ModuleType("services")
    svc.is_feature_enabled = MagicMock(return_value=is_feature_enabled_return)
    gateway = MagicMock()
    gateway.available = llm_available
    # find-element'in kullandığı gw.complete(...) dönüş değeri
    complete_resp = MagicMock()
    complete_resp.content = "  [data-testid='login-btn']  "
    complete_resp.model = "gpt-4o-mini"
    complete_resp.cached = False
    gateway.complete = MagicMock(return_value=complete_resp)
    svc.get_llm_gateway = MagicMock(return_value=gateway)

    # ---- services.self_healer ----
    healer_mod = types.ModuleType("services.self_healer")
    healer_obj = MagicMock()
    heal_result = MagicMock()
    heal_result.to_dict = MagicMock(return_value={
        "healed_selector": "[data-testid='submit']",
        "confidence": 0.92,
        "strategy": "data-testid",
    })
    healer_obj.heal = MagicMock(return_value=heal_result)
    healer_mod.SelfHealer = MagicMock(return_value=healer_obj)

    return {
        "services": svc,
        "services.self_healer": healer_mod,
    }


def _install_stubs(stubs: dict):
    for name, mod in stubs.items():
        sys.modules[name] = mod


def _remove_stubs(stubs: dict):
    for name in stubs:
        sys.modules.pop(name, None)
    sys.modules.pop("routes.ai_healing_routes", None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """Feature açık, LLM mevcut — happy-path istemci."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_healing_routes import ai_healing_bp
        app = Flask(__name__)
        app.register_blueprint(ai_healing_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


@pytest.fixture()
def client_feature_off(tmp_path):
    """Feature devre dışı — 503 beklenir."""
    stubs = _make_service_stubs(is_feature_enabled_return=False, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_healing_routes import ai_healing_bp
        app = Flask(__name__)
        app.register_blueprint(ai_healing_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


@pytest.fixture()
def client_llm_off(tmp_path):
    """Feature açık, LLM mevcut değil."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=False)
    _install_stubs(stubs)
    try:
        from routes.ai_healing_routes import ai_healing_bp
        app = Flask(__name__)
        app.register_blueprint(ai_healing_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


@pytest.fixture()
def client_with_log(tmp_path, monkeypatch):
    """Healing log dosyası mevcut olan istemci."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_healing_routes import ai_healing_bp
        import routes.ai_healing_routes as healing_mod

        log_file = tmp_path / "healing-log.json"
        sample_entries = [
            {"failed_locator": "#old-btn", "healed_selector": "[data-testid='new-btn']", "confidence": 0.9},
            {"failed_locator": ".broken", "healed_selector": "[aria-label='Submit']", "confidence": 0.85},
        ]
        log_file.write_text(json.dumps(sample_entries))
        monkeypatch.setattr(healing_mod, "_HEALING_LOG", log_file)

        app = Flask(__name__)
        app.register_blueprint(ai_healing_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


@pytest.fixture()
def client_no_log(tmp_path, monkeypatch):
    """Healing log dosyası bulunmayan istemci."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_healing_routes import ai_healing_bp
        import routes.ai_healing_routes as healing_mod

        missing_log = tmp_path / "nonexistent-healing-log.json"
        monkeypatch.setattr(healing_mod, "_HEALING_LOG", missing_log)

        app = Flask(__name__)
        app.register_blueprint(ai_healing_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


# ---------------------------------------------------------------------------
# /api/ai/self-heal  — POST
# ---------------------------------------------------------------------------

class TestSelfHeal:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/self-heal", json={"failed_locator": "#btn"})
        assert resp.status_code == 503

    def test_feature_disabled_error_in_body(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/self-heal", json={})
        data = resp.get_json()
        assert "error" in data

    def test_llm_unavailable_returns_503(self, client_llm_off):
        resp = client_llm_off.post("/api/ai/self-heal", json={"failed_locator": "#btn"})
        assert resp.status_code == 503

    def test_missing_failed_locator_returns_400(self, client):
        resp = client.post("/api/ai/self-heal", json={})
        assert resp.status_code == 400

    def test_missing_failed_locator_error_in_body(self, client):
        resp = client.post("/api/ai/self-heal", json={})
        data = resp.get_json()
        assert "error" in data

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/self-heal", json={"failed_locator": "#broken-btn"})
        assert resp.status_code == 200

    def test_success_contains_healed_selector(self, client):
        resp = client.post("/api/ai/self-heal", json={"failed_locator": "#broken-btn"})
        data = resp.get_json()
        assert "healed_selector" in data

    def test_success_healed_selector_value(self, client):
        resp = client.post("/api/ai/self-heal", json={"failed_locator": "#broken-btn"})
        data = resp.get_json()
        assert data["healed_selector"] == "[data-testid='submit']"


# ---------------------------------------------------------------------------
# /api/ai/find-element  — POST
# ---------------------------------------------------------------------------

class TestFindElement:
    def test_llm_unavailable_returns_503(self, client_llm_off):
        resp = client_llm_off.post("/api/ai/find-element", json={"element_intent": "login button"})
        assert resp.status_code == 503

    def test_missing_element_intent_returns_400(self, client):
        resp = client.post("/api/ai/find-element", json={})
        assert resp.status_code == 400

    def test_missing_element_intent_error_in_body(self, client):
        resp = client.post("/api/ai/find-element", json={})
        data = resp.get_json()
        assert "error" in data

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/find-element", json={"element_intent": "login button"})
        assert resp.status_code == 200

    def test_success_contains_locator(self, client):
        resp = client.post("/api/ai/find-element", json={"element_intent": "login button"})
        data = resp.get_json()
        assert "locator" in data


# ---------------------------------------------------------------------------
# /api/ai/healing-log  — GET
# ---------------------------------------------------------------------------

class TestHealingLog:
    def test_no_log_file_returns_200(self, client_no_log):
        resp = client_no_log.get("/api/ai/healing-log")
        assert resp.status_code == 200

    def test_no_log_file_empty_entries(self, client_no_log):
        resp = client_no_log.get("/api/ai/healing-log")
        data = resp.get_json()
        assert data["total"] == 0
        assert data["entries"] == []

    def test_with_log_file_returns_entries(self, client_with_log):
        resp = client_with_log.get("/api/ai/healing-log")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total"] == 2
        assert len(data["entries"]) == 2
