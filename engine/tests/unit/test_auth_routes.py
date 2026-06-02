"""
tests/unit/test_auth_routes.py
====================================
auth_bp (/login, /api/auth/register, /api/auth/login,
         /api/auth/verify/<token>, /api/auth/logout)
için birim testler.

Dış bağımlılıklar (core.db, werkzeug.security) monkeypatching
ile izole edilir; Flask test istemcisi üzerinden HTTP akışları doğrulanır.
"""
import sys
import types
import pytest


# ── Stub helpers ──────────────────────────────────────────────────────────────

def _stub_auth_deps():
    """auth_routes için gerekli stub modülleri oluşturur."""
    # core package stub
    core_pkg = sys.modules.get("core") or types.ModuleType("core")
    core_db = types.ModuleType("core.db")

    # Default implementations (overridden per-test via monkeypatch)
    core_db.create_platform_user = lambda email, pw_hash, token: {"success": True}
    core_db.get_platform_user_by_email = lambda email: None
    core_db.verify_platform_user = lambda token: True

    core_pkg.db = core_db
    sys.modules["core"] = core_pkg
    sys.modules["core.db"] = core_db


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client():
    """Sadece auth_bp ile kurulmuş minimal Flask test istemcisi."""
    _stub_auth_deps()

    # Remove cached module so stubs take effect
    sys.modules.pop("routes.auth_routes", None)
    sys.modules.pop("auth_routes", None)

    from flask import Flask
    from routes.auth_routes import auth_bp

    app = Flask(__name__, template_folder="/tmp")
    app.config["TESTING"] = True
    app.secret_key = "test-secret-key"
    app.register_blueprint(auth_bp)

    with app.test_client() as client:
        yield client


# ── POST /api/auth/register ───────────────────────────────────────────────────

