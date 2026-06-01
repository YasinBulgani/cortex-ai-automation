"""
ai_analysis_routes blueprint testleri — 22 test.

Kapsanan endpoint'ler:
  POST /api/ai/analyze-anomaly
  GET  /api/ai/flaky-report
  POST /api/ai/coverage-gaps
  POST /api/ai/prioritize
  GET  /api/ai/stats
  POST /api/ai/analyze-assertions
  POST /api/ai/security-scan
"""
from __future__ import annotations

import sys
import types
import pytest
from unittest.mock import MagicMock
from flask import Flask


# ---------------------------------------------------------------------------
# sys.modules stubs — blueprint import edilmeden ÖNCE kurulmalı
# ---------------------------------------------------------------------------

def _make_service_stubs(is_feature_enabled_return=True, llm_available=True):
    """services paketi ve alt modülleri için stub'lar üretir."""

    # ---- services (top-level) ----
    svc = types.ModuleType("services")
    svc.is_feature_enabled = MagicMock(return_value=is_feature_enabled_return)
    gateway = MagicMock()
    gateway.available = llm_available
    gateway.stats = MagicMock()
    gateway.stats.to_dict = MagicMock(return_value={"calls": 5, "tokens": 100})
    svc.get_llm_gateway = MagicMock(return_value=gateway)

    # ---- services.anomaly_detector ----
    anomaly_mod = types.ModuleType("services.anomaly_detector")
    anomaly_obj = MagicMock()
    anomaly_result = MagicMock()
    anomaly_result.to_dict = MagicMock(return_value={"type": "spike"})
    anomaly_obj.analyze_test_run = MagicMock(return_value=[anomaly_result])
    anomaly_mod.AnomalyDetector = MagicMock(return_value=anomaly_obj)

    # ---- services.flaky_detector ----
    flaky_mod = types.ModuleType("services.flaky_detector")
    flaky_obj = MagicMock()
    flaky_result_q = MagicMock()
    flaky_result_q.recommendation = "quarantine"
    flaky_result_q.to_dict = MagicMock(return_value={"test": "test_a", "recommendation": "quarantine"})
    flaky_result_ok = MagicMock()
    flaky_result_ok.recommendation = "ok"
    flaky_result_ok.to_dict = MagicMock(return_value={"test": "test_b", "recommendation": "ok"})
    flaky_obj.analyze_all = MagicMock(return_value=[flaky_result_q, flaky_result_ok])
    flaky_mod.FlakyDetector = MagicMock(return_value=flaky_obj)

    # ---- services.coverage_analyzer ----
    coverage_mod = types.ModuleType("services.coverage_analyzer")
    coverage_obj = MagicMock()
    gap = MagicMock()
    gap.to_dict = MagicMock(return_value={"module": "auth", "coverage": 40})
    coverage_obj.analyze = MagicMock(return_value=[gap])
    coverage_mod.CoverageAnalyzer = MagicMock(return_value=coverage_obj)

    # ---- services.test_prioritizer ----
    prioritizer_mod = types.ModuleType("services.test_prioritizer")
    prioritizer_obj = MagicMock()
    prio_result = MagicMock()
    prio_result.to_dict = MagicMock(return_value={"ranked": ["test_a"]})
    prioritizer_obj.prioritize = MagicMock(return_value=prio_result)
    prioritizer_mod.TestPrioritizer = MagicMock(return_value=prioritizer_obj)

    # ---- services.assertion_engine ----
    assertion_mod = types.ModuleType("services.assertion_engine")
    assertion_obj = MagicMock()
    suggestion = MagicMock()
    suggestion.to_dict = MagicMock(return_value={"line": 10, "suggestion": "assert status == 200"})
    assertion_obj.analyze_file = MagicMock(return_value=[suggestion])
    assertion_mod.AssertionEngine = MagicMock(return_value=assertion_obj)

    # ---- services.security_scanner ----
    security_mod = types.ModuleType("services.security_scanner")
    scanner_obj = MagicMock()
    finding = MagicMock()
    finding.to_dict = MagicMock(return_value={"severity": "high", "url": "/login"})
    scanner_obj.quick_scan = MagicMock(return_value=[finding])
    scanner_obj.api_scan = MagicMock(return_value=[finding])
    scanner_obj.save_report = MagicMock()
    security_mod.SecurityScanner = MagicMock(return_value=scanner_obj)

    return {
        "services": svc,
        "services.anomaly_detector": anomaly_mod,
        "services.flaky_detector": flaky_mod,
        "services.coverage_analyzer": coverage_mod,
        "services.test_prioritizer": prioritizer_mod,
        "services.assertion_engine": assertion_mod,
        "services.security_scanner": security_mod,
    }


