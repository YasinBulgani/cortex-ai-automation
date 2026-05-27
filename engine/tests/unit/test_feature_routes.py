"""
feature_bp route testleri.
22 test — tüm endpoint'ler kapsandı.
"""
import importlib
import sys
import types
import json
import pytest
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_settings_stub(tmp_path: Path):
    """Return a minimal settings-like namespace backed by tmp_path."""
    features_dir = tmp_path / "features"
    features_dir.mkdir()
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    steps_dir = tmp_path / "steps"
    steps_dir.mkdir()

    ns = types.SimpleNamespace(
        BASE_DIR=tmp_path,
        FEATURES_DIR=features_dir,
        TESTS_DIR=tests_dir,
        STEPS_DIR=steps_dir,
    )
    return ns


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def feature_client(monkeypatch, tmp_path):
    """Minimal Flask app with only feature_bp; heavy deps are stubbed."""

    # 1. Stub config.settings before the blueprint module is imported
    settings_stub = _make_settings_stub(tmp_path)

    cfg_mod = types.ModuleType("config")
    cfg_mod.settings = settings_stub
    cfg_settings_mod = types.ModuleType("config.settings")
    cfg_settings_mod.settings = settings_stub
    sys.modules.setdefault("config", cfg_mod)
    sys.modules["config.settings"] = cfg_settings_mod

    # 2. Remove cached blueprint module so monkeypatches take effect
    for key in list(sys.modules.keys()):
        if "feature_routes" in key:
            del sys.modules[key]

    # 3. Patch config.settings inside the already-imported module namespace
    import engine.routes.feature_routes as fr_mod  # type: ignore
    monkeypatch.setattr(fr_mod, "settings", settings_stub, raising=True)

    # 4. Build a minimal Flask app
    from flask import Flask
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(fr_mod.feature_bp)

    with app.test_client() as client:
        yield client, settings_stub


# ── GET /api/features ─────────────────────────────────────────────────────────

def test_list_features_empty_dir(feature_client):
    """Empty features dir returns an empty JSON list."""
    client, _ = feature_client
    resp = client.get("/api/features")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_features_with_feature_file(feature_client):
    """A .feature file in features_dir appears in the tree."""
    client, settings = feature_client
    (settings.FEATURES_DIR / "login.feature").write_text(
        "Feature: Login\n  Scenario: valid login\n    Given the app is open",
        encoding="utf-8",
    )
    resp = client.get("/api/features")
    data = resp.get_json()
    assert resp.status_code == 200
    assert len(data) == 1
    assert data[0]["name"] == "login.feature"
    assert data[0]["type"] == "file"


def test_list_features_returns_json_content_type(feature_client):
    client, _ = feature_client
    resp = client.get("/api/features")
    assert "application/json" in resp.content_type


def test_list_features_scenario_count(feature_client):
    """Scenario count is derived from occurrences of 'Scenario' in file text."""
    client, settings = feature_client
    (settings.FEATURES_DIR / "multi.feature").write_text(
        "Feature: Multi\n  Scenario: first\n  Scenario: second\n",
        encoding="utf-8",
    )
    data = client.get("/api/features").get_json()
    assert data[0]["scenarios"] == 2


def test_list_features_subfolder_appears_as_folder(feature_client):
    """Sub-directories show up as type=folder in the tree."""
    client, settings = feature_client
    (settings.FEATURES_DIR / "auth").mkdir()
    data = client.get("/api/features").get_json()
    assert any(item["type"] == "folder" for item in data)


# ── POST /api/features/folder ─────────────────────────────────────────────────

