"""
tests/unit/test_magic_test_routes.py
====================================
magic_test_bp (/api/magic/generate-test-cases, /api/magic/monkey-test,
               /api/magic/analyze-test-strategy, /api/magic/test-cases,
               /api/magic/test-cases/<id>, /api/magic/test-cases/<id>/export)
için birim testler.

Playwright, BrowserEngine, PageInspector, AI engine ve TestCaseManager
monkeypatching ile izole edilir.
"""
import sys
import types
import json
import pytest
from unittest.mock import MagicMock, patch


# ── Stub helpers ──────────────────────────────────────────────────────────────

def _stub_magic_deps():
    """magic_test_routes için gerekli stub modülleri oluşturur."""

    # playwright stub
    pw_mock = MagicMock()
    sys.modules.setdefault("playwright", pw_mock)
    sys.modules.setdefault("playwright.sync_api", pw_mock)

    # core package
    core_pkg = sys.modules.get("core") or types.ModuleType("core")

    # core.test_case_manager
    tcm_mod = types.ModuleType("core.test_case_manager")
    _tcm = MagicMock()
    _tcm.create_test_case.return_value = "test_abc123"
    _tcm.list_test_cases.return_value = []
    _tcm.get_test_case.return_value = None
    _tcm.get_execution_history.return_value = []
    _tcm.export_test_case_to_gherkin.return_value = "Feature: test"
    _tcm.record_strategy_analysis.return_value = "analysis_001"

    class _FakeTCM:
        def __init__(self): pass
        def create_test_case(self, **kw): return _tcm.create_test_case(**kw)
        def list_test_cases(self, url=None, limit=50): return _tcm.list_test_cases(url=url, limit=limit)
        def get_test_case(self, test_id): return _tcm.get_test_case(test_id)
        def get_execution_history(self, test_id): return _tcm.get_execution_history(test_id)
        def export_test_case_to_gherkin(self, test_id): return _tcm.export_test_case_to_gherkin(test_id)
        def record_strategy_analysis(self, **kw): return _tcm.record_strategy_analysis(**kw)

    tcm_mod.TestCaseManager = _FakeTCM
    core_pkg.test_case_manager = tcm_mod
    sys.modules["core"] = core_pkg
    sys.modules["core.test_case_manager"] = tcm_mod

    # core.ai_engine
    ai_mod = types.ModuleType("core.ai_engine")
    _ai = MagicMock()
    _ai.generate_test_cases_with_explanations.return_value = [
        {"title": "Sample Test", "steps": ["Step 1"], "explanations": ["exp"],
         "risk_level": "low", "tags": [], "description": "desc"}
    ]
    _ai.analyze_page_for_test_strategy.return_value = {
        "complexity_score": 5.0,
        "critical_elements": [],
        "recommendations": [],
        "best_practices": [],
    }
    ai_mod.get_ai_engine = lambda: _ai
    core_pkg.ai_engine = ai_mod
    sys.modules["core.ai_engine"] = ai_mod

    # core.page_inspector
    pi_mod = types.ModuleType("core.page_inspector")
    class _FakeInspector:
        def __init__(self, page): pass
        def get_summary_text(self): return "summary"
        def detect_page_type(self): return "login"
        def get_form_fields_with_validation(self): return []
        def get_interactive_elements_ranked(self): return []
    pi_mod.PageInspector = _FakeInspector
    core_pkg.page_inspector = pi_mod
    sys.modules["core.page_inspector"] = pi_mod

    # core.browser
    br_mod = types.ModuleType("core.browser")
    class _FakeBrowserEngine:
        def get_page(self, url): return MagicMock()
        def close_page(self, page): pass
    br_mod.BrowserEngine = _FakeBrowserEngine
    core_pkg.browser = br_mod
    sys.modules["core.browser"] = br_mod

    # core.monkey_test_engine (lazy import inside route)
    mte_mod = types.ModuleType("core.monkey_test_engine")
    class _FakeMTE:
        def run_monkey_test_streamed(self, **kw):
            yield {"progress": 100, "status": "done"}
    mte_mod.MonkeyTestEngine = _FakeMTE
    core_pkg.monkey_test_engine = mte_mod
    sys.modules["core.monkey_test_engine"] = mte_mod

    return _tcm, _ai


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def magic_client():
    """Sadece magic_test_bp ile kurulmuş minimal Flask test istemcisi."""
    _tcm_mock, _ai_mock = _stub_magic_deps()

    sys.modules.pop("routes.magic_test_routes", None)
    sys.modules.pop("magic_test_routes", None)

    from flask import Flask
    from routes.magic_test_routes import magic_test_bp

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.secret_key = "test-secret"
    app.register_blueprint(magic_test_bp)

    with app.test_client() as client:
        yield client, _tcm_mock, _ai_mock


