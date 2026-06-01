"""
tests/unit/test_project_routes.py
====================================
Project blueprint (/api/projects, /api/projects/<id>, /api/projects/set-active, …)
için birim testler.

Dış bağımlılıklar (DB, config.settings, scripts.scaffold_project) monkeypatching
ile izole edilir.
"""
import importlib
import sys
import types
import pytest
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stub_project_deps(tmp_path=None):
    """project_routes için gerekli stub modülleri oluşturur."""
    # config.settings stub
    cfg_pkg = sys.modules.get("config") or types.ModuleType("config")
    settings_mod = types.ModuleType("config.settings")

    class _FakeSettings:
        BASE_DIR = Path(tmp_path) if tmp_path else Path("/tmp/neurex_test")

        def __getattr__(self, name):
            return None

    settings_mod.settings = _FakeSettings()
    cfg_pkg.settings = settings_mod
    sys.modules["config"] = cfg_pkg
    sys.modules["config.settings"] = settings_mod

    # scripts.scaffold_project stub
    scripts_pkg = sys.modules.get("scripts") or types.ModuleType("scripts")
    scaffold_mod = types.ModuleType("scripts.scaffold_project")

    class _FakeScaffolder:
        def __init__(self, *a, **kw): pass
        def create(self): pass

    scaffold_mod.ProjectScaffolder = _FakeScaffolder
    scripts_pkg.scaffold_project = scaffold_mod
    sys.modules["scripts"] = scripts_pkg
    sys.modules["scripts.scaffold_project"] = scaffold_mod

    # core.db stub
    core_pkg = sys.modules.get("core") or types.ModuleType("core")
    core_db = types.ModuleType("core.db")
    core_db.create_project = lambda name, description="": 1
    core_db.get_projects = lambda: []
    core_db.get_project = lambda project_id: None
    # Diğer olası importlar
    core_db.get_locators = lambda: []
    core_db.save_locator = lambda *a, **kw: 1
    core_db.delete_locator = lambda *a: None
    core_pkg.db = core_db
    sys.modules["core"] = core_pkg
    sys.modules["core.db"] = core_db


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def project_client(tmp_path):
    """Sadece project_bp ile kurulmuş minimal Flask test istemcisi."""
    _stub_project_deps(tmp_path)

    sys.modules.pop("routes.project_routes", None)
    sys.modules.pop("project_routes", None)

    from flask import Flask
    from routes.project_routes import project_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(project_bp)

    with app.test_client() as client:
        yield client


# ── GET /api/projects ─────────────────────────────────────────────────────────

def test_list_projects_returns_200(project_client):
    """GET /api/projects 200 dönmeli."""
    response = project_client.get("/api/projects")
    assert response.status_code == 200


def test_list_projects_returns_json(project_client):
    """GET /api/projects JSON yanıt dönmeli."""
    response = project_client.get("/api/projects")
    data = response.get_json()
    assert data is not None


def test_list_projects_empty_db_returns_empty_list(project_client):
    """DB boş iken /api/projects boş projects listesi dönmeli."""
    response = project_client.get("/api/projects")
    data = response.get_json()
    assert data.get("projects") == []


def test_list_projects_returns_total_field(project_client):
    """GET /api/projects yanıtı total alanını içermeli."""
    response = project_client.get("/api/projects")
    data = response.get_json()
    assert "total" in data


def test_list_projects_with_data_returns_populated_list(monkeypatch, project_client):
    """DB'de proje varken /api/projects onları içermeli."""
    import routes.project_routes as routes_mod

    class _FakeRow(dict):
        pass

    rows = [_FakeRow({"id": 1, "name": "my_project", "description": "", "created_at": "2024-01-01"})]
    monkeypatch.setattr(routes_mod, "db_get_projects", lambda: rows)

    response = project_client.get("/api/projects")
    data = response.get_json()
    assert data.get("total") == 1
    assert len(data.get("projects", [])) == 1