def test_create_folder_success(feature_client):
    """POST /api/features/folder creates a sub-directory."""
    client, settings = feature_client
    resp = client.post(
        "/api/features/folder",
        json={"path": "auth/flows"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert (settings.FEATURES_DIR / "auth" / "flows").is_dir()


def test_create_folder_missing_path_returns_400(feature_client):
    """POST /api/features/folder with no path returns 400."""
    client, _ = feature_client
    resp = client.post("/api/features/folder", json={}, content_type="application/json")
    assert resp.status_code == 400
    assert "error" in resp.get_json()


# ── DELETE /api/features/folder ───────────────────────────────────────────────

def test_delete_folder_success(feature_client):
    """DELETE /api/features/folder removes an existing directory."""
    client, settings = feature_client
    target = settings.FEATURES_DIR / "to_remove"
    target.mkdir()
    resp = client.delete(
        "/api/features/folder",
        json={"path": "to_remove"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert not target.exists()


def test_delete_folder_missing_path_returns_400(feature_client):
    client, _ = feature_client
    resp = client.delete("/api/features/folder", json={}, content_type="application/json")
    assert resp.status_code == 400


# ── GET /api/features/<name> ──────────────────────────────────────────────────

def test_get_feature_not_found(feature_client):
    client, _ = feature_client
    resp = client.get("/api/features/nonexistent.feature")
    assert resp.status_code == 404
    assert "error" in resp.get_json()


def test_get_feature_returns_content(feature_client):
    client, settings = feature_client
    (settings.FEATURES_DIR / "sample.feature").write_text("Feature: Sample", encoding="utf-8")
    resp = client.get("/api/features/sample.feature")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["content"] == "Feature: Sample"
    assert data["name"] == "sample.feature"


# ── PUT /api/features/<name> ──────────────────────────────────────────────────

def test_save_feature_creates_file(feature_client):
    client, settings = feature_client
    resp = client.put(
        "/api/features/new_feature.feature",
        json={"content": "Feature: New"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    saved = settings.FEATURES_DIR / "new_feature.feature"
    assert saved.exists()
    assert saved.read_text(encoding="utf-8") == "Feature: New"


def test_save_feature_creates_glue_file(feature_client):
    """Saving a feature also writes a companion glue test file."""
    client, settings = feature_client
    client.put(
        "/api/features/checkout.feature",
        json={"content": "Feature: Checkout"},
        content_type="application/json",
    )
    glue = settings.TESTS_DIR / "test_checkout.py"
    assert glue.exists()
    assert "scenarios" in glue.read_text(encoding="utf-8")


def test_save_feature_auto_appends_extension(feature_client):
    """If the name lacks .feature, the route appends it."""
    client, settings = feature_client
    client.put(
        "/api/features/no_ext",
        json={"content": "Feature: No ext"},
        content_type="application/json",
    )
    assert (settings.FEATURES_DIR / "no_ext.feature").exists()


def test_save_feature_updates_existing(feature_client):
    """PUT on an existing feature overwrites its content."""
    client, settings = feature_client
    fp = settings.FEATURES_DIR / "existing.feature"
    fp.write_text("old content", encoding="utf-8")
    client.put(
        "/api/features/existing.feature",
        json={"content": "new content"},
        content_type="application/json",
    )
    assert fp.read_text(encoding="utf-8") == "new content"


# ── DELETE /api/features/<name> ───────────────────────────────────────────────

def test_delete_feature_removes_file(feature_client):
    client, settings = feature_client
    fp = settings.FEATURES_DIR / "to_delete.feature"
    fp.write_text("Feature: Del", encoding="utf-8")
    resp = client.delete("/api/features/to_delete.feature")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True
    assert not fp.exists()


def test_delete_feature_also_removes_glue(feature_client):
    """Deleting a feature also removes its companion glue file."""
    client, settings = feature_client
    fp = settings.FEATURES_DIR / "glued.feature"
    fp.write_text("Feature: Glued", encoding="utf-8")
    glue = settings.TESTS_DIR / "test_glued.py"
    glue.write_text("# glue", encoding="utf-8")
    client.delete("/api/features/glued.feature")
    assert not glue.exists()


def test_delete_feature_nonexistent_still_200(feature_client):
    """DELETE on a non-existent feature returns 200 (idempotent)."""
    client, _ = feature_client
    resp = client.delete("/api/features/ghost.feature")
    assert resp.status_code == 200
    assert resp.get_json()["ok"] is True


# ── _build_glue_content helper ────────────────────────────────────────────────

def test_build_glue_content_no_steps(feature_client, monkeypatch):
    """With no step files, glue content still contains scenarios() call."""
    _, settings = feature_client
    import engine.routes.feature_routes as fr_mod  # type: ignore
    content = fr_mod._build_glue_content("login.feature")
    assert "scenarios" in content
    assert "login.feature" in content


def test_build_glue_content_with_step_file(feature_client):
    """With a step file present, glue content includes the import line."""
    _, settings = feature_client
    (settings.STEPS_DIR / "login_steps.py").write_text("# steps", encoding="utf-8")
    import engine.routes.feature_routes as fr_mod  # type: ignore
    content = fr_mod._build_glue_content("login.feature")
    assert "from steps.login_steps import *" in content
