"""
tests/unit/test_auth_security.py
===================================
Auth blueprint güvenlik testleri.

Gerçek kimlik doğrulama akışı test edilmez; yalnızca:
  - endpoint'lerin varlığı
  - yanlış / eksik kimlik bilgileriyle hata kodları
  - oturum açılmadan korunan endpoint'lere erişim reddi
"""
import importlib
import sys
import pytest


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch):
    """Kimlik doğrulama DB çağrıları stub'lanmış test istemcisi."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    # DB stub'ları — gerçek DB bağlantısı kurulmadan davranışları simüle et
    monkeypatch.setattr(
        "core.db.get_platform_user_by_email",
        lambda email: None,
        raising=False,
    )
    monkeypatch.setattr(
        "core.db.create_platform_user",
        lambda email, pw, token: {"success": False, "error": "stub"},
        raising=False,
    )
    monkeypatch.setattr(
        "core.db.verify_platform_user",
        lambda token: False,
        raising=False,
    )

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


# ── /api/auth/login ───────────────────────────────────────────────────────────

def test_login_endpoint_exists(engine_client):
    """/api/auth/login endpoint'i var olmalı (405 değil, 401 veya 400 dönmeli)."""
    response = engine_client.post(
        "/api/auth/login",
        json={"email": "x@x.com", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code not in {404, 405}


def test_login_rejects_unknown_user(engine_client):
    """Bilinmeyen kullanıcıyla giriş 401 dönmeli."""
    response = engine_client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "secret"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_login_with_empty_body_returns_error(engine_client):
    """Boş body ile /api/auth/login 401 dönmeli (kullanıcı bulunamaz)."""
    response = engine_client.post(
        "/api/auth/login",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_login_returns_json_error(engine_client):
    """Hatalı giriş denemesi JSON hata mesajı dönmeli."""
    response = engine_client.post(
        "/api/auth/login",
        json={"email": "bad@example.com", "password": "wrong"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data is not None
    assert "error" in data


# ── /api/auth/register ────────────────────────────────────────────────────────

def test_register_missing_email_returns_400(engine_client):
    """E-posta eksik olduğunda kayıt 400 dönmeli."""
    response = engine_client.post(
        "/api/auth/register",
        json={"password": "pass123"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_register_missing_password_returns_400(engine_client):
    """Şifre eksik olduğunda kayıt 400 dönmeli."""
    response = engine_client.post(
        "/api/auth/register",
        json={"email": "user@example.com"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_register_empty_body_returns_400(engine_client):
    """Boş body ile kayıt 400 dönmeli."""
    response = engine_client.post(
        "/api/auth/register",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


# ── /api/auth/logout ──────────────────────────────────────────────────────────

def test_logout_accessible_without_session(engine_client):
    """Logout endpoint'i oturum açık olmadan da çağrılabilmeli (401 değil)."""
    response = engine_client.post("/api/auth/logout")
    # Logout public endpoint'tir; 200 veya 302 beklenir, 401 beklenmez
    assert response.status_code not in {401, 404}


def test_logout_returns_success(engine_client):
    """Logout JSON {success: true} dönmeli."""
    response = engine_client.post("/api/auth/logout")
    data = response.get_json()
    assert data is not None
    assert data.get("success") is True
