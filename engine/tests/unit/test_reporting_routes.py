"""
tests/unit/test_reporting_routes.py
=====================================
reporting_routes.py (reporting_bp) HTTP katmanı testleri.

Blueprint: reporting_bp  —  url_prefix=/api/reporting
Imports from: core.python.reporting_engine, core.python.analytics_engine

Kapsanan endpointler:
  GET  /api/reporting/health
  POST /api/reporting/generate-report
  POST /api/reporting/record-run
  POST /api/reporting/record-failure
  GET  /api/reporting/analytics/trends
  GET  /api/reporting/analytics/risk-assessment
  GET  /api/reporting/analytics/predictions
  GET  /api/reporting/analytics/performance
  GET  /api/reporting/analytics/report

Fixture stratejisi:
  core.python.reporting_engine ve core.python.analytics_engine sys.modules
  üzerinden stub'lanır; yalnızca reporting_routes blueprint'i yüklenir.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def reporting_client(monkeypatch):
    """
    Sadece reporting_routes (reporting_bp) blueprint'ini barındıran
    minimal Flask test istemcisi.

    core.python.reporting_engine ve core.python.analytics_engine stub'lanır;
    başka route modülleri yüklenmez.
    """
    # ── core.python.reporting_engine stub ────────────────────────────────
    fake_report_engine = MagicMock()

    fake_test_run_cls = MagicMock()
    fake_test_run_instance = MagicMock()
    fake_test_run_instance.run_id = "run-001"
    fake_test_run_instance.total_tests = 10
    fake_test_run_instance.passed = 9
    fake_test_run_instance.failed = 1
    fake_test_run_instance.skipped = 0
    fake_test_run_instance.success_rate = 90.0
    fake_test_run_instance.duration_ms = 5000
    fake_test_run_cls.return_value = fake_test_run_instance

    fake_generator = MagicMock()
    fake_generator.generate_report.return_value = {"html": "/tmp/report.html", "json": "/tmp/report.json"}
    fake_report_engine.get_report_generator = MagicMock(return_value=fake_generator)
    fake_report_engine.TestRun = fake_test_run_cls
    fake_report_engine.TestCase = MagicMock()
    fake_report_engine.TestStep = MagicMock()
    fake_report_engine.ReportFormat = MagicMock()

    monkeypatch.setitem(sys.modules, "core", MagicMock())
    monkeypatch.setitem(sys.modules, "core.python", MagicMock())
    monkeypatch.setitem(sys.modules, "core.python.reporting_engine", fake_report_engine)

    # ── core.python.analytics_engine stub ────────────────────────────────
    fake_analytics_engine_mod = MagicMock()
    fake_analytics = MagicMock()

    fake_trend = MagicMock()
    fake_trend.current_value = 90.0
    fake_trend.previous_value = 85.0
    fake_trend.direction = "up"
    fake_trend.change_percentage = 5.88
    fake_trend.data_points = []
    fake_analytics.analyze_trends.return_value = {"success_rate": fake_trend}

    fake_risk = MagicMock()
    fake_risk.level = "low"
    fake_risk.score = 10.0
    fake_risk.failing_tests = []
    fake_risk.unstable_tests = []
    fake_risk.regression_risk = 5.0
    fake_risk.recommendations = ["All good"]
    fake_analytics.assess_risk.return_value = fake_risk

    fake_analytics.predict_failures.return_value = []
    fake_analytics.get_performance_trends.return_value = {"avg_duration_ms": 150}

    fake_report_obj = MagicMock()
    fake_report_obj.run_id = "analytics-run-002"
    fake_report_obj.timestamp = "2024-06-01T12:00:00"
    fake_report_obj.risk_assessment = fake_risk
    fake_report_obj.trends = {}
    fake_analytics.generate_analytics_report.return_value = fake_report_obj
    fake_analytics.export_analytics.return_value = "/tmp/analytics_export.json"

    fake_analytics_engine_mod.get_analytics_engine = MagicMock(return_value=fake_analytics)
    monkeypatch.setitem(sys.modules, "core.python.analytics_engine", fake_analytics_engine_mod)

    # ── blueprint modülünü temizle ve yükle ──────────────────────────────
    sys.modules.pop("routes.reporting_routes", None)
    sys.modules.pop("routes", None)

    import importlib
    bp_module = importlib.import_module("routes.reporting_routes")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(bp_module.reporting_bp)

    with app.test_client() as client:
        yield client


# ── /api/reporting/health ─────────────────────────────────────────────────────

class TestHealthEndpoint:
    """GET /api/reporting/health testleri."""

    def test_health_returns_200(self, reporting_client):
        """Health endpoint → 200 dönmeli."""
        response = reporting_client.get("/api/reporting/health")
        assert response.status_code == 200

    def test_health_response_fields(self, reporting_client):
        """Response: status=healthy, service, version alanları olmalı."""
        data = reporting_client.get("/api/reporting/health").get_json()
        assert data.get("status") == "healthy"
        assert "service" in data
        assert "version" in data


# ── /api/reporting/generate-report ───────────────────────────────────────────

class TestGenerateReportEndpoint:
    """POST /api/reporting/generate-report testleri."""

    VALID_TEST_RUN = {
        "run_id": "run-999",
        "environment": "production",
        "browser": "firefox",
        "start_time": "2024-06-01T08:00:00",
        "end_time": "2024-06-01T08:20:00",
        "total_tests": 20,
        "passed": 18,
        "failed": 2,
        "skipped": 0,
        "duration_ms": 1200000,
        "test_cases": [],
    }

    def test_missing_test_run_returns_400(self, reporting_client):
        """`test_run` gönderilmeden çağırma → 400 dönmeli."""
        response = reporting_client.post(
            "/api/reporting/generate-report",
            json={"formats": ["json"]},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_empty_body_returns_error(self, reporting_client):
        """Boş JSON body → 400 veya 500 dönmeli (test_run yok)."""
        response = reporting_client.post(
            "/api/reporting/generate-report",
            json={},
            content_type="application/json",
        )
        assert response.status_code in (400, 500)

    def test_valid_payload_returns_200(self, reporting_client):
        """Geçerli test_run → 200 ve success=True dönmeli."""
        response = reporting_client.post(
            "/api/reporting/generate-report",
            json={"test_run": self.VALID_TEST_RUN, "formats": ["json"]},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True

    def test_response_contains_summary(self, reporting_client):
        """Response'da `summary` ve beklenen alt anahtarlar olmalı."""
        response = reporting_client.post(
            "/api/reporting/generate-report",
            json={"test_run": self.VALID_TEST_RUN},
            content_type="application/json",
        )
        assert response.status_code == 200
        summary = response.get_json().get("summary", {})
        for key in ("total_tests", "passed", "failed", "skipped", "success_rate", "duration_seconds"):
            assert key in summary, f"summary içinde '{key}' eksik"

    def test_response_contains_run_id_and_reports(self, reporting_client):
        """Response'da `run_id` ve `reports` alanları olmalı."""
        response = reporting_client.post(
            "/api/reporting/generate-report",
            json={"test_run": self.VALID_TEST_RUN},
            content_type="application/json",
        )
        data = response.get_json()
        assert "run_id" in data
        assert "reports" in data