def test_list_projects_project_has_expected_fields(monkeypatch, project_client):
    """Proje listesindeki her kayıt id ve name içermeli."""
    import routes.project_routes as routes_mod

    class _FakeRow(dict):
        pass

    rows = [_FakeRow({"id": 2, "name": "alpha", "description": "desc", "created_at": "2024-02-01"})]
    monkeypatch.setattr(routes_mod, "db_get_projects", lambda: rows)

    response = project_client.get("/api/projects")
    data = response.get_json()
    project = data["projects"][0]
    assert "id" in project
    assert "name" in project


# ── POST /api/projects ────────────────────────────────────────────────────────

def test_create_project_missing_name_returns_400(project_client):
    """name eksik olduğunda POST /api/projects 400 dönmeli."""
    response = project_client.post(
        "/api/projects",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_create_project_empty_name_returns_400(project_client):
    """Boş name ile POST /api/projects 400 dönmeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": ""},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_create_project_whitespace_name_returns_400(project_client):
    """Sadece boşluk olan name ile POST /api/projects 400 dönmeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": "   "},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_create_project_missing_name_returns_error_field(project_client):
    """400 yanıtı error alanını içermeli."""
    response = project_client.post(
        "/api/projects",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_create_project_success_returns_201(project_client):
    """Geçerli name ile POST /api/projects 201 dönmeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": "new_project"},
        content_type="application/json",
    )
    assert response.status_code == 201


def test_create_project_success_returns_ok_true(project_client):
    """Başarılı proje oluşturma ok=True içermeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": "another_project"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data.get("ok") is True


def test_create_project_success_returns_id(project_client):
    """Başarılı proje oluşturma id alanı içermeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": "project_with_id"},
        content_type="application/json",
    )
    data = response.get_json()
    assert "id" in data


def test_create_project_success_returns_name(project_client):
    """Başarılı yanıt name alanını içermeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": "named_project"},
        content_type="application/json",
    )
    data = response.get_json()
    assert data.get("name") == "named_project"


def test_create_project_with_description_succeeds(project_client):
    """name ve description ile POST /api/projects 201 dönmeli."""
    response = project_client.post(
        "/api/projects",
        json={"name": "full_project", "description": "Test açıklaması"},
        content_type="application/json",
    )
    assert response.status_code == 201


# ── GET /api/projects/<id> ────────────────────────────────────────────────────

def test_get_project_not_found_returns_404(project_client):
    """Olmayan proje id ile GET /api/projects/<id> 404 dönmeli."""
    response = project_client.get("/api/projects/9999")
    assert response.status_code == 404


def test_get_project_not_found_returns_error_field(project_client):
    """404 yanıtı error alanını içermeli."""
    response = project_client.get("/api/projects/9999")
    data = response.get_json()
    assert "error" in data


def test_get_project_found_returns_200(monkeypatch, project_client):
    """Mevcut proje id ile GET /api/projects/<id> 200 dönmeli."""
    import routes.project_routes as routes_mod

    class _FakeRow(dict):
        pass

    row = _FakeRow({"id": 5, "name": "found_project", "description": "", "created_at": "2024-03-01"})
    monkeypatch.setattr(routes_mod, "db_get_project", lambda pid: row)

    response = project_client.get("/api/projects/5")
    assert response.status_code == 200


def test_get_project_found_returns_correct_data(monkeypatch, project_client):
    """Proje verisi yanıtta doğru dönmeli."""
    import routes.project_routes as routes_mod

    class _FakeRow(dict):
        pass

    row = _FakeRow({"id": 7, "name": "test_project", "description": "desc", "created_at": "2024-04-01"})
    monkeypatch.setattr(routes_mod, "db_get_project", lambda pid: row)

    response = project_client.get("/api/projects/7")
    data = response.get_json()
    assert data.get("name") == "test_project"
    assert data.get("id") == 7
