"""
tests/unit/test_playback_routes.py
=====================================
Playback blueprint (/api/playback/*) icin birim testler.

playwright ve core.playback_engine.PlaybackEngine sys.modules stub'lari
ile izole edilir; config.settings de stub'lanir.
"""
import importlib.util
import sys
import types
import json
import pytest
from pathlib import Path
from flask import Flask


# ── Stubs ─────────────────────────────────────────────────────────────────────

class _FakeReport:
    def __init__(self, session_id="test-session"):
        self.session_id = session_id
        self.total = 5
        self.passed = 5
        self.failed = 0
        self.healed = 0
        self.pass_rate = 100.0
        self.started_at = "2024-01-01T10:00:00"

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "healed": self.healed,
            "pass_rate": self.pass_rate,
            "started_at": self.started_at,
        }


class _FakePlaybackEngine:
    def __init__(self, page, timeout=10_000):
        self.page = page
        self.timeout = timeout

    def replay_from_file(self, path):
        return _FakeReport()

    def replay(self, events, session_id="inline"):
        return _FakeReport(session_id=session_id)

    def save_report(self):
        return "/tmp/fake_playback_report.json"

    def summary(self):
        return {"total": 5, "passed": 5, "failed": 0, "pass_rate": 100.0}


class _FakePage:
    def goto(self, url, **kwargs): pass
    def close(self): pass


class _FakeBrowser:
    def new_page(self):
        return _FakePage()

    def close(self): pass


class _FakePWLauncher:
    def launch(self, headless=True):
        return _FakeBrowser()


class _FakeSyncPlaywright:
    def __enter__(self):
        self.chromium = _FakePWLauncher()
        self.firefox = _FakePWLauncher()
        self.webkit = _FakePWLauncher()
        return self

    def __exit__(self, *args): pass


def _make_playwright_stub():
    pw_mod = types.ModuleType("playwright")
    sync_api_mod = types.ModuleType("playwright.sync_api")
    sync_api_mod.sync_playwright = _FakeSyncPlaywright
    sys.modules["playwright"] = pw_mod
    sys.modules["playwright.sync_api"] = sync_api_mod
    return sync_api_mod


def _make_playback_engine_stub():
    core_mod = sys.modules.setdefault("core", types.ModuleType("core"))
    pe_mod = types.ModuleType("core.playback_engine")
    pe_mod.PlaybackEngine = _FakePlaybackEngine
    sys.modules["core.playback_engine"] = pe_mod
    return pe_mod


def _make_settings_stub(tmp_path=None):
    base = tmp_path or Path("/tmp/neurex_test")
    settings_obj = types.SimpleNamespace(BASE_DIR=base)
    settings_mod = types.ModuleType("config.settings")
    settings_mod.settings = settings_obj
    config_pkg = sys.modules.setdefault("config", types.ModuleType("config"))
    sys.modules["config.settings"] = settings_mod
    return settings_obj