# ── /api/reporting/record-run ────────────────────────────────────────────────

class TestRecordRunEndpoint:
    """POST /api/reporting/record-run testleri."""

    def test_missing_run_id_returns_400(self, reporting_client):
        """`run_id` olmadan → 400 dönmeli."""
        response = reporting_client.post(
            "/api/reporting/record-run",
            json={"environment": "staging", "total_tests": 5},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "error" in response.get_json()

    def test_valid_run_returns_200(self, reporting_client):
        """Geçerli run_id → 200, success=True ve run_id dönmeli."""
        payload = {
            "run_id": "run-xyz",
            "environment": "staging",
            "browser": "chromium",
            "total_tests": 10,
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "duration_ms": 30000,
        }
        response = reporting_client.post(
            "/api/reporting/record-run",
            json=payload,
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert data.get("run_id") == "run-xyz"

    def test_success_rate_present_in_response(self, reporting_client):
        """Response'da `success_rate` alanı olmalı."""
        response = reporting_client.post(
            "/api/reporting/record-run",
            json={"run_id": "run-abc", "total_tests": 4, "passed": 3, "failed": 1},
            content_type="application/json",
        )
        data = response.get_json()
        assert "success_rate" in data


# ── /api/reporting/record-failure ────────────────────────────────────────────

class TestRecordFailureEndpoint:
    """POST /api/reporting/record-failure testleri."""

    def test_missing_test_name_returns_400(self, reporting_client):
        """`test_name` eksik → 400 dönmeli."""
        response = reporting_client.post(
            "/api/reporting/record-failure",
            json={"run_id": "run-001"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_missing_run_id_returns_400(self, reporting_client):
        """`run_id` eksik → 400 dönmeli."""
        response = reporting_client.post(
            "/api/reporting/record-failure",
            json={"test_name": "test_checkout"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_valid_failure_returns_200(self, reporting_client):
        """Geçerli payload → 200 ve success=True dönmeli."""
        response = reporting_client.post(
            "/api/reporting/record-failure",
            json={
                "test_name": "test_payment_flow",
                "run_id": "run-777",
                "error_message": "Timeout waiting for element",
                "duration_ms": 3000,
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert data.get("test_name") == "test_payment_flow"


# ── /api/reporting/analytics/trends ──────────────────────────────────────────

class TestTrendsEndpoint:
    """GET /api/reporting/analytics/trends testleri."""

    def test_trends_returns_200(self, reporting_client):
        response = reporting_client.get("/api/reporting/analytics/trends")
        assert response.status_code == 200

    def test_trends_default_lookback(self, reporting_client):
        """Varsayılan lookback_hours 24 olmalı."""
        data = reporting_client.get("/api/reporting/analytics/trends").get_json()
        assert data.get("lookback_hours") == 24
        assert "trends" in data

    def test_trends_custom_hours(self, reporting_client):
        """hours=12 → lookback_hours=12 dönmeli."""
        data = reporting_client.get("/api/reporting/analytics/trends?hours=12").get_json()
        assert data.get("lookback_hours") == 12


# ── /api/reporting/analytics/risk-assessment ─────────────────────────────────

class TestRiskAssessmentEndpoint:
    """GET /api/reporting/analytics/risk-assessment testleri."""

    def test_risk_assessment_returns_200(self, reporting_client):
        response = reporting_client.get("/api/reporting/analytics/risk-assessment")
        assert response.status_code == 200

    def test_risk_assessment_has_all_fields(self, reporting_client):
        """risk_assessment içinde level, score, recommendations alanları olmalı."""
        data = reporting_client.get("/api/reporting/analytics/risk-assessment").get_json()
        assert data.get("success") is True
        risk = data.get("risk_assessment", {})
        for key in ("level", "score", "failing_tests", "unstable_tests", "regression_risk", "recommendations"):
            assert key in risk, f"risk_assessment içinde '{key}' eksik"


# ── /api/reporting/analytics/predictions ─────────────────────────────────────

class TestPredictionsEndpoint:
    """GET /api/reporting/analytics/predictions testleri."""

    def test_predictions_returns_200(self, reporting_client):
        response = reporting_client.get("/api/reporting/analytics/predictions")
        assert response.status_code == 200

    def test_predictions_response_shape(self, reporting_client):
        """Response: success, predictions, lookback_days olmalı."""
        data = reporting_client.get("/api/reporting/analytics/predictions").get_json()
        assert data.get("success") is True
        assert "predictions" in data
        assert "lookback_days" in data


# ── /api/reporting/analytics/performance ─────────────────────────────────────

class TestPerformanceTrendsEndpoint:
    """GET /api/reporting/analytics/performance testleri."""

    def test_performance_returns_200(self, reporting_client):
        response = reporting_client.get("/api/reporting/analytics/performance")
        assert response.status_code == 200

    def test_performance_response_shape(self, reporting_client):
        """Response: success=True, lookback_hours, performance anahtarları olmalı."""
        data = reporting_client.get("/api/reporting/analytics/performance").get_json()
        assert data.get("success") is True
        assert "lookback_hours" in data
        assert "performance" in data


# ── /api/reporting/analytics/report ──────────────────────────────────────────

class TestAnalyticsReportEndpoint:
    """GET /api/reporting/analytics/report testleri."""

    def test_analytics_report_returns_200(self, reporting_client):
        response = reporting_client.get("/api/reporting/analytics/report")
        assert response.status_code == 200

    def test_analytics_report_shape(self, reporting_client):
        """Response: success, report_id, timestamp, risk_level, recommendations olmalı."""
        data = reporting_client.get("/api/reporting/analytics/report").get_json()
        assert data.get("success") is True
        for key in ("report_id", "timestamp", "risk_level", "recommendations", "trends_summary"):
            assert key in data, f"Response içinde '{key}' eksik"
