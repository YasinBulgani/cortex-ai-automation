"""
ai_generation_routes blueprint testleri — 17 test.

Kapsanan endpoint'ler:
  POST /api/ai/generate-test
  POST /api/ai/generate-bdd
"""
from __future__ import annotations

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
    svc.get_llm_gateway = MagicMock(return_value=gateway)

    # ---- services.ai_test_generator ----
    gen_mod = types.ModuleType("services.ai_test_generator")
    gen_obj = MagicMock()
    gen_result = MagicMock()
    gen_result.framework = "pytest-bdd"
    gen_result.code = "def test_login(): pass"
    gen_result.file_path = "tests/test_login.py"
    gen_result.validation_passed = True
    gen_result.validation_errors = []
    gen_obj.generate_from_requirement = MagicMock(return_value=gen_result)
    gen_mod.AITestGenerator = MagicMock(return_value=gen_obj)

    # ---- services.bdd_generator ----
    bdd_mod = types.ModuleType("services.bdd_generator")
    bdd_obj = MagicMock()
    bdd_result = MagicMock()
    bdd_result.feature_content = "Feature: Login\n  Scenario: Valid login"
    bdd_result.step_definitions = ["@given('the user is on the login page')"]
    bdd_result.matched_existing_steps = []
    bdd_result.new_steps_needed = ["@then('the user is logged in')"]
    bdd_obj.generate = MagicMock(return_value=bdd_result)
    bdd_mod.BDDGenerator = MagicMock(return_value=bdd_obj)

    return {
        "services": svc,
        "services.ai_test_generator": gen_mod,
        "services.bdd_generator": bdd_mod,
    }


def _install_stubs(stubs: dict):
    for name, mod in stubs.items():
        sys.modules[name] = mod


def _remove_stubs(stubs: dict):
    for name in stubs:
        sys.modules.pop(name, None)
    sys.modules.pop("routes.ai_generation_routes", None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(tmp_path):
    """Feature açık, LLM mevcut — happy-path istemci."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_generation_routes import ai_gen_bp
        app = Flask(__name__)
        app.register_blueprint(ai_gen_bp)
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
        from routes.ai_generation_routes import ai_gen_bp
        app = Flask(__name__)
        app.register_blueprint(ai_gen_bp)
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
        from routes.ai_generation_routes import ai_gen_bp
        app = Flask(__name__)
        app.register_blueprint(ai_gen_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


# ---------------------------------------------------------------------------
# /api/ai/generate-test  — POST
# ---------------------------------------------------------------------------

class TestGenerateTest:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/generate-test", json={"requirement": "login test"})
        assert resp.status_code == 503

    def test_feature_disabled_error_in_body(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/generate-test", json={"requirement": "login test"})
        data = resp.get_json()
        assert "error" in data

    def test_llm_unavailable_returns_503(self, client_llm_off):
        resp = client_llm_off.post("/api/ai/generate-test", json={"requirement": "login test"})
        assert resp.status_code == 503

    def test_missing_requirement_returns_400(self, client):
        resp = client.post("/api/ai/generate-test", json={})
        assert resp.status_code == 400

    def test_missing_requirement_error_in_body(self, client):
        resp = client.post("/api/ai/generate-test", json={})
        data = resp.get_json()
        assert "error" in data

    def test_empty_requirement_returns_400(self, client):
        resp = client.post("/api/ai/generate-test", json={"requirement": "   "})
        assert resp.status_code == 400

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/generate-test", json={"requirement": "User can log in with valid credentials"})
        assert resp.status_code == 200

    def test_success_contains_code(self, client):
        resp = client.post("/api/ai/generate-test", json={"requirement": "User can log in"})
        data = resp.get_json()
        assert "code" in data
        assert data["code"] == "def test_login(): pass"

    def test_success_contains_framework(self, client):
        resp = client.post("/api/ai/generate-test", json={"requirement": "User can log in"})
        data = resp.get_json()
        assert "framework" in data
        assert data["framework"] == "pytest-bdd"

    def test_success_contains_validation_passed(self, client):
        resp = client.post("/api/ai/generate-test", json={"requirement": "User can log in"})
        data = resp.get_json()
        assert "validation_passed" in data
        assert data["validation_passed"] is True

    def test_extra_params_framework_passed_through(self, client):
        """framework parametresi generator'a iletilmeli."""
        resp = client.post(
            "/api/ai/generate-test",
            json={"requirement": "User can log in", "framework": "playwright", "language": "typescript"},
        )
        assert resp.status_code == 200
        gen_obj = sys.modules["services.ai_test_generator"].AITestGenerator.return_value
        call_kwargs = gen_obj.generate_from_requirement.call_args
        assert call_kwargs is not None
        assert call_kwargs.kwargs.get("framework") == "playwright" or (
            len(call_kwargs.args) > 1 and "playwright" in call_kwargs.args
        )


# ---------------------------------------------------------------------------
# /api/ai/generate-bdd  — POST
# ---------------------------------------------------------------------------

class TestGenerateBDD:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/generate-bdd", json={"requirement": "login scenario"})
        assert resp.status_code == 503

    def test_llm_unavailable_returns_503(self, client_llm_off):
        resp = client_llm_off.post("/api/ai/generate-bdd", json={"requirement": "login scenario"})
        assert resp.status_code == 503

    def test_missing_requirement_returns_400(self, client):
        resp = client.post("/api/ai/generate-bdd", json={})
        assert resp.status_code == 400

    def test_missing_requirement_error_in_body(self, client):
        resp = client.post("/api/ai/generate-bdd", json={})
        data = resp.get_json()
        assert "error" in data

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/generate-bdd", json={"requirement": "User logs in with valid credentials"})
        assert resp.status_code == 200

    def test_success_contains_feature_content(self, client):
        resp = client.post("/api/ai/generate-bdd", json={"requirement": "User logs in"})
        data = resp.get_json()
        assert "feature_content" in data
        assert "Feature" in data["feature_content"]

    def test_success_contains_step_definitions(self, client):
        resp = client.post("/api/ai/generate-bdd", json={"requirement": "User logs in"})
        data = resp.get_json()
        assert "step_definitions" in data
        assert isinstance(data["step_definitions"], list)

    def test_success_contains_new_steps_needed(self, client):
        resp = client.post("/api/ai/generate-bdd", json={"requirement": "User logs in"})
        data = resp.get_json()
        assert "new_steps_needed" in data

    def test_extra_params_passed_through(self, client):
        """framework ve language parametreleri 200 ile karşılanmalı (bilinmeyen param görmezden gelinmeli)."""
        resp = client.post(
            "/api/ai/generate-bdd",
            json={"requirement": "User logs in", "framework": "cucumber", "language": "java"},
        )
        assert resp.status_code == 200
