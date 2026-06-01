"""
tests/unit/test_wizard_routes.py
==================================
Wizard blueprint (/api/wizard/*) için birim testler.

Playwright, browser otomasyonu, LLM/AI çağrıları ve dosya G/Ç
işlemleri mock'lanır — yalnızca HTTP katmanı doğrulanır.

Kapsanan endpoint'ler (7 adet):
  POST /api/wizard/analyze-document
  POST /api/wizard/crawl
  POST /api/wizard/discover-selectors
  POST /api/wizard/monkey-test
  POST /api/wizard/generate-automation
  POST /api/wizard/full-run
  POST /api/wizard/run-nexusqa
"""
import importlib
import sys
import json
import pytest
from unittest.mock import MagicMock, patch


# ── Fixture ──────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch):
    """
    Playwright ve AI engine bağımlılıkları stub'lanmış test istemcisi.
    sys.modules manipülasyonu ile modüller uygulama import edilmeden önce
    enjekte edilir.
    """
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    # Playwright stub — sync_playwright() context manager taklit edilir
    fake_pw_module = MagicMock()
    fake_browser = MagicMock()
    fake_context = MagicMock()
    fake_page = MagicMock()
    fake_page.evaluate.return_value = {
        "title": "Test Page",
        "headings": [],
        "buttons": [],
        "inputs": [],
        "links": [],
        "forms_count": 0,
        "tables_count": 0,
        "elements": [],
    }
    fake_page.screenshot.return_value = b"fake-screenshot-bytes"
    fake_context.new_page.return_value = fake_page
    fake_browser.new_context.return_value = fake_context
    fake_browser.new_page.return_value = fake_page

    fake_playwright_instance = MagicMock()
    fake_playwright_instance.chromium.launch.return_value = fake_browser

    fake_pw_ctx = MagicMock()
    fake_pw_ctx.__enter__ = MagicMock(return_value=fake_playwright_instance)
    fake_pw_ctx.__exit__ = MagicMock(return_value=False)
    fake_pw_module.sync_playwright.return_value = fake_pw_ctx

    monkeypatch.setitem(sys.modules, "playwright", fake_pw_module)
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_pw_module)

    # AI engine stub
    fake_ai_engine = MagicMock()
    fake_ai_engine.extract_manual_tests_from_text.return_value = [
        {"title": "Test Senaryosu 1", "steps": []}
    ]
    fake_ai_engine.generate_gherkin.return_value = "Feature: Test\n  Scenario: Example\n    Given I am on the page"
    fake_ai_engine.generate_test_file.return_value = "def test_example(): pass"
    fake_ai_module = MagicMock()
    fake_ai_module.get_ai_engine.return_value = fake_ai_engine
    monkeypatch.setitem(sys.modules, "core.ai_engine", fake_ai_module)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(engine_client):
    """Oturum enjekte edilmiş istemci — kimlik doğrulama gerektiren endpoint'ler için."""
    with engine_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return engine_client


# ── /api/wizard/analyze-document ─────────────────────────────────────────────