def _install_stubs(stubs: dict):
    for name, mod in stubs.items():
        sys.modules[name] = mod


def _remove_stubs(stubs: dict):
    for name in stubs:
        sys.modules.pop(name, None)
    sys.modules.pop("routes.ai_analysis_routes", None)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def client():
    """Feature açık, LLM mevcut — happy-path istemci."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_analysis_routes import ai_analysis_bp
        app = Flask(__name__)
        app.register_blueprint(ai_analysis_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


@pytest.fixture()
def client_feature_off():
    """Feature devre dışı — 503 beklenir."""
    stubs = _make_service_stubs(is_feature_enabled_return=False, llm_available=True)
    _install_stubs(stubs)
    try:
        from routes.ai_analysis_routes import ai_analysis_bp
        app = Flask(__name__)
        app.register_blueprint(ai_analysis_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


@pytest.fixture()
def client_llm_off():
    """Feature açık, LLM mevcut değil."""
    stubs = _make_service_stubs(is_feature_enabled_return=True, llm_available=False)
    _install_stubs(stubs)
    try:
        from routes.ai_analysis_routes import ai_analysis_bp
        app = Flask(__name__)
        app.register_blueprint(ai_analysis_bp)
        app.config["TESTING"] = True
        yield app.test_client()
    finally:
        _remove_stubs(stubs)


# ---------------------------------------------------------------------------
# /api/ai/analyze-anomaly  — POST
# ---------------------------------------------------------------------------

class TestAnalyzeAnomaly:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/analyze-anomaly", json={})
        assert resp.status_code == 503

    def test_feature_disabled_error_in_body(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/analyze-anomaly", json={})
        data = resp.get_json()
        assert "error" in data

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/analyze-anomaly", json={"run_id": "abc"})
        assert resp.status_code == 200

    def test_success_contains_anomaly_count(self, client):
        resp = client.post("/api/ai/analyze-anomaly", json={"run_id": "abc"})
        data = resp.get_json()
        assert "anomaly_count" in data
        assert data["anomaly_count"] == 1

    def test_success_contains_anomalies_list(self, client):
        resp = client.post("/api/ai/analyze-anomaly", json={})
        data = resp.get_json()
        assert "anomalies" in data
        assert isinstance(data["anomalies"], list)

    def test_service_exception_returns_500(self, client):
        sys.modules["services.anomaly_detector"].AnomalyDetector.return_value.analyze_test_run.side_effect = RuntimeError("boom")
        resp = client.post("/api/ai/analyze-anomaly", json={})
        assert resp.status_code == 500
        sys.modules["services.anomaly_detector"].AnomalyDetector.return_value.analyze_test_run.side_effect = None

    def test_service_exception_error_in_body(self, client):
        sys.modules["services.anomaly_detector"].AnomalyDetector.return_value.analyze_test_run.side_effect = ValueError("bad data")
        resp = client.post("/api/ai/analyze-anomaly", json={})
        data = resp.get_json()
        assert "error" in data
        sys.modules["services.anomaly_detector"].AnomalyDetector.return_value.analyze_test_run.side_effect = None


# ---------------------------------------------------------------------------
# /api/ai/flaky-report  — GET
# ---------------------------------------------------------------------------

class TestFlakyReport:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.get("/api/ai/flaky-report")
        assert resp.status_code == 503

    def test_success_returns_200(self, client):
        resp = client.get("/api/ai/flaky-report")
        assert resp.status_code == 200

    def test_success_contains_total_analyzed(self, client):
        resp = client.get("/api/ai/flaky-report")
        data = resp.get_json()
        assert "total_analyzed" in data
        assert data["total_analyzed"] == 2

    def test_success_contains_quarantined_count(self, client):
        resp = client.get("/api/ai/flaky-report")
        data = resp.get_json()
        assert "quarantined_count" in data
        assert data["quarantined_count"] == 1

    def test_success_contains_tests_list(self, client):
        resp = client.get("/api/ai/flaky-report")
        data = resp.get_json()
        assert "tests" in data
        assert isinstance(data["tests"], list)


# ---------------------------------------------------------------------------
# /api/ai/coverage-gaps  — POST
# ---------------------------------------------------------------------------

class TestCoverageGaps:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/coverage-gaps", json={})
        assert resp.status_code == 503

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/coverage-gaps", json={})
        assert resp.status_code == 200

    def test_success_contains_gap_count(self, client):
        resp = client.post("/api/ai/coverage-gaps", json={})
        data = resp.get_json()
        assert "gap_count" in data

    def test_suggestions_llm_unavailable_returns_503(self, client_llm_off):
        resp = client_llm_off.post("/api/ai/coverage-gaps", json={"generate_suggestions": True})
        assert resp.status_code == 503


# ---------------------------------------------------------------------------
# /api/ai/prioritize  — POST
# ---------------------------------------------------------------------------

class TestPrioritizeTests:
    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/prioritize", json={"git_diff": "diff --git a/test.py b/test.py"})
        assert resp.status_code == 200

    def test_success_contains_ranked(self, client):
        resp = client.post("/api/ai/prioritize", json={})
        data = resp.get_json()
        assert "ranked" in data


# ---------------------------------------------------------------------------
# /api/ai/stats  — GET
# ---------------------------------------------------------------------------

class TestLlmStats:
    def test_success_returns_200(self, client):
        resp = client.get("/api/ai/stats")
        assert resp.status_code == 200

    def test_success_contains_stats_fields(self, client):
        resp = client.get("/api/ai/stats")
        data = resp.get_json()
        assert "calls" in data or "tokens" in data


# ---------------------------------------------------------------------------
# /api/ai/analyze-assertions  — POST
# ---------------------------------------------------------------------------

class TestAnalyzeAssertions:
    def test_llm_unavailable_returns_503(self, client_llm_off):
        resp = client_llm_off.post("/api/ai/analyze-assertions", json={"file_path": "tests/test_login.py"})
        assert resp.status_code == 503

    def test_missing_file_path_returns_400(self, client):
        resp = client.post("/api/ai/analyze-assertions", json={})
        assert resp.status_code == 400

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/analyze-assertions", json={"file_path": "tests/test_login.py"})
        assert resp.status_code == 200

    def test_success_contains_suggestion_count(self, client):
        resp = client.post("/api/ai/analyze-assertions", json={"file_path": "tests/test_login.py"})
        data = resp.get_json()
        assert "suggestion_count" in data
        assert data["suggestion_count"] == 1


# ---------------------------------------------------------------------------
# /api/ai/security-scan  — POST
# ---------------------------------------------------------------------------

class TestSecurityScan:
    def test_feature_disabled_returns_503(self, client_feature_off):
        resp = client_feature_off.post("/api/ai/security-scan", json={})
        assert resp.status_code == 503

    def test_success_returns_200(self, client):
        resp = client.post("/api/ai/security-scan", json={"target_url": "http://localhost:8000"})
        assert resp.status_code == 200

    def test_success_contains_finding_count(self, client):
        resp = client.post("/api/ai/security-scan", json={})
        data = resp.get_json()
        assert "finding_count" in data

    def test_success_contains_scan_type(self, client):
        resp = client.post("/api/ai/security-scan", json={"scan_type": "quick"})
        data = resp.get_json()
        assert data.get("scan_type") == "quick"