# ── POST /api/magic/generate-test-cases ──────────────────────────────────────

def test_generate_test_cases_missing_url_returns_400(magic_client):
    """URL olmadan /api/magic/generate-test-cases 400 dönmeli."""
    client, _, _ = magic_client
    response = client.post(
        "/api/magic/generate-test-cases",
        json={"goals": "Login testi"},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_generate_test_cases_missing_url_has_error_field(magic_client):
    """URL eksikliğinde yanıt error alanı içermeli."""
    client, _, _ = magic_client
    response = client.post(
        "/api/magic/generate-test-cases",
        json={},
        content_type="application/json",
    )
    data = response.get_json()
    assert "error" in data


def test_generate_test_cases_success_returns_201(monkeypatch, magic_client):
    """Geçerli URL ile test üretimi 201 dönmeli."""
    client, tcm_mock, ai_mock = magic_client

    with patch("routes.magic_test_routes.sync_playwright") as mock_pw:
        _setup_playwright_mock(mock_pw)
        response = client.post(
            "/api/magic/generate-test-cases",
            json={"url": "https://example.com/login", "goals": "Login test", "count": 2},
            content_type="application/json",
        )
    assert response.status_code == 201


def test_generate_test_cases_success_has_status_field(monkeypatch, magic_client):
    """Başarılı yanıt status='success' içermeli."""
    client, _, _ = magic_client

    with patch("routes.magic_test_routes.sync_playwright") as mock_pw:
        _setup_playwright_mock(mock_pw)
        response = client.post(
            "/api/magic/generate-test-cases",
            json={"url": "https://example.com"},
            content_type="application/json",
        )
    data = response.get_json()
    assert data.get("status") == "success"


def test_generate_test_cases_returns_test_cases_list(monkeypatch, magic_client):
    """Başarılı yanıt test_cases listesi içermeli."""
    client, _, _ = magic_client

    with patch("routes.magic_test_routes.sync_playwright") as mock_pw:
        _setup_playwright_mock(mock_pw)
        response = client.post(
            "/api/magic/generate-test-cases",
            json={"url": "https://example.com"},
            content_type="application/json",
        )
    data = response.get_json()
    assert isinstance(data.get("test_cases"), list)


# ── POST /api/magic/monkey-test ───────────────────────────────────────────────

def test_monkey_test_missing_url_streams_error(magic_client):
    """URL olmadan monkey-test SSE akışı hata mesajı içermeli."""
    client, _, _ = magic_client
    response = client.post(
        "/api/magic/monkey-test",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 200  # SSE always 200
    body = response.data.decode()
    assert "error" in body


def test_monkey_test_returns_event_stream_content_type(magic_client):
    """monkey-test text/event-stream content-type dönmeli."""
    client, _, _ = magic_client
    response = client.post(
        "/api/magic/monkey-test",
        json={"url": "https://example.com"},
        content_type="application/json",
    )
    assert "text/event-stream" in response.content_type


# ── POST /api/magic/analyze-test-strategy ────────────────────────────────────

def test_analyze_strategy_missing_url_returns_400(magic_client):
    """URL olmadan /api/magic/analyze-test-strategy 400 dönmeli."""
    client, _, _ = magic_client
    response = client.post(
        "/api/magic/analyze-test-strategy",
        json={},
        content_type="application/json",
    )
    assert response.status_code == 400


def test_analyze_strategy_success_returns_200(magic_client):
    """Geçerli URL ile strateji analizi 200 dönmeli."""
    client, _, _ = magic_client

    with patch("routes.magic_test_routes.sync_playwright") as mock_pw:
        _setup_playwright_mock(mock_pw)
        response = client.post(
            "/api/magic/analyze-test-strategy",
            json={"url": "https://example.com/checkout"},
            content_type="application/json",
        )
    assert response.status_code == 200


def test_analyze_strategy_success_has_status_field(magic_client):
    """Strateji analizi yanıtı status='success' içermeli."""
    client, _, _ = magic_client

    with patch("routes.magic_test_routes.sync_playwright") as mock_pw:
        _setup_playwright_mock(mock_pw)
        response = client.post(
            "/api/magic/analyze-test-strategy",
            json={"url": "https://example.com/checkout"},
            content_type="application/json",
        )
    data = response.get_json()
    assert data.get("status") == "success"


# ── GET /api/magic/test-cases ─────────────────────────────────────────────────

def test_list_test_cases_returns_200(magic_client):
    """GET /api/magic/test-cases 200 dönmeli."""
    client, _, _ = magic_client
    response = client.get("/api/magic/test-cases")
    assert response.status_code == 200


def test_list_test_cases_returns_json_with_status(magic_client):
    """Test case listesi yanıtı status alanı içermeli."""
    client, _, _ = magic_client
    response = client.get("/api/magic/test-cases")
    data = response.get_json()
    assert data.get("status") == "success"


def test_list_test_cases_empty_db_returns_empty_list(magic_client):
    """DB boş iken test_cases listesi boş dönmeli."""
    client, _, _ = magic_client
    response = client.get("/api/magic/test-cases")
    data = response.get_json()
    assert data.get("test_cases") == []


def test_list_test_cases_with_data(monkeypatch, magic_client):
    """DB'de kayıt varken list endpoint onları dönmeli."""
    client, tcm_mock, _ = magic_client
    tcm_mock.list_test_cases.return_value = [
        {"test_id": "t1", "title": "Login Test", "risk_level": "low"}
    ]
    response = client.get("/api/magic/test-cases")
    data = response.get_json()
    assert data.get("total") == 1


# ── GET /api/magic/test-cases/<test_id> ──────────────────────────────────────

def test_get_test_case_not_found_returns_404(magic_client):
    """Olmayan test_id ile GET /api/magic/test-cases/<id> 404 dönmeli."""
    client, _, _ = magic_client
    response = client.get("/api/magic/test-cases/nonexistent")
    assert response.status_code == 404


def test_get_test_case_found_returns_200(monkeypatch, magic_client):
    """Mevcut test_id ile GET 200 dönmeli."""
    client, tcm_mock, _ = magic_client
    tcm_mock.get_test_case.return_value = {"test_id": "t42", "title": "Smoke"}
    response = client.get("/api/magic/test-cases/t42")
    assert response.status_code == 200


# ── GET /api/magic/test-cases/<test_id>/export ───────────────────────────────

def test_export_test_case_not_found_returns_404(magic_client):
    """Olmayan test_id ile export 404 dönmeli."""
    client, _, _ = magic_client
    response = client.get("/api/magic/test-cases/bad_id/export")
    assert response.status_code == 404


def test_export_test_case_gherkin_format_returns_plain_text(monkeypatch, magic_client):
    """Gherkin formatı ile export text/plain dönmeli."""
    client, tcm_mock, _ = magic_client
    tcm_mock.get_test_case.return_value = {"test_id": "t1", "title": "Login"}
    tcm_mock.export_test_case_to_gherkin.return_value = "Feature: Login\n  Scenario: ..."
    response = client.get("/api/magic/test-cases/t1/export?format=gherkin")
    assert response.status_code == 200
    assert "text/plain" in response.content_type


def test_export_test_case_json_format_returns_200(monkeypatch, magic_client):
    """JSON formatı ile export 200 dönmeli."""
    client, tcm_mock, _ = magic_client
    tcm_mock.get_test_case.return_value = {"test_id": "t1", "title": "Login"}
    response = client.get("/api/magic/test-cases/t1/export?format=json")
    assert response.status_code == 200


def test_export_test_case_invalid_format_returns_400(monkeypatch, magic_client):
    """Geçersiz format ile export 400 dönmeli."""
    client, tcm_mock, _ = magic_client
    tcm_mock.get_test_case.return_value = {"test_id": "t1", "title": "Login"}
    response = client.get("/api/magic/test-cases/t1/export?format=xml")
    assert response.status_code == 400


# ── Helper ────────────────────────────────────────────────────────────────────

def _setup_playwright_mock(mock_pw):
    """sync_playwright context manager mock'u yapılandırır."""
    mock_page = MagicMock()
    mock_page.goto.return_value = None
    mock_page.wait_for_timeout.return_value = None

    mock_context = MagicMock()
    mock_context.new_page.return_value = mock_page

    mock_browser = MagicMock()
    mock_browser.new_context.return_value = mock_context

    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.launch.return_value = mock_browser

    mock_pw.return_value.__enter__ = lambda s: mock_pw_instance
    mock_pw.return_value.__exit__ = MagicMock(return_value=False)