def test_analyze_document_requires_auth(engine_client):
    """/api/wizard/analyze-document oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/analyze-document",
        json={"text": "test metni"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_analyze_document_missing_text_returns_400(authed_client):
    """text alanı boş veya eksikken 400 ve error anahtarı dönmeli."""
    resp = authed_client.post(
        "/api/wizard/analyze-document",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_analyze_document_blank_text_returns_400(authed_client):
    """Yalnızca boşluk içeren text ile 400 dönmeli."""
    resp = authed_client.post(
        "/api/wizard/analyze-document",
        json={"text": "   "},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_analyze_document_success_shape(authed_client):
    """Geçerli text ile 200 ve beklenen JSON yapısı dönmeli."""
    with patch("core.ai_engine.get_ai_engine") as mock_get:
        mock_engine = MagicMock()
        mock_engine.extract_manual_tests_from_text.return_value = [
            {"title": "Login testi", "steps": []}
        ]
        mock_get.return_value = mock_engine

        resp = authed_client.post(
            "/api/wizard/analyze-document",
            json={"text": "Kullanıcı sisteme giriş yapabilmelidir."},
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "manual_tests" in data
    assert "count" in data
    assert isinstance(data["count"], int)


# ── /api/wizard/crawl ─────────────────────────────────────────────────────────

def test_crawl_requires_auth(engine_client):
    """/api/wizard/crawl oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/crawl",
        json={"url": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_crawl_missing_url_returns_400(authed_client):
    """url alanı eksikken 400 ve error anahtarı dönmeli."""
    resp = authed_client.post(
        "/api/wizard/crawl",
        json={"max_pages": 5},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_crawl_success_shape(authed_client):
    """Geçerli URL ile mock Playwright üzerinden 200 ve beklenen JSON yapısı dönmeli."""
    fake_pw = MagicMock()
    fake_page = MagicMock()
    fake_page.evaluate.return_value = {
        "title": "Home",
        "headings": ["Welcome"],
        "buttons": [],
        "inputs": [],
        "links": [],
        "forms_count": 0,
        "tables_count": 0,
    }
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_browser = MagicMock()
    fake_browser.new_context.return_value = fake_context
    fake_playwright_inst = MagicMock()
    fake_playwright_inst.chromium.launch.return_value = fake_browser
    fake_pw.sync_playwright.return_value.__enter__ = MagicMock(return_value=fake_playwright_inst)
    fake_pw.sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

    with patch.dict("sys.modules", {"playwright.sync_api": fake_pw}):
        resp = authed_client.post(
            "/api/wizard/crawl",
            json={"url": "https://example.com", "max_pages": 1},
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "pages" in data
    assert "visited_count" in data


# ── /api/wizard/discover-selectors ───────────────────────────────────────────

def test_discover_selectors_requires_auth(engine_client):
    """/api/wizard/discover-selectors oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/discover-selectors",
        json={"url": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_discover_selectors_missing_url_returns_400(authed_client):
    """url alanı eksikken 400 ve error anahtarı dönmeli."""
    resp = authed_client.post(
        "/api/wizard/discover-selectors",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_discover_selectors_success_shape(authed_client):
    """Geçerli URL ile 200 ve elements listesi içeren JSON dönmeli."""
    fake_pw = MagicMock()
    fake_page = MagicMock()
    fake_page.evaluate.return_value = [
        {"tag": "button", "type": "", "text": "Giriş Yap", "css": "#login-btn", "xpath": "//*[@id='login-btn']"}
    ]
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_context.route = MagicMock()
    fake_browser = MagicMock()
    fake_browser.new_context.return_value = fake_context
    fake_playwright_inst = MagicMock()
    fake_playwright_inst.chromium.launch.return_value = fake_browser
    fake_pw.sync_playwright.return_value.__enter__ = MagicMock(return_value=fake_playwright_inst)
    fake_pw.sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

    with patch.dict("sys.modules", {"playwright.sync_api": fake_pw}):
        resp = authed_client.post(
            "/api/wizard/discover-selectors",
            json={"url": "https://example.com"},
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "elements" in data
    assert "element_count" in data
    assert isinstance(data["elements"], list)


# ── /api/wizard/monkey-test ───────────────────────────────────────────────────

def test_monkey_test_requires_auth(engine_client):
    """/api/wizard/monkey-test oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/monkey-test",
        json={"url": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_monkey_test_missing_url_returns_400(authed_client):
    """url alanı eksikken 400 ve error anahtarı dönmeli."""
    resp = authed_client.post(
        "/api/wizard/monkey-test",
        json={"max_actions": 5},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_monkey_test_success_shape(authed_client):
    """Geçerli URL ile 200 ve stability_score içeren JSON dönmeli."""
    fake_pw = MagicMock()
    fake_page = MagicMock()
    fake_page.evaluate.return_value = []
    fake_page.query_selector_all.return_value = []
    fake_page.screenshot.return_value = b"fake-screenshot"
    fake_context = MagicMock()
    fake_context.new_page.return_value = fake_page
    fake_browser = MagicMock()
    fake_browser.new_context.return_value = fake_context
    fake_playwright_inst = MagicMock()
    fake_playwright_inst.chromium.launch.return_value = fake_browser
    fake_pw.sync_playwright.return_value.__enter__ = MagicMock(return_value=fake_playwright_inst)
    fake_pw.sync_playwright.return_value.__exit__ = MagicMock(return_value=False)

    with patch.dict("sys.modules", {"playwright.sync_api": fake_pw}):
        resp = authed_client.post(
            "/api/wizard/monkey-test",
            json={"url": "https://example.com", "max_actions": 0},
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "stability_score" in data
    assert "actions_performed" in data
    assert "console_errors" in data
    assert "network_errors" in data


# ── /api/wizard/generate-automation ──────────────────────────────────────────

def test_generate_automation_requires_auth(engine_client):
    """/api/wizard/generate-automation oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/generate-automation",
        json={"scenarios": [{"title": "Test"}]},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_generate_automation_missing_scenarios_returns_400(authed_client):
    """scenarios alanı boş veya eksikken 400 dönmeli."""
    resp = authed_client.post(
        "/api/wizard/generate-automation",
        json={"url": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_generate_automation_empty_list_returns_400(authed_client):
    """Boş scenarios listesi ile 400 dönmeli."""
    resp = authed_client.post(
        "/api/wizard/generate-automation",
        json={"scenarios": []},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_generate_automation_success_shape(authed_client):
    """Geçerli senaryo listesi ile 200 ve feature_files/test_files içeren JSON dönmeli."""
    with patch("core.ai_engine.get_ai_engine") as mock_get:
        mock_engine = MagicMock()
        mock_engine.generate_gherkin.return_value = "Feature: Login\n  Scenario: Valid login\n    Given a user"
        mock_engine.generate_test_file.return_value = "def test_login(): pass"
        mock_get.return_value = mock_engine

        resp = authed_client.post(
            "/api/wizard/generate-automation",
            json={
                "scenarios": [{"title": "Giriş Testi", "steps": [{"action": "Tıkla", "expected": "Açılır"}]}],
                "url": "https://example.com",
                "project_name": "my_project",
            },
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "feature_files" in data
    assert "test_files" in data
    assert isinstance(data["feature_files"], list)
    assert len(data["feature_files"]) == 1


# ── /api/wizard/full-run ─────────────────────────────────────────────────────

def test_full_run_requires_auth(engine_client):
    """/api/wizard/full-run oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/full-run",
        json={"text": "test", "url": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_full_run_no_text_no_url_returns_200_skipped(authed_client):
    """text ve url verilmezse adımlar skipped olarak 200 dönmeli."""
    resp = authed_client.post(
        "/api/wizard/full-run",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("status") == "ok"
    assert "steps" in data
    # document_analysis adımı skipped olmalı
    step_names = [s["name"] for s in data["steps"]]
    assert "document_analysis" in step_names
    doc_step = next(s for s in data["steps"] if s["name"] == "document_analysis")
    assert doc_step["status"] == "skipped"


def test_full_run_with_text_triggers_document_analysis(authed_client):
    """text sağlandığında document_analysis adımı ok statüsünde dönmeli."""
    with patch("core.ai_engine.get_ai_engine") as mock_get:
        mock_engine = MagicMock()
        mock_engine.extract_manual_tests_from_text.return_value = [{"title": "T1", "steps": []}]
        mock_get.return_value = mock_engine

        resp = authed_client.post(
            "/api/wizard/full-run",
            json={"text": "Kullanıcı giriş yapabilmeli."},
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    doc_step = next((s for s in data["steps"] if s["name"] == "document_analysis"), None)
    assert doc_step is not None
    assert doc_step["status"] == "ok"
    assert doc_step["count"] == 1


# ── /api/wizard/run-nexusqa ──────────────────────────────────────────────────

def test_run_nexusqa_requires_auth(engine_client):
    """/api/wizard/run-nexusqa oturum açılmadan 401 dönmeli."""
    resp = engine_client.post(
        "/api/wizard/run-nexusqa",
        json={"features": [{"title": "T", "content": "Feature: T"}]},
        content_type="application/json",
    )
    assert resp.status_code == 401


def test_run_nexusqa_missing_features_returns_400(authed_client):
    """features listesi boş veya eksikken 400 ve ok=False dönmeli."""
    resp = authed_client.post(
        "/api/wizard/run-nexusqa",
        json={"url": "https://example.com"},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("ok") is False
    assert "error" in data


def test_run_nexusqa_empty_features_returns_400(authed_client):
    """Boş features listesi ile 400 dönmeli."""
    resp = authed_client.post(
        "/api/wizard/run-nexusqa",
        json={"features": []},
        content_type="application/json",
    )
    assert resp.status_code == 400
    data = resp.get_json()
    assert data.get("ok") is False


def test_run_nexusqa_success_shape(authed_client, tmp_path, monkeypatch):
    """
    Geçerli features ile subprocess mock'lanarak 200 ve beklenen JSON şekli dönmeli.
    Dosya G/Ç settings dizinleri geçici path'e yönlendirilir.
    """
    import subprocess as real_subprocess

    # settings dizinlerini geçici path'e yönlendir
    features_dir = tmp_path / "features"
    tests_dir = tmp_path / "tests"
    locators_dir = tmp_path / "locators"
    testdata_dir = tmp_path / "testdata"
    allure_dir = tmp_path / "allure"
    for d in [features_dir, tests_dir, locators_dir, testdata_dir, allure_dir]:
        d.mkdir(parents=True)

    monkeypatch.setattr("config.settings.settings.FEATURES_DIR", features_dir, raising=False)
    monkeypatch.setattr("config.settings.settings.TESTS_DIR", tests_dir, raising=False)
    monkeypatch.setattr("config.settings.settings.LOCATORS_DIR", locators_dir, raising=False)
    monkeypatch.setattr("config.settings.settings.TESTDATA_DIR", testdata_dir, raising=False)
    monkeypatch.setattr("config.settings.settings.ALLURE_RESULTS_DIR", allure_dir, raising=False)
    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("config.settings.settings.BASE_URL", "http://localhost", raising=False)

    fake_glue = MagicMock(return_value="# glue file")
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = "1 passed"
    fake_proc.stderr = ""

    with patch("routes.runner_routes._build_glue_file_content", fake_glue), \
         patch("subprocess.run", return_value=fake_proc):
        resp = authed_client.post(
            "/api/wizard/run-nexusqa",
            json={
                "features": [{"title": "Login Testi", "content": "Feature: Login\n  Scenario: Test\n    Given I open the page"}],
                "url": "https://example.com",
                "domain": "default",
                "browser": "chromium",
            },
            content_type="application/json",
        )

    assert resp.status_code == 200
    data = resp.get_json()
    assert "ok" in data
    assert "exit_code" in data
    assert "passed" in data
    assert "failed" in data
    assert "output" in data
