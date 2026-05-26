"""
tests/unit/test_accessibility_routes.py
=========================================
Accessibility blueprint (/api/a11y/*) icin birim testler.

core.accessibility_tester.AccessibilityTester ve config.settings
monkeypatching / sys.modules stub ile izole edilir.
"""
import importlib.util
import sys
import types
import json
import pytest
from pathlib import Path
from flask import Flask


# ── Stubs ─────────────────────────────────────────────────────────────────────

class _FakeA11yResult:
    """AccessibilityTester.test_url() cikti nesnesi stub'i."""

    def __init__(self, error=None):
        self.url = "https://example.com"
        self.score = 95
        self.violations = []
        self.warnings = []
        self.passes = []
        self.violation_count = 0
        self.error = error


class _FakeTester:
    def __init__(self, **kwargs):
        self._raise = False

    def test_url(self, url, wait_for=None, wait_ms=1000):
        if self._raise:
            raise RuntimeError("Tester hatasi")
        return _FakeA11yResult()

    def to_dict(self, result):
        return {
            "url": result.url,
            "score": result.score,
            "violations": result.violations,
            "warnings": result.warnings,
            "passes": result.passes,
            "violation_count": result.violation_count,
        }

    def generate_report(self, result, include_warnings=True):
        return "/tmp/fake_report.html"


class _FakeTesterWithError(_FakeTester):
    def test_url(self, url, wait_for=None, wait_ms=1000):
        raise RuntimeError("Tester hatasi simule edildi")


def _make_settings_stub(tmp_path=None):
    from pathlib import Path as P
    base = tmp_path or P("/tmp/neurex_test")
    settings_obj = types.SimpleNamespace(BASE_DIR=base)
    settings_mod = types.ModuleType("config.settings")
    settings_mod.settings = settings_obj
    config_pkg = types.ModuleType("config")
    sys.modules["config"] = config_pkg
    sys.modules["config.settings"] = settings_mod
    return settings_obj


def _make_a11y_tester_stub(tester_class=_FakeTester):
    """core.accessibility_tester modulu stub'i."""
    core_mod = sys.modules.setdefault("core", types.ModuleType("core"))
    a11y_mod = types.ModuleType("core.accessibility_tester")
    a11y_mod.AccessibilityTester = tester_class
    sys.modules["core.accessibility_tester"] = a11y_mod
    return a11y_mod


def _load_a11y_blueprint():
    for key in list(sys.modules.keys()):
        if "accessibility_routes" in key:
            del sys.modules[key]

    spec = importlib.util.spec_from_file_location(
        "accessibility_routes",
        "/Users/yasin_bulgan/Desktop/Neurex_QA/engine/routes/accessibility_routes.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def a11y_client(tmp_path):
    """Normal (basarili) tester ile istemci."""
    _make_settings_stub(tmp_path)
    _make_a11y_tester_stub(_FakeTester)
    mod = _load_a11y_blueprint()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(mod.a11y_bp)

    with app.test_client() as client:
        yield client, mod


@pytest.fixture
def a11y_client_error(tmp_path):
    """Tester exception firlatacak sekilde yapilandirilmis istemci."""
    _make_settings_stub(tmp_path)
    _make_a11y_tester_stub(_FakeTesterWithError)
    mod = _load_a11y_blueprint()

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(mod.a11y_bp)

    with app.test_client() as client:
        yield client, mod


# ── /api/a11y/test (POST) ─────────────────────────────────────────────────────

def test_test_url_missing_url_returns_400(a11y_client):
    """url alani gonderilmezse 400 donmeli."""
    client, _ = a11y_client
    resp = client.post("/api/a11y/test", json={}, content_type="application/json")
    assert resp.status_code == 400


def test_test_url_missing_url_has_error(a11y_client):
    client, _ = a11y_client
    data = client.post("/api/a11y/test", json={}).get_json()
    assert "error" in data
    assert data["ok"] is False


def test_test_url_empty_string_returns_400(a11y_client):
    client, _ = a11y_client
    resp = client.post("/api/a11y/test", json={"url": ""})
    assert resp.status_code == 400


def test_test_url_success_returns_200(a11y_client):
    client, _ = a11y_client
    resp = client.post("/api/a11y/test", json={"url": "https://example.com"})
    assert resp.status_code == 200


def test_test_url_success_ok_true(a11y_client):
    client, _ = a11y_client
    data = client.post("/api/a11y/test", json={"url": "https://example.com"}).get_json()
    assert data["ok"] is True


def test_test_url_result_has_violations_list(a11y_client):
    client, _ = a11y_client
    data = client.post("/api/a11y/test", json={"url": "https://example.com"}).get_json()
    assert "result" in data
    assert "violations" in data["result"]
    assert isinstance(data["result"]["violations"], list)


def test_test_url_result_has_score(a11y_client):
    client, _ = a11y_client
    data = client.post("/api/a11y/test", json={"url": "https://example.com"}).get_json()
    assert "score" in data["result"]


def test_test_url_tester_raises_returns_500(a11y_client_error):
    """Tester exception firlatirsa 500 donmeli."""
    client, _ = a11y_client_error
    resp = client.post("/api/a11y/test", json={"url": "https://example.com"})
    assert resp.status_code == 500


def test_test_url_tester_raises_ok_false(a11y_client_error):
    client, _ = a11y_client_error
    data = client.post("/api/a11y/test", json={"url": "https://example.com"}).get_json()
    assert data["ok"] is False


def test_test_url_accepts_wcag_level(a11y_client):
    client, _ = a11y_client
    resp = client.post("/api/a11y/test", json={"url": "https://example.com", "wcag_level": "AAA"})
    assert resp.status_code == 200


def test_test_url_accepts_ignore_rules(a11y_client):
    client, _ = a11y_client
    resp = client.post(
        "/api/a11y/test",
        json={"url": "https://example.com", "ignore_rules": ["color-contrast"]},
    )
    assert resp.status_code == 200


# ── /api/a11y/report (POST) ───────────────────────────────────────────────────

def test_report_missing_url_returns_400(a11y_client):
    client, _ = a11y_client
    resp = client.post("/api/a11y/report", json={})
    assert resp.status_code == 400


def test_report_with_url_returns_200(a11y_client):
    client, _ = a11y_client
    resp = client.post("/api/a11y/report", json={"url": "https://example.com"})
    assert resp.status_code == 200


def test_report_response_has_report_path(a11y_client):
    client, _ = a11y_client
    data = client.post("/api/a11y/report", json={"url": "https://example.com"}).get_json()
    assert "report_path" in data


# ── Blueprint sanity ──────────────────────────────────────────────────────────

def test_blueprint_registered_correctly(a11y_client):
    _, mod = a11y_client
    assert mod.a11y_bp is not None
    assert mod.a11y_bp.name == "accessibility"
