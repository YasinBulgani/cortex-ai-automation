"""
tests/unit/test_monkey_routes.py
==================================
Monkey Testing blueprint (/api/monkey-testing/run, /api/monkey-testing/video, …)
için birim testler.

SSE streaming endpoint'leri yerine non-SSE endpoint'lere odaklanılır.
Playwright ve core.ai_engine ağır bağımlılıkları monkeypatching ile izole edilir.
"""
import importlib
import sys
import types
import pytest


# ── Helpers ───────────────────────────────────────────────────────────────────

def _stub_playwright_and_core():
    """Playwright ve core modüllerini hafif stub'larla değiştirir."""
    # playwright stub
    playwright_pkg = types.ModuleType("playwright")
    sync_api_mod = types.ModuleType("playwright.sync_api")
    sync_api_mod.sync_playwright = None
    playwright_pkg.sync_api = sync_api_mod
    sys.modules["playwright"] = playwright_pkg
    sys.modules["playwright.sync_api"] = sync_api_mod

    # core stub
    core_pkg = sys.modules.get("core") or types.ModuleType("core")

    # core.ai_engine stub
    ai_mod = types.ModuleType("core.ai_engine")
    ai_mod.get_ai_engine = lambda: None
    core_pkg.ai_engine = ai_mod
    sys.modules["core"] = core_pkg
    sys.modules["core.ai_engine"] = ai_mod

    # core.db stub (monkey_routes may import indirectly)
    core_db = types.ModuleType("core.db")
    core_db.get_locators = lambda: []
    core_db.save_locator = lambda *a, **kw: 1
    core_db.delete_locator = lambda *a: None
    core_pkg.db = core_db
    sys.modules["core.db"] = core_db


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def monkey_client():
    """Sadece monkey_bp ile kurulmuş minimal Flask test istemcisi."""
    _stub_playwright_and_core()

    sys.modules.pop("routes.monkey_routes", None)
    sys.modules.pop("monkey_routes", None)

    from flask import Flask
    from routes.monkey_routes import monkey_bp, _VIDEO_STORE

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(monkey_bp)

    with app.test_client() as client:
        yield client


@pytest.fixture
def monkey_client_with_store():
    """Video store erişimi olan monkey_bp test istemcisi."""
    _stub_playwright_and_core()

    sys.modules.pop("routes.monkey_routes", None)
    sys.modules.pop("monkey_routes", None)

    from flask import Flask
    import routes.monkey_routes as monkey_mod

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(monkey_mod.monkey_bp)

    with app.test_client() as client:
        yield client, monkey_mod


# ── POST /api/monkey-testing/run — validation ────────────────────────────────

def test_run_missing_url_returns_400(monkey_client):
    """URL belirtilmezse /api/monkey-testing/run 400 dönmeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_run_missing_url_returns_error_field(monkey_client):
    """URL eksik olduğunda yanıt error alanını içermeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_run_empty_url_string_returns_400(monkey_client):
    """Boş URL string ile /api/monkey-testing/run 400 dönmeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run",
        json={"url": ""},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_run_whitespace_url_returns_400(monkey_client):
    """Sadece boşluk içeren URL ile /api/monkey-testing/run 400 dönmeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run",
        json={"url": "   "},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_run_with_playwright_stubbed_attempts_execution(monkeypatch, monkey_client):
    """Playwright stub'lanmış iken POST /api/monkey-testing/run hata yönetimi yapmalı."""
    import sys
    import types

    class _FakePage:
        url = "http://example.com"
        def goto(self, *a, **kw): pass
        def wait_for_timeout(self, *a): pass
        def evaluate(self, *a): return []
        def on(self, *a, **kw): pass
        def query_selector_all(self, *a): return []

    class _FakeContext:
        def new_page(self): return _FakePage()
        def close(self): pass

    class _FakeBrowser:
        def new_context(self, **kw): return _FakeContext()
        def close(self): pass

    class _FakeP:
        chromium = types.SimpleNamespace(launch=lambda headless=True: _FakeBrowser())

    class _FakeSyncPW:
        def __enter__(self): return _FakeP()
        def __exit__(self, *a): pass

    sync_api = sys.modules.get("playwright.sync_api")
    if sync_api:
        monkeypatch.setattr(sync_api, "sync_playwright", lambda: _FakeSyncPW(), raising=False)

    response = monkey_client.post(
        "/api/monkey-testing/run",
        json={"url": "http://example.com", "max_actions": 1},
        content_type="application/json",
    )
    # URL geçerli, 400 olmamalı
    assert response.status_code != 400


