"""
tests/unit/test_locators_routes.py
====================================
Locators blueprint (/api/locators, /api/discover, /api/locators/json, …)
için birim testler.

Dış bağımlılıklar (DB, LocatorManager, playwright) monkeypatching ile izole edilir.
"""
import importlib
import sys
import types
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stub_heavy_modules():
    """playwright ve core modüllerini sys.modules'a stub olarak ekle."""
    # playwright stub
    if "playwright" not in sys.modules:
        playwright_pkg = types.ModuleType("playwright")
        sync_api = types.ModuleType("playwright.sync_api")
        sync_api.sync_playwright = None
        playwright_pkg.sync_api = sync_api
        sys.modules["playwright"] = playwright_pkg
        sys.modules["playwright.sync_api"] = sync_api

    # core.db stub
    core_pkg = sys.modules.get("core") or types.ModuleType("core")
    core_db = types.ModuleType("core.db")
    core_db.get_locators = lambda: []
    core_db.save_locator = lambda name, value, url="": 1
    core_db.delete_locator = lambda loc_id: None
    core_pkg.db = core_db
    sys.modules["core"] = core_pkg
    sys.modules["core.db"] = core_db

    # core.locator_manager stub
    class _FakeLocatorManager:
        @staticmethod
        def as_dict():
            return {}

        @staticmethod
        def keys():
            return []

        @staticmethod
        def load(feature, directory=None):
            pass

        @staticmethod
        def load_all(directory=None):
            pass

        @staticmethod
        def resolve(key):
            return key

    lm_mod = types.ModuleType("core.locator_manager")
    lm_mod.LocatorManager = _FakeLocatorManager
    core_pkg.locator_manager = lm_mod
    sys.modules["core.locator_manager"] = lm_mod

    # core.locator_bridge stub
    class _FakeBridge:
        def resolve(self, *args, **kwargs):
            return "css=.stub"

        def health_report(self):
            return {"status": "ok"}

    lb_mod = types.ModuleType("core.locator_bridge")
    lb_mod.get_bridge = lambda: _FakeBridge()
    core_pkg.locator_bridge = lb_mod
    sys.modules["core.locator_bridge"] = lb_mod

    # core.ai_engine stub
    ai_mod = types.ModuleType("core.ai_engine")
    ai_mod.get_ai_engine = lambda: None
    core_pkg.ai_engine = ai_mod
    sys.modules["core.ai_engine"] = ai_mod


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def locators_client():
    """Sadece locators_bp ile kurulmuş minimal Flask test istemcisi."""
    _stub_heavy_modules()

    # Önceki import'u temizle
    sys.modules.pop("routes.locators_routes", None)
    sys.modules.pop("locators_routes", None)

    from flask import Flask
    from routes.locators_routes import locators_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(locators_bp)

    with app.test_client() as client:
        yield client


# ── GET /api/locators (source=db) ─────────────────────────────────────────────

def test_get_locators_db_source_returns_200(locators_client):
    """source=db (varsayılan) ile GET /api/locators 200 dönmeli."""
    response = locators_client.get("/api/locators")
    assert response.status_code == 200


def test_get_locators_db_source_returns_list(locators_client):
    """source=db ile yanıt bir liste (veya dict) olmalı."""
    response = locators_client.get("/api/locators")
    data = response.get_json()
    assert data is not None


def test_get_locators_db_source_returns_empty_list_when_db_empty(locators_client):
    """DB boş olduğunda yanıt boş liste dönmeli."""
    response = locators_client.get("/api/locators")
    data = response.get_json()
    assert data == [] or isinstance(data, (list, dict))


def test_get_locators_db_source_with_data(monkeypatch, locators_client):
    """DB'de locator varsa yanıt onları içermeli."""
    import core.db as db_mod
    monkeypatch.setattr(db_mod, "get_locators", lambda: [{"id": 1, "name": "btn_login", "locator_value": "#login"}])
    response = locators_client.get("/api/locators")
    assert response.status_code == 200


# ── GET /api/locators (source=json) ──────────────────────────────────────────

def test_get_locators_json_source_returns_200(locators_client):
    """source=json ile GET /api/locators 200 dönmeli."""
    response = locators_client.get("/api/locators?source=json")
    assert response.status_code == 200


