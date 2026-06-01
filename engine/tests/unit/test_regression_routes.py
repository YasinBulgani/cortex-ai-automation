"""
tests/unit/test_regression_routes.py
=======================================
Regression Sets blueprint (/api/regression-sets, …)
için birim testler.

Dış bağımlılıklar (DB) monkeypatching ile izole edilir.
"""
import importlib
import sys
import types
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stub_regression_db():
    """core.db stub'ını regression_routes için hazırla."""
    core_pkg = sys.modules.get("core") or types.ModuleType("core")
    core_db = types.ModuleType("core.db")
    core_db.get_regression_sets = lambda: []
    core_db.create_regression_set = lambda name: True
    core_db.delete_regression_set = lambda set_id: None
    core_db.add_feature_to_set = lambda set_id, feature_name: None
    core_db.remove_feature_from_set = lambda set_id, feature_name: None
    core_pkg.db = core_db
    sys.modules["core"] = core_pkg
    sys.modules["core.db"] = core_db


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def regression_client():
    """Sadece regression_bp ile kurulmuş minimal Flask test istemcisi."""
    _stub_regression_db()

    sys.modules.pop("routes.regression_routes", None)
    sys.modules.pop("regression_routes", None)

    from flask import Flask
    from routes.regression_routes import regression_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(regression_bp)

    with app.test_client() as client:
        yield client


# ── GET /api/regression-sets ──────────────────────────────────────────────────

def test_list_regression_sets_returns_200(regression_client):
    """GET /api/regression-sets 200 dönmeli."""
    response = regression_client.get("/api/regression-sets")
    assert response.status_code == 200


def test_list_regression_sets_returns_json(regression_client):
    """GET /api/regression-sets JSON yanıt dönmeli."""
    response = regression_client.get("/api/regression-sets")
    data = response.get_json()
    assert data is not None


def test_list_regression_sets_empty_returns_empty_list(regression_client):
    """DB boş iken GET /api/regression-sets boş liste dönmeli."""
    response = regression_client.get("/api/regression-sets")
    data = response.get_json()
    assert data == []


def test_list_regression_sets_populated_returns_data(monkeypatch, regression_client):
    """DB'de set varken GET /api/regression-sets onları içermeli."""
    import routes.regression_routes as routes_mod

    sets = [{"id": 1, "name": "Smoke Suite", "features": []},
            {"id": 2, "name": "Full Regression", "features": ["login", "checkout"]}]
    monkeypatch.setattr(routes_mod, "get_regression_sets", lambda: sets)

    response = regression_client.get("/api/regression-sets")
    data = response.get_json()
    assert len(data) == 2


def test_list_regression_sets_populated_contains_names(monkeypatch, regression_client):
    """Listelenen set'ler name alanlarını içermeli."""
    import routes.regression_routes as routes_mod

    sets = [{"id": 1, "name": "Quick Check", "features": []}]
    monkeypatch.setattr(routes_mod, "get_regression_sets", lambda: sets)

    response = regression_client.get("/api/regression-sets")
    data = response.get_json()
    assert data[0]["name"] == "Quick Check"


# ── POST /api/regression-sets ─────────────────────────────────────────────────

def test_create_regression_set_missing_name_returns_400(regression_client):
    """name eksik iken POST /api/regression-sets 400 dönmeli."""
    response = regression_client.post(
        "/api/regression-sets",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_create_regression_set_missing_name_returns_error(regression_client):
    """name eksik yanıtı error alanını içermeli."""
    response = regression_client.post(
        "/api/regression-sets",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_create_regression_set_duplicate_name_returns_400(monkeypatch, regression_client):
    """Aynı isimli set varken POST /api/regression-sets 400 dönmeli."""
    import routes.regression_routes as routes_mod
    monkeypatch.setattr(routes_mod, "create_regression_set", lambda name: False)

    response = regression_client.post(
        "/api/regression-sets",
        json={"name": "Existing Suite"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_create_regression_set_duplicate_name_returns_error_message(monkeypatch, regression_client):
    """Duplicate set yanıtı açıklayıcı hata içermeli."""
    import routes.regression_routes as routes_mod
    monkeypatch.setattr(routes_mod, "create_regression_set", lambda name: False)

    response = regression_client.post(
        "/api/regression-sets",
        json={"name": "Duplicate"},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_create_regression_set_success_returns_200(regression_client):
    """Geçerli name ile POST /api/regression-sets 200 dönmeli."""
    response = regression_client.post(
        "/api/regression-sets",
        json={"name": "New Suite"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_create_regression_set_success_returns_ok_true(regression_client):
    """Başarılı set oluşturma ok=True içermeli."""
    response = regression_client.post(
        "/api/regression-sets",
        json={"name": "Valid Suite"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data.get("ok") is True


# ── DELETE /api/regression-sets/<id> ─────────────────────────────────────────

def test_delete_regression_set_returns_200(regression_client):
    """DELETE /api/regression-sets/<id> 200 dönmeli."""
    response = regression_client.delete("/api/regression-sets/1")
    assert response.status_code == 200


def test_delete_regression_set_returns_ok_true(regression_client):
    """DELETE /api/regression-sets/<id> ok=True içermeli."""
    response = regression_client.delete("/api/regression-sets/5")
    data = response.get_json()
    assert data.get("ok") is True


def test_delete_regression_set_large_id_returns_200(regression_client):
    """Büyük id değeri ile DELETE /api/regression-sets 200 dönmeli."""
    response = regression_client.delete("/api/regression-sets/9999")
    assert response.status_code == 200


# ── POST /api/regression-sets/<id>/features ───────────────────────────────────

def test_add_feature_missing_name_returns_400(regression_client):
    """feature_name eksik iken /api/regression-sets/<id>/features 400 dönmeli."""
    response = regression_client.post(
        "/api/regression-sets/1/features",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_add_feature_missing_name_returns_error_field(regression_client):
    """feature_name eksik yanıtı error alanını içermeli."""
    response = regression_client.post(
        "/api/regression-sets/1/features",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_add_feature_success_returns_200(regression_client):
    """Geçerli feature_name ile /api/regression-sets/<id>/features 200 dönmeli."""
    response = regression_client.post(
        "/api/regression-sets/1/features",
        json={"feature_name": "login"},
        content_type="application/json",
    )
    assert response.status_code == 200


def test_add_feature_success_returns_ok_true(regression_client):
    """Başarılı feature ekleme ok=True içermeli."""
    response = regression_client.post(
        "/api/regression-sets/3/features",
        json={"feature_name": "checkout"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data.get("ok") is True


# ── DELETE /api/regression-sets/<id>/features/<name> ─────────────────────────

def test_remove_feature_returns_200(regression_client):
    """DELETE /api/regression-sets/<id>/features/<name> 200 dönmeli."""
    response = regression_client.delete("/api/regression-sets/1/features/login")
    assert response.status_code == 200


def test_remove_feature_returns_ok_true(regression_client):
    """Feature silme ok=True içermeli."""
    response = regression_client.delete("/api/regression-sets/2/features/checkout")
    data = response.get_json()
    assert data.get("ok") is True


def test_remove_feature_url_encoded_name_returns_200(regression_client):
    """URL encoded feature adı ile silme de 200 dönmeli."""
    response = regression_client.delete("/api/regression-sets/1/features/user_registration")
    assert response.status_code == 200