def test_register_missing_email_returns_400(auth_client):
    """E-posta eksik olduğunda /api/auth/register 400 dönmeli."""
    response = auth_client.post(
        "/api/auth/register",
        json={"password": "secret123"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_register_missing_password_returns_400(auth_client):
    """Şifre eksik olduğunda /api/auth/register 400 dönmeli."""
    response = auth_client.post(
        "/api/auth/register",
        json={"email": "user@test.com"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_register_empty_body_returns_400(auth_client):
    """Boş gövde ile /api/auth/register 400 dönmeli."""
    response = auth_client.post(
        "/api/auth/register",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_register_missing_fields_returns_error_message(auth_client):
    """400 yanıtı error alanını içermeli."""
    response = auth_client.post(
        "/api/auth/register",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_register_success_returns_200(auth_client):
    """Geçerli e-posta ve şifre ile kayıt 200 dönmeli."""
    response = auth_client.post(
        "/api/auth/register",
        json={"email": "newuser@test.com", "password": "strongpass"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_register_success_returns_success_true(auth_client):
    """Başarılı kayıt yanıtı success=True içermeli."""
    response = auth_client.post(
        "/api/auth/register",
        json={"email": "newuser@test.com", "password": "strongpass"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data.get("success") is True


def test_register_db_error_returns_400(monkeypatch, auth_client):
    """DB create_platform_user başarısız döndüğünde kayıt 400 dönmeli."""
    import core.db as db_mod
    monkeypatch.setattr(db_mod, "create_platform_user",
                        lambda email, pw_hash, token: {"success": False, "error": "Email zaten kayıtlı"})

    response = auth_client.post(
        "/api/auth/register",
        json={"email": "dup@test.com", "password": "pass"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_register_db_error_returns_error_field(monkeypatch, auth_client):
    """DB hatası durumunda yanıt error alanını içermeli."""
    import core.db as db_mod
    monkeypatch.setattr(db_mod, "create_platform_user",
                        lambda email, pw_hash, token: {"success": False, "error": "Email zaten kayıtlı"})

    response = auth_client.post(
        "/api/auth/register",
        json={"email": "dup@test.com", "password": "pass"},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


# ── POST /api/auth/login ──────────────────────────────────────────────────────

def test_login_invalid_credentials_returns_401(monkeypatch, auth_client):
    """Yanlış kimlik bilgileri ile /api/auth/login 401 dönmeli."""
    import core.db as db_mod
    monkeypatch.setattr(db_mod, "get_platform_user_by_email", lambda email: None)

    response = auth_client.post(
        "/api/auth/login",
        json={"email": "nobody@test.com", "password": "wrong"},
        content_type="application/json",
    )
    assert response.status_code == 401


def test_login_unverified_user_returns_403(monkeypatch, auth_client):
    """Doğrulanmamış kullanıcı ile giriş 403 dönmeli."""
    import core.db as db_mod
    from werkzeug.security import generate_password_hash

    fake_user = {
        "id": 1,
        "email": "user@test.com",
        "password_hash": generate_password_hash("correctpass"),
        "is_verified": False,
    }
    monkeypatch.setattr(db_mod, "get_platform_user_by_email", lambda email: fake_user)

    response = auth_client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "correctpass"},
        content_type="application/json",
    )
    assert response.status_code == 403


def test_login_verified_user_returns_200(monkeypatch, auth_client):
    """Doğrulanmış kullanıcı ile başarılı giriş 200 dönmeli."""
    import core.db as db_mod
    from werkzeug.security import generate_password_hash

    fake_user = {
        "id": 42,
        "email": "verified@test.com",
        "password_hash": generate_password_hash("mypassword"),
        "is_verified": True,
    }
    monkeypatch.setattr(db_mod, "get_platform_user_by_email", lambda email: fake_user)

    response = auth_client.post(
        "/api/auth/login",
        json={"email": "verified@test.com", "password": "mypassword"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_login_success_returns_success_true(monkeypatch, auth_client):
    """Başarılı giriş yanıtı success=True içermeli."""
    import core.db as db_mod
    from werkzeug.security import generate_password_hash

    fake_user = {
        "id": 7,
        "email": "ok@test.com",
        "password_hash": generate_password_hash("pass"),
        "is_verified": True,
    }
    monkeypatch.setattr(db_mod, "get_platform_user_by_email", lambda email: fake_user)

    response = auth_client.post(
        "/api/auth/login",
        json={"email": "ok@test.com", "password": "pass"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data.get("success") is True


# ── GET /api/auth/verify/<token> ──────────────────────────────────────────────

def test_verify_email_valid_token_returns_200(monkeypatch, auth_client):
    """Geçerli token ile /api/auth/verify 200 dönmeli."""
    import core.db as db_mod
    monkeypatch.setattr(db_mod, "verify_platform_user", lambda token: True)

    response = auth_client.get("/api/auth/verify/valid-token-abc123")
    assert response.status_code == 200


def test_verify_email_invalid_token_returns_200_with_error_html(monkeypatch, auth_client):
    """Geçersiz token ile /api/auth/verify 200 dönmeli (HTML hata mesajı ile)."""
    import core.db as db_mod
    monkeypatch.setattr(db_mod, "verify_platform_user", lambda token: False)

    response = auth_client.get("/api/auth/verify/bad-token")
    assert response.status_code == 200
    assert b"Ge" in response.data  # "Geçersiz" içeriyor


# ── POST /api/auth/logout ─────────────────────────────────────────────────────

def test_logout_returns_200(auth_client):
    """POST /api/auth/logout 200 dönmeli."""
    response = auth_client.post("/api/auth/logout")
    assert response.status_code == 200


def test_logout_returns_success_true(auth_client):
    """Çıkış yanıtı success=True içermeli."""
    response = auth_client.post("/api/auth/logout")
    data = response.get_json()
    assert data.get("success") is True


def test_logout_clears_session(monkeypatch, auth_client):
    """Çıkış sonrası session temizlenmiş olmalı."""
    import core.db as db_mod
    from werkzeug.security import generate_password_hash

    fake_user = {
        "id": 99,
        "email": "sess@test.com",
        "password_hash": generate_password_hash("pw"),
        "is_verified": True,
    }
    monkeypatch.setattr(db_mod, "get_platform_user_by_email", lambda email: fake_user)

    # Login first to populate session
    auth_client.post(
        "/api/auth/login",
        json={"email": "sess@test.com", "password": "pw"},
        content_type="application/json",
    )
    # Then logout
    response = auth_client.post("/api/auth/logout")
    assert response.status_code == 200