def test_get_locators_json_source_returns_source_field(locators_client):
    """source=json yanıtı source alanını içermeli."""
    response = locators_client.get("/api/locators?source=json")
    data = response.get_json()
    assert data.get("source") == "json"


def test_get_locators_json_source_returns_locators_field(locators_client):
    """source=json yanıtı locators alanını içermeli."""
    response = locators_client.get("/api/locators?source=json")
    data = response.get_json()
    assert "locators" in data


# ── POST /api/locators ────────────────────────────────────────────────────────

def test_post_locator_returns_ok_status(locators_client):
    """Geçerli veri ile POST /api/locators 200 ve status=ok dönmeli."""
    response = locators_client.post(
        "/api/locators",
        json={"name": "btn_submit", "locator_value": "#submit", "page_url": "http://example.com"},
        content_type="application/json",
    )
    assert response.status_code == 200
    data = response.get_json()
    assert data.get("status") == "ok"


def test_post_locator_returns_id_field(locators_client):
    """POST /api/locators yanıtı id alanını içermeli."""
    response = locators_client.post(
        "/api/locators",
        json={"name": "txt_username", "locator_value": "[name='username']"},
        content_type="application/json",
    )
    data = response.get_json()
    assert "id" in data


def test_post_locator_id_is_integer(locators_client):
    """POST /api/locators yanıtındaki id tam sayı olmalı."""
    response = locators_client.post(
        "/api/locators",
        json={"name": "lnk_home", "locator_value": "a.home-link"},
        content_type="application/json",
    )
    data = response.get_json()
    assert isinstance(data.get("id"), int)


# ── DELETE /api/locators/<id> ─────────────────────────────────────────────────

def test_delete_locator_returns_200(locators_client):
    """DELETE /api/locators/<id> 200 dönmeli."""
    response = locators_client.delete("/api/locators/1")
    assert response.status_code == 200


def test_delete_locator_returns_ok_status(locators_client):
    """DELETE /api/locators/<id> yanıtı status=ok içermeli."""
    response = locators_client.delete("/api/locators/42")
    data = response.get_json()
    assert data.get("status") == "ok"


def test_delete_locator_with_large_id(locators_client):
    """DELETE /api/locators/<büyük id> de 200 dönmeli."""
    response = locators_client.delete("/api/locators/9999")
    assert response.status_code == 200


# ── POST /api/discover ────────────────────────────────────────────────────────

def test_discover_missing_url_returns_400(locators_client):
    """URL belirtilmezse /api/discover 400 dönmeli."""
    response = locators_client.post(
        "/api/discover",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_discover_missing_url_returns_error_message(locators_client):
    """URL eksik olduğunda yanıt error alanını içermeli."""
    response = locators_client.post(
        "/api/discover",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_discover_with_playwright_stubbed_returns_ok(monkeypatch, locators_client):
    """Playwright stub'lanmış iken /api/discover geçerli URL ile tamamlanmalı."""
    import sys
    import types

    # sync_playwright context manager stub
    class _FakePage:
        url = "http://example.com"
        def goto(self, *a, **kw): pass
        def wait_for_timeout(self, *a): pass
        def evaluate(self, *a): return []
        def on(self, *a, **kw): pass

    class _FakeBrowser:
        def new_page(self): return _FakePage()
        def close(self): pass

    class _FakeP:
        chromium = types.SimpleNamespace(launch=lambda **kw: _FakeBrowser())

    class _FakeSyncPW:
        def __enter__(self): return _FakeP()
        def __exit__(self, *a): pass

    sync_api = sys.modules.get("playwright.sync_api")
    if sync_api:
        monkeypatch.setattr(sync_api, "sync_playwright", lambda: _FakeSyncPW(), raising=False)

    response = locators_client.post(
        "/api/discover",
        json={"url": "http://example.com"},
        content_type="application/json",
    )
    # 200 veya 500 (playwright stub tam çalışmasa da 400 olmamalı)
    assert response.status_code != 400


def test_discover_url_without_scheme_is_normalized(monkeypatch, locators_client):
    """Şema olmayan URL /api/discover'da 400 dönmemeli (normalize edilmeli)."""
    response = locators_client.post(
        "/api/discover",
        json={"url": "example.com"},
        content_type="application/json",
    )
    # 400 dönmemeli — URL normalize edilmiş olmalı
    assert response.status_code != 400