# ── POST /api/monkey-testing/run/stream — validation ─────────────────────────

def test_stream_missing_url_returns_400(monkey_client):
    """URL eksik iken /api/monkey-testing/run/stream 400 dönmeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run/stream",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_stream_missing_url_returns_error_json(monkey_client):
    """URL eksik stream hatası JSON error alanı içermeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run/stream",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_stream_empty_url_returns_400(monkey_client):
    """Boş URL string ile /api/monkey-testing/run/stream 400 dönmeli."""
    response = monkey_client.post(
        "/api/monkey-testing/run/stream",
        json={"url": ""},
        content_type="application/json",
    )
    assert response.status_code == 400


# ── GET /api/monkey-testing/video/<run_id> ───────────────────────────────────

def test_video_unknown_run_id_returns_404(monkey_client):
    """Bilinmeyen run_id ile /api/monkey-testing/video 404 dönmeli."""
    response = monkey_client.get("/api/monkey-testing/video/nonexistent-run-id")
    assert response.status_code == 404


def test_video_unknown_run_id_returns_error_field(monkey_client):
    """Bilinmeyen run_id için yanıt error alanını içermeli."""
    response = monkey_client.get("/api/monkey-testing/video/nonexistent-run-id")
    data = response.get_json()
    assert "error" in data


def test_video_with_missing_file_returns_404(monkey_client_with_store, tmp_path):
    """VIDEO_STORE'da kayıt var ama dosya yoksa 404 dönmeli."""
    client, monkey_mod = monkey_client_with_store
    run_id = "test-run-abc-123"
    monkey_mod._VIDEO_STORE[run_id] = str(tmp_path / "nonexistent.webm")

    response = client.get(f"/api/monkey-testing/video/{run_id}")
    assert response.status_code == 404


def test_video_with_existing_file_returns_200(monkey_client_with_store, tmp_path):
    """VIDEO_STORE'da kayıt var ve dosya mevcutsa 200 dönmeli."""
    client, monkey_mod = monkey_client_with_store
    run_id = "test-run-real-456"
    video_file = tmp_path / "test.webm"
    video_file.write_bytes(b"\x1aE\xdf\xa3")  # WebM magic bytes

    monkey_mod._VIDEO_STORE[run_id] = str(video_file)

    response = client.get(f"/api/monkey-testing/video/{run_id}")
    assert response.status_code == 200


# ── Utility functions — pure unit tests ──────────────────────────────────────

def test_sse_helper_formats_event_correctly():
    """_sse yardımcısı SSE formatına uygun string üretmeli."""
    sys.modules.pop("routes.monkey_routes", None)
    _stub_playwright_and_core()

    from routes.monkey_routes import _sse
    result = _sse("test_event", {"key": "value"})
    assert result.startswith("event: test_event\n")
    assert "data:" in result
    assert result.endswith("\n\n")


def test_categorize_error_javascript_error():
    """_categorize_error JavaScript hatasını doğru kategorilendirmeli."""
    _stub_playwright_and_core()
    from routes.monkey_routes import _categorize_error
    result = _categorize_error("Uncaught TypeError: Cannot read property")
    assert "JavaScript" in result or "Hatası" in result


def test_categorize_error_network_error():
    """_categorize_error ağ hatasını doğru kategorilendirmeli."""
    _stub_playwright_and_core()
    from routes.monkey_routes import _categorize_error
    result = _categorize_error("Failed to fetch resource from server")
    assert result != ""


def test_categorize_network_error_400():
    """_categorize_network_error 400 için doğru etiket dönmeli."""
    _stub_playwright_and_core()
    from routes.monkey_routes import _categorize_network_error
    result = _categorize_network_error(400)
    assert "400" in result


def test_categorize_network_error_500():
    """_categorize_network_error 500 için doğru etiket dönmeli."""
    _stub_playwright_and_core()
    from routes.monkey_routes import _categorize_network_error
    result = _categorize_network_error(500)
    assert "500" in result


def test_categorize_network_error_unknown():
    """_categorize_network_error bilinmeyen kod için fallback dönmeli."""
    _stub_playwright_and_core()
    from routes.monkey_routes import _categorize_network_error
    result = _categorize_network_error(999)
    assert "999" in result
