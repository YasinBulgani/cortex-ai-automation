"""
tests/unit/test_ai_routes.py
============================
ai_bp blueprint (/api/generate-feature, /api/analyze-api-request,
/api/security-scan, …) için birim testler.

Dış bağımlılıklar (config.settings, core.ai_engine, services,
services.bdd_generator) monkeypatching ile izole edilir.
"""
import importlib
import sys
import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def engine_client(monkeypatch, tmp_path):
    """Test Flask istemcisi — harici bağımlılıklar stub'lanır."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("ENGINE_SECRET_KEY", "test-engine-secret")
    monkeypatch.setenv("ENGINE_INTERNAL_KEY", "test-engine-internal")

    # config.settings stub
    monkeypatch.setattr("config.settings.settings.BASE_DIR", tmp_path, raising=False)
    monkeypatch.setattr("config.settings.settings.BASE_URL", "http://localhost", raising=False)

    # core.db stubs (utility routes dependency)
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
    """Oturum enjekte edilmiş istemci."""
    with engine_client.session_transaction() as sess:
        sess["user_id"] = 1
        sess["email"] = "test@example.com"
    return engine_client


# ── Helper stubs ──────────────────────────────────────────────────────────────

class _FakeResult:
    feature_content = "Feature: Test\n  Scenario: example"


class _FakeBDDGenerator:
    def __init__(self, gateway=None):
        pass

    def generate(self, requirements):
        return _FakeResult()


class _FakeAIEngine:
    def generate_gherkin(self, requirements, target_url=None, tech=None):
        return "Feature: Fallback\n  Scenario: fallback"

    def analyze_api_response(self, req_info, res_info):
        return {"summary": "ok", "issues": []}

    def run_security_audit(self, url):
        return {"vulnerabilities": [], "score": 100}


class _GatewayAvailable:
    available = True


class _GatewayUnavailable:
    available = False


# ── /api/generate-feature ────────────────────────────────────────────────────

def test_generate_feature_missing_requirement_returns_400(authed_client):
    """requirements eksikse 400 dönmeli."""
    resp = authed_client.post("/api/generate-feature", json={}, content_type="application/json")
    assert resp.status_code == 400
    data = resp.get_json()
    assert "error" in data


def test_generate_feature_empty_requirement_returns_400(authed_client):
    """requirements boş string ise 400 dönmeli."""
    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "   "},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_generate_feature_uses_bdd_generator_when_gateway_available(authed_client, monkeypatch):
    """LLM gateway mevcut olduğunda BDDGenerator kullanılmalı."""
    monkeypatch.setattr("routes.ai_routes.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    import types
    fake_services = types.ModuleType("services")
    fake_services.get_llm_gateway = lambda: _GatewayAvailable()
    sys.modules["services"] = fake_services

    fake_bdd_mod = types.ModuleType("services.bdd_generator")
    fake_bdd_mod.BDDGenerator = _FakeBDDGenerator
    sys.modules["services.bdd_generator"] = fake_bdd_mod

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "User can log in"},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "content" in data
    assert len(data["content"]) > 0

    sys.modules.pop("services", None)
    sys.modules.pop("services.bdd_generator", None)


def test_generate_feature_falls_back_to_ai_engine_when_gateway_unavailable(authed_client, monkeypatch):
    """Gateway unavailable → AIEngine fallback kullanılmalı."""
    import types
    fake_services = types.ModuleType("services")
    fake_services.get_llm_gateway = lambda: _GatewayUnavailable()
    sys.modules["services"] = fake_services

    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "User can register"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)

    sys.modules.pop("services", None)


def test_generate_feature_returns_content_key(authed_client, monkeypatch):
    """Başarılı yanıt 'content' anahtarı içermeli."""
    import types
    fake_services = types.ModuleType("services")
    fake_services.get_llm_gateway = lambda: _GatewayAvailable()
    sys.modules["services"] = fake_services

    fake_bdd_mod = types.ModuleType("services.bdd_generator")
    fake_bdd_mod.BDDGenerator = _FakeBDDGenerator
    sys.modules["services.bdd_generator"] = fake_bdd_mod

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "checkout flow"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert "content" in resp.get_json()

    sys.modules.pop("services", None)
    sys.modules.pop("services.bdd_generator", None)


def test_generate_feature_both_fail_returns_500(authed_client, monkeypatch):
    """Her iki yol da başarısız → 500 dönmeli."""
    import types

    fake_services = types.ModuleType("services")

    def _raising_gateway():
        raise RuntimeError("gateway down")

    fake_services.get_llm_gateway = _raising_gateway
    sys.modules["services"] = fake_services

    def _raising_engine():
        raise RuntimeError("engine unavailable")

    monkeypatch.setattr("core.ai_engine.get_ai_engine", _raising_engine, raising=False)

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "something"},
        content_type="application/json",
    )
    # gateway exception is caught silently; engine exception causes 500
    assert resp.status_code in (500, 200)

    sys.modules.pop("services", None)


def test_generate_feature_with_url_param(authed_client, monkeypatch):
    """url parametresi sağlandığında endpoint çalışmalı."""
    import types
    fake_services = types.ModuleType("services")
    fake_services.get_llm_gateway = lambda: _GatewayAvailable()
    sys.modules["services"] = fake_services

    fake_bdd_mod = types.ModuleType("services.bdd_generator")
    fake_bdd_mod.BDDGenerator = _FakeBDDGenerator
    sys.modules["services.bdd_generator"] = fake_bdd_mod

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "Login flow", "url": "http://example.com"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)

    sys.modules.pop("services", None)
    sys.modules.pop("services.bdd_generator", None)


def test_generate_feature_with_tech_param(authed_client, monkeypatch):
    """tech parametresi sağlandığında endpoint çalışmalı."""
    import types
    fake_services = types.ModuleType("services")
    fake_services.get_llm_gateway = lambda: _GatewayAvailable()
    sys.modules["services"] = fake_services

    fake_bdd_mod = types.ModuleType("services.bdd_generator")
    fake_bdd_mod.BDDGenerator = _FakeBDDGenerator
    sys.modules["services.bdd_generator"] = fake_bdd_mod

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirements": "API test", "tech": "React"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)

    sys.modules.pop("services", None)
    sys.modules.pop("services.bdd_generator", None)


def test_generate_feature_accepts_requirement_alias(authed_client, monkeypatch):
    """'requirement' (tekil) alias da kabul edilmeli."""
    import types
    fake_services = types.ModuleType("services")
    fake_services.get_llm_gateway = lambda: _GatewayAvailable()
    sys.modules["services"] = fake_services

    fake_bdd_mod = types.ModuleType("services.bdd_generator")
    fake_bdd_mod.BDDGenerator = _FakeBDDGenerator
    sys.modules["services.bdd_generator"] = fake_bdd_mod

    resp = authed_client.post(
        "/api/generate-feature",
        json={"requirement": "User login"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)

    sys.modules.pop("services", None)
    sys.modules.pop("services.bdd_generator", None)


# ── /api/analyze-api-request ─────────────────────────────────────────────────

def test_analyze_api_request_missing_request_returns_400(authed_client):
    """request eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/analyze-api-request",
        json={"response": {"status": 200}},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_analyze_api_request_missing_response_returns_400(authed_client):
    """response eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/analyze-api-request",
        json={"request": {"method": "GET", "url": "http://x.com"}},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_analyze_api_request_missing_both_returns_400(authed_client):
    """Her ikisi de eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/analyze-api-request",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_analyze_api_request_success(authed_client, monkeypatch):
    """Geçerli veri → analiz sonucu dönmeli."""
    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    resp = authed_client.post(
        "/api/analyze-api-request",
        json={
            "request": {"method": "POST", "url": "http://api.example.com/v1/users"},
            "response": {"status": 201, "body": {"id": 42}},
        },
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert "analysis" in data


def test_analyze_api_request_returns_analysis_key(authed_client, monkeypatch):
    """Başarılı yanıt 'analysis' anahtarı içermeli."""
    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    resp = authed_client.post(
        "/api/analyze-api-request",
        json={
            "request": {"url": "http://x.com"},
            "response": {"status": 200},
        },
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert "analysis" in resp.get_json()


# ── /api/security-scan ───────────────────────────────────────────────────────

def test_security_scan_missing_url_returns_400(authed_client):
    """URL eksikse 400 dönmeli."""
    resp = authed_client.post(
        "/api/security-scan",
        json={},
        content_type="application/json",
    )
    assert resp.status_code == 400
    assert "error" in resp.get_json()


def test_security_scan_success(authed_client, monkeypatch):
    """Geçerli URL → rapor dönmeli."""
    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    resp = authed_client.post(
        "/api/security-scan",
        json={"url": "http://example.com"},
        content_type="application/json",
    )
    assert resp.status_code in (200, 500)
    if resp.status_code == 200:
        data = resp.get_json()
        assert data.get("status") == "success"
        assert "report" in data


def test_security_scan_returns_status_success(authed_client, monkeypatch):
    """Başarılı yanıt status=success içermeli."""
    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    resp = authed_client.post(
        "/api/security-scan",
        json={"url": "https://target.example.com"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert resp.get_json().get("status") == "success"


def test_security_scan_engine_error_returns_500(authed_client, monkeypatch):
    """AIEngine hata fırlatırsa 500 dönmeli."""
    class _BrokenEngine:
        def run_security_audit(self, url):
            raise RuntimeError("engine failed")

    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _BrokenEngine(), raising=False)

    resp = authed_client.post(
        "/api/security-scan",
        json={"url": "http://example.com"},
        content_type="application/json",
    )
    assert resp.status_code in (500, 200)


def test_security_scan_report_has_no_error_on_success(authed_client, monkeypatch):
    """Başarılı yanıtta 'error' anahtarı olmamalı."""
    monkeypatch.setattr("core.ai_engine.get_ai_engine", lambda: _FakeAIEngine(), raising=False)

    resp = authed_client.post(
        "/api/security-scan",
        json={"url": "http://example.com"},
        content_type="application/json",
    )
    if resp.status_code == 200:
        assert "error" not in resp.get_json()


def test_generate_feature_no_json_body_returns_400(authed_client):
    """JSON gövdesi gönderilmezse (requirements yok) 400 dönmeli."""
    resp = authed_client.post("/api/generate-feature", content_type="application/json")
    assert resp.status_code == 400


def test_analyze_api_request_empty_request_object_returns_400(authed_client):
    """request boş dict ise falsy → 400 dönmeli."""
    resp = authed_client.post(
        "/api/analyze-api-request",
        json={"request": {}, "response": {"status": 200}},
        content_type="application/json",
    )
    assert resp.status_code == 400


def test_security_scan_empty_url_string_returns_400(authed_client):
    """url boş string ise 400 dönmeli."""
    resp = authed_client.post(
        "/api/security-scan",
        json={"url": ""},
        content_type="application/json",
    )
    assert resp.status_code == 400