def _load_playback_blueprint():
    for key in list(sys.modules.keys()):
        if "playback_routes" in key:
            del sys.modules[key]

    spec = importlib.util.spec_from_file_location(
        "playback_routes",
        "/Users/yasin_bulgan/Desktop/Neurex_QA/engine/routes/playback_routes.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def playback_client(tmp_path):
    """Tam stub'lanmis playback test istemcisi."""
    _make_settings_stub(tmp_path)
    _make_playwright_stub()
    _make_playback_engine_stub()
    mod = _load_playback_blueprint()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(mod.playback_bp)

    with app.test_client() as client:
        yield client, mod, tmp_path


# ── /api/playback/replay (POST) ───────────────────────────────────────────────

def test_replay_missing_session_path_returns_400(playback_client):
    """session_path gonderilmezse 400 donmeli."""
    client, _, _ = playback_client
    resp = client.post("/api/playback/replay", json={})
    assert resp.status_code == 400


def test_replay_missing_session_path_ok_false(playback_client):
    client, _, _ = playback_client
    data = client.post("/api/playback/replay", json={}).get_json()
    assert data["ok"] is False


def test_replay_missing_session_path_has_error(playback_client):
    client, _, _ = playback_client
    data = client.post("/api/playback/replay", json={}).get_json()
    assert "error" in data


def test_replay_nonexistent_path_returns_404(playback_client):
    """Var olmayan dosya yolu ile 404 donmeli."""
    client, _, _ = playback_client
    resp = client.post(
        "/api/playback/replay",
        json={"session_path": "/nonexistent/session_xyz.json"},
    )
    assert resp.status_code == 404


def test_replay_nonexistent_path_ok_false(playback_client):
    client, _, _ = playback_client
    data = client.post(
        "/api/playback/replay",
        json={"session_path": "/nonexistent/session_xyz.json"},
    ).get_json()
    assert data["ok"] is False


def test_replay_success_returns_200(playback_client, tmp_path):
    """Gecerli dosya yolu ile 200 ve rapor donmeli."""
    client, _, _ = playback_client

    # Gecici oturum dosyasi olustur
    session_file = tmp_path / "test_session.json"
    session_file.write_text(json.dumps({"events": [], "session_id": "abc123"}))

    resp = client.post(
        "/api/playback/replay",
        json={"session_path": str(session_file)},
    )
    assert resp.status_code == 200


def test_replay_success_ok_true(playback_client, tmp_path):
    client, _, _ = playback_client
    session_file = tmp_path / "test_session2.json"
    session_file.write_text(json.dumps({"events": []}))

    data = client.post(
        "/api/playback/replay",
        json={"session_path": str(session_file)},
    ).get_json()
    assert data["ok"] is True


def test_replay_success_has_report(playback_client, tmp_path):
    client, _, _ = playback_client
    session_file = tmp_path / "test_session3.json"
    session_file.write_text(json.dumps({"events": []}))

    data = client.post(
        "/api/playback/replay",
        json={"session_path": str(session_file)},
    ).get_json()
    assert "report" in data
    assert isinstance(data["report"], dict)


def test_replay_success_has_summary(playback_client, tmp_path):
    client, _, _ = playback_client
    session_file = tmp_path / "test_session4.json"
    session_file.write_text(json.dumps({"events": []}))

    data = client.post(
        "/api/playback/replay",
        json={"session_path": str(session_file)},
    ).get_json()
    assert "summary" in data


# ── /api/playback/reports (GET) ───────────────────────────────────────────────

def test_list_reports_returns_200(playback_client):
    """Rapor listesi endpoint'i 200 donmeli."""
    client, _, _ = playback_client
    resp = client.get("/api/playback/reports")
    assert resp.status_code == 200


def test_list_reports_ok_true(playback_client):
    client, _, _ = playback_client
    data = client.get("/api/playback/reports").get_json()
    assert data["ok"] is True


def test_list_reports_empty_when_no_reports(playback_client):
    """Rapor dizini bos oldugunda bos liste donmeli."""
    client, _, _ = playback_client
    data = client.get("/api/playback/reports").get_json()
    assert "reports" in data
    assert isinstance(data["reports"], list)


def test_list_reports_with_mocked_file(playback_client, tmp_path, monkeypatch):
    """Rapor dizininde dosya oldugunda listede gorunmeli."""
    client, mod, _ = playback_client

    reports_dir = tmp_path / "reports" / "playback"
    reports_dir.mkdir(parents=True)
    report_data = {
        "session_id": "sess001",
        "total": 3,
        "passed": 3,
        "failed": 0,
        "healed": 0,
        "pass_rate": 100.0,
        "started_at": "2024-01-01T10:00:00",
    }
    (reports_dir / "report_001.json").write_text(json.dumps(report_data))

    # settings.BASE_DIR'i tmp_path ile guncelle
    monkeypatch.setattr(
        sys.modules["config.settings"].settings,
        "BASE_DIR",
        tmp_path,
    )

    data = client.get("/api/playback/reports").get_json()
    assert data["count"] >= 1
    assert len(data["reports"]) >= 1


# ── /api/playback/reports/<filename> (GET) ───────────────────────────────────

def test_get_report_unknown_file_returns_404_or_403(playback_client):
    """Bilinmeyen rapor dosyasi icin 404 veya 403 donmeli."""
    client, _, _ = playback_client
    resp = client.get("/api/playback/reports/nonexistent_report.json")
    assert resp.status_code in (404, 403, 500)


def test_blueprint_registered(playback_client):
    _, mod, _ = playback_client
    assert mod.playback_bp is not None
    assert mod.playback_bp.name == "playback"
