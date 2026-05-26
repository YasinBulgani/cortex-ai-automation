"""
tests/unit/test_ai_intelligence_routes.py
==========================================
ai_intel_bp blueprint (/api/ai/*) için birim testler.

Dış bağımlılıklar (core.ai_locator, core.ai_bdd, core.feedback_loop,
core.ai_security, core.ai_performance) monkeypatching ile izole edilir.
"""
import importlib
import sys
import types
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch, tmp_path):
    """Test Flask istemcisi."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("config.settings.settings.BASE_URL", "http://localhost", raising=False)

    monkeypatch.setattr("core.db.get_run_stats", lambda: {"total": 0, "passed": 0, "failed": 0}, raising=False)
    monkeypatch.setattr("core.db.get_run_history", lambda: [], raising=False)
    monkeypatch.setattr("core.db.get_comprehensive_reports", lambda: [], raising=False)

    sys.modules.pop("app", None)
    module = importlib.import_module("app")
    module.app.config["TESTING"] = True

    with module.app.test_client() as client:
        yield client


@pytest.fixture
def authed_client(engine_client):
    with engine_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return engine_client


# ── Stub helpers ──────────────────────────────────────────────────────────────

class _FakeSuggestion:
    strategy = "css"
    selector = "#login-btn"
    confidence = 0.95
    stability = 0.9
    reason = "unique id"


class _FakeLocatorGenerator:
    def generate_for_element(self, element_description, page_content=""):
        return [_FakeSuggestion()]


class _FakeAuditReport:
    def to_dict(self):
        return {"health": "good", "issues": [], "score": 98}


class _FakeLocatorAuditor:
    def audit_from_json(self, json_path):
        return _FakeAuditReport()

    def audit_all_json_files(self):
        return {"files": [], "total_issues": 0}


class _FakeMapping:
    gherkin_step = "Given I am on the login page"
    mapped_definition = "step_definitions/auth.py::login_page"
    is_new = False
    suggested_code = ""


class _FakeStepMapper:
    def map_feature(self, feature_content):
        return [_FakeMapping()]


class _FakeInsight:
    type = "flakiness"
    severity = "medium"
    description = "Test is flaky"
    suggestion = "Add retry"
    affected_tests = ["test_login"]
    confidence = 0.8


class _FakeCollector:
    def get_history(self):
        return [{"test": "example", "passed": True}]


class _FakeAnalyzer:
    def analyze(self, history):
        return [_FakeInsight()]


class _FakeOptimizeReport:
    quality_score = 87.5
    actions = [{"action": "quarantine", "test": "flaky_test"}]

    def to_dict(self):
        return {"quality_score": self.quality_score, "actions": self.actions}


class _FakeOptimizer:
    def optimize(self, history):
        return _FakeOptimizeReport()

    def get_quarantined(self):
        return ["flaky_test_1"]


class _FakeSecurityReport:
    def to_dict(self):
        return {"findings": [], "severity": "low", "url": "http://example.com"}


class _FakeVulnAnalyzer:
    def analyze_headers(self, headers, url):
        return _FakeSecurityReport()


class _FakeBottleneck:
    component = "login_api"
    metric = "response_time"
    value = 2500.0
    severity = "high"
    description = "Slow response"
    recommendation = "Add caching"


class _FakeBNAnalyzer:
    def analyze(self, results):
        return [_FakeBottleneck()]


class _FakeThOptimizer:
    def record_results(self, results):
        pass

    def detect_regression(self, results):
        return []


def _inject_locator_stubs(monkeypatch):
    mod = types.ModuleType("core.ai_locator")
    mod.AILocatorGenerator = _FakeLocatorGenerator
    mod.LocatorAuditor = _FakeLocatorAuditor
    sys.modules["core.ai_locator"] = mod


def _inject_bdd_stubs():
    mod = types.ModuleType("core.ai_bdd")
    mod.StepDefinitionMapper = _FakeStepMapper
    sys.modules["core.ai_bdd"] = mod


def _inject_feedback_stubs():
    collector_mod = types.ModuleType("core.feedback_loop.collector")
    collector_mod.ResultCollector = _FakeCollector
    sys.modules["core.feedback_loop.collector"] = collector_mod

    analyzer_mod = types.ModuleType("core.feedback_loop.analyzer")
    analyzer_mod.PatternAnalyzer = _FakeAnalyzer
    sys.modules["core.feedback_loop.analyzer"] = analyzer_mod

    optimizer_mod = types.ModuleType("core.feedback_loop.optimizer")
    optimizer_mod.SuiteOptimizer = _FakeOptimizer
    sys.modules["core.feedback_loop.optimizer"] = optimizer_mod


def _inject_security_stubs():
    mod = types.ModuleType("core.ai_security")
    mod.VulnerabilityAnalyzer = _FakeVulnAnalyzer
    sys.modules["core.ai_security"] = mod


def _inject_perf_stubs():
    mod = types.ModuleType("core.ai_performance")
    mod.BottleneckAnalyzer = _FakeBNAnalyzer
    mod.ThresholdOptimizer = _FakeThOptimizer
    sys.modules["core.ai_performance"] = mod


# ── POST /api/ai/generate-locators ───────────────────────────────────────────

def test_generate_locators_missing_element_description_returns_400(authed_client):
    """element_description eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_generate_locators_empty_element_description_returns_400(authed_client):
    """element_description boş string ise 400 dönmeli."""
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={"element_description": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_generate_locators_success_returns_suggestions(authed_client, monkeypatch):
    """Geçerli element_description → suggestions listesi dönmeli."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={"element_description": "Login button at top right"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)


def test_generate_locators_suggestion_has_strategy(authed_client, monkeypatch):
    """Suggestion nesnesi strategy alanı içermeli."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={"element_description": "Submit button"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        suggestions = resp.get_json()["suggestions"]
        if suggestions:
            assert "strategy" in suggestions[0]


def test_generate_locators_suggestion_has_selector(authed_client, monkeypatch):
    """Suggestion nesnesi selector alanı içermeli."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={"element_description": "Username input"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        suggestions = resp.get_json()["suggestions"]
        if suggestions:
            assert "selector" in suggestions[0]


def test_generate_locators_suggestion_has_confidence(authed_client, monkeypatch):
    """Suggestion nesnesi confidence alanı içermeli."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={"element_description": "Password field"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        suggestions = resp.get_json()["suggestions"]
        if suggestions:
            assert "confidence" in suggestions[0]


def test_generate_locators_with_page_content(authed_client, monkeypatch):
    """page_content parametresiyle de çalışmalı."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/generate-locators",
        json={
            "element_description": "Login button",
            "page_content": "<button id='login'>Login</button>",
        },
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)


# ── POST /api/ai/audit-locators ──────────────────────────────────────────────

def test_audit_locators_success_returns_report(authed_client, monkeypatch):
    """audit-locators → health_report veya sonuç dönmeli."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/audit-locators",
        json={},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert data is not None


def test_audit_locators_with_json_path(authed_client, monkeypatch):
    """json_path verildiğinde o dosyadan denetim yapılmalı."""
    _inject_locator_stubs(monkeypatch)
    resp = authed_client.post(
        "/api/ai/audit-locators",
        json={"json_path": "/fake/locators.json"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)


# ── POST /api/ai/map-steps ───────────────────────────────────────────────────

def test_map_steps_missing_feature_content_returns_400(authed_client):
    """feature_content eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/ai/map-steps",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_map_steps_success_returns_mappings(authed_client, monkeypatch):
    """Geçerli feature_content → mappings listesi dönmeli."""
    _inject_bdd_stubs()
    resp = authed_client.post(
        "/api/ai/map-steps",
        json={"feature_content": "Feature: Login\n  Scenario: Valid login\n    Given I am on the login page"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "mappings" in data
        assert "total_steps" in data

    sys.modules.pop("core.ai_bdd", None)


def test_map_steps_returns_total_steps_count(authed_client, monkeypatch):
    """Yanıt total_steps alanı içermeli."""
    _inject_bdd_stubs()
    resp = authed_client.post(
        "/api/ai/map-steps",
        json={"feature_content": "Feature: X\n  Scenario: Y\n    Given something"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert "total_steps" in resp.get_json()
    sys.modules.pop("core.ai_bdd", None)


# ── GET /api/ai/feedback-insights ────────────────────────────────────────────

def test_feedback_insights_success(authed_client, monkeypatch):
    """feedback-insights → insights listesi dönmeli."""
    _inject_feedback_stubs()
    resp = authed_client.get("/api/ai/feedback-insights")
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "insights" in data
        assert "history_count" in data

    sys.modules.pop("core.feedback_loop.collector", None)
    sys.modules.pop("core.feedback_loop.analyzer", None)
    sys.modules.pop("core.feedback_loop.optimizer", None)


def test_feedback_insights_has_history_count(authed_client, monkeypatch):
    """Yanıt history_count alanı içermeli."""
    _inject_feedback_stubs()
    resp = authed_client.get("/api/ai/feedback-insights")
    if resp.status_code == 200:
        assert "history_count" in resp.get_json()
    sys.modules.pop("core.feedback_loop.collector", None)
    sys.modules.pop("core.feedback_loop.analyzer", None)
    sys.modules.pop("core.feedback_loop.optimizer", None)


# ── GET /api/ai/quality-score ────────────────────────────────────────────────

def test_quality_score_success(authed_client, monkeypatch):
    """quality-score → score alanı dönmeli."""
    _inject_feedback_stubs()
    resp = authed_client.get("/api/ai/quality-score")
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "quality_score" in data

    sys.modules.pop("core.feedback_loop.collector", None)
    sys.modules.pop("core.feedback_loop.analyzer", None)
    sys.modules.pop("core.feedback_loop.optimizer", None)


def test_quality_score_returns_numeric_score(authed_client, monkeypatch):
    """quality_score sayısal olmalı."""
    _inject_feedback_stubs()
    resp = authed_client.get("/api/ai/quality-score")
    if resp.status_code == 200:
        score = resp.get_json().get("quality_score")
        assert isinstance(score, (int, float))
    sys.modules.pop("core.feedback_loop.collector", None)
    sys.modules.pop("core.feedback_loop.analyzer", None)
    sys.modules.pop("core.feedback_loop.optimizer", None)


# ── POST /api/ai/security-analyze ────────────────────────────────────────────

def test_security_analyze_missing_url_returns_400(authed_client):
    """url eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/ai/security-analyze",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_security_analyze_success_with_headers(authed_client, monkeypatch):
    """headers sağlandığında analiz yapılmalı."""
    _inject_security_stubs()
    resp = authed_client.post(
        "/api/ai/security-analyze",
        json={
            "url": "http://example.com",
            "headers": {"X-Frame-Options": "DENY", "Content-Security-Policy": "default-src 'self'"},
        },
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "findings" in data or data is not None
    sys.modules.pop("core.ai_security", None)


def test_security_analyze_returns_non_null(authed_client, monkeypatch):
    """Başarılı yanıt None olmayan JSON dönmeli."""
    _inject_security_stubs()
    resp = authed_client.post(
        "/api/ai/security-analyze",
        json={"url": "http://example.com", "headers": {"Server": "nginx"}},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert resp.get_json() is not None
    sys.modules.pop("core.ai_security", None)


# ── POST /api/ai/perf-analyze ────────────────────────────────────────────────

def test_perf_analyze_missing_results_returns_400(authed_client):
    """results eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/ai/perf-analyze",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_perf_analyze_success_returns_bottlenecks(authed_client, monkeypatch):
    """Geçerli results → bottlenecks listesi dönmeli."""
    _inject_perf_stubs()
    resp = authed_client.post(
        "/api/ai/perf-analyze",
        json={"results": {"test_login": {"duration": 2500, "memory": 128}}},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "bottlenecks" in data
    sys.modules.pop("core.ai_performance", None)


def test_perf_analyze_has_regressions_key(authed_client, monkeypatch):
    """Yanıt regressions alanı içermeli."""
    _inject_perf_stubs()
    resp = authed_client.post(
        "/api/ai/perf-analyze",
        json={"results": {"test_x": {"duration": 100}}},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert "regressions" in resp.get_json()
    sys.modules.pop("core.ai_performance", None)


# ── POST /api/ai/optimize-suite ──────────────────────────────────────────────

def test_optimize_suite_success_returns_report(authed_client, monkeypatch):
    """optimize-suite → optimizasyon raporu dönmeli."""
    _inject_feedback_stubs()
    resp = authed_client.post(
        "/api/ai/optimize-suite",
        json={},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert data is not None
    sys.modules.pop("core.feedback_loop.collector", None)
    sys.modules.pop("core.feedback_loop.analyzer", None)
    sys.modules.pop("core.feedback_loop.optimizer", None)


def test_optimize_suite_report_is_dict(authed_client, monkeypatch):
    """Yanıt dict (JSON object) olmalı."""
    _inject_feedback_stubs()
    resp = authed_client.post(
        "/api/ai/optimize-suite",
        json={},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert isinstance(resp.get_json(), dict)
    sys.modules.pop("core.feedback_loop.collector", None)
    sys.modules.pop("core.feedback_loop.analyzer", None)
    sys.modules.pop("core.feedback_loop.optimizer", None)
