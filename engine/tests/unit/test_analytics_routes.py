"""
tests/unit/test_analytics_routes.py
=====================================
analytics_routes.py (reporting_bp) HTTP katmanı testleri.

Blueprint: reporting_bp  —  url_prefix=/api/reporting
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
  core.reporting_engine ve core.analytics_engine sys.modules üzerinden
  stub'lanır; yalnızca analytics_routes blueprint'i yüklenir.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask


# ── Fixture ───────────────────────────────────────────────────────────────────

@pytest.fixture
def analytics_client(monkeypatch):
    """
    Sadece analytics_routes (reporting_bp) blueprint'ini barındıran
    minimal Flask test istemcisi.
    """
    # ── core.reporting_engine stub ────────────────────────────────────────
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

    monkeypatch.setitem(sys.modules, "core.reporting_engine", fake_report_engine)

    # ── core.analytics_engine stub ────────────────────────────────────────
    fake_analytics_engine_mod = MagicMock()

    fake_analytics = MagicMock()

    # trends mock
    fake_trend = MagicMock()
    fake_trend.current_value = 90.0
    fake_trend.previous_value = 85.0
    fake_trend.direction = "up"
    fake_trend.change_percentage = 5.88
    fake_trend.data_points = []
    fake_analytics.analyze_trends.return_value = {"success_rate": fake_trend}

    # risk mock
    fake_risk = MagicMock()
    fake_risk.level = "low"
    fake_risk.score = 10.0
    fake_risk.failing_tests = []
    fake_risk.unstable_tests = []
    fake_risk.regression_risk = 5.0
    fake_risk.recommendations = ["Keep it up"]
    fake_analytics.assess_risk.return_value = fake_risk

    # predictions mock
    fake_analytics.predict_failures.return_value = []

    # performance mock
    fake_analytics.get_performance_trends.return_value = {"avg_duration_ms": 200}

    # analytics report mock
    fake_report_obj = MagicMock()
    fake_report_obj.run_id = "analytics-run-001"
    fake_report_obj.timestamp = "2024-01-01T10:00:00"
    fake_report_obj.risk_assessment = fake_risk
    fake_report_obj.trends = {}
    fake_analytics.generate_analytics_report.return_value = fake_report_obj
    fake_analytics.export_analytics.return_value = "/tmp/analytics.json"

    fake_analytics_engine_mod.get_analytics_engine = MagicMock(return_value=fake_analytics)
    monkeypatch.setitem(sys.modules, "core.analytics_engine", fake_analytics_engine_mod)

    # ── blueprint modülünü temizle ve yükle ──────────────────────────────
    sys.modules.pop("routes.analytics_routes", None)
    sys.modules.pop("routes", None)

    import importlib
    bp_module = importlib.import_module("routes.analytics_routes")

    app = Flask(__name__)
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    app.register_blueprint(bp_module.reporting_bp)

    with app.test_client() as client:
        yield client


# ── /api/reporting/health ─────────────────────────────────────────────────────

class TestHealthEndpoint:
    """GET /api/reporting/health testleri."""

    def test_health_returns_200(self, analytics_client):
        """Health endpoint → 200 dönmeli."""
        response = analytics_client.get("/api/reporting/health")
        assert response.status_code == 200

    def test_health_response_shape(self, analytics_client):
        """Response: status, service, version anahtarları olmalı."""
        response = analytics_client.get("/api/reporting/health")
        data = response.get_json()
        assert data.get("status") == "healthy"
        assert "service" in data
        assert "version" in data


# ── /api/reporting/generate-report ───────────────────────────────────────────

class TestGenerateReportEndpoint:
    """POST /api/reporting/generate-report testleri."""

    VALID_TEST_RUN = {
        "run_id": "run-001",
        "environment": "staging",
        "browser": "chromium",
        "start_time": "2024-01-01T10:00:00",
        "end_time": "2024-01-01T10:15:00",
        "total_tests": 10,
        "passed": 9,
        "failed": 1,
        "skipped": 0,
        "duration_ms": 900000,
        "test_cases": [],
    }

    def test_generate_report_missing_test_run_returns_400(self, analytics_client):
        """`test_run` eksik → 400 dönmeli."""
        response = analytics_client.post(
            "/api/reporting/generate-report",
            json={"formats": ["html"]},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_generate_report_valid_payload_returns_200(self, analytics_client):
        """Geçerli test_run → 200 ve success=True dönmeli."""
        response = analytics_client.post(
            "/api/reporting/generate-report",
            json={"test_run": self.VALID_TEST_RUN, "formats": ["json"]},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True

    def test_generate_report_response_has_summary(self, analytics_client):
        """Response'da `summary` anahtarı ve beklenen alanlar olmalı."""
        response = analytics_client.post(
            "/api/reporting/generate-report",
            json={"test_run": self.VALID_TEST_RUN},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        summary = data.get("summary", {})
        for key in ("total_tests", "passed", "failed", "skipped", "success_rate", "duration_seconds"):
            assert key in summary, f"summary içinde '{key}' bulunamadı"

    def test_generate_report_response_has_run_id(self, analytics_client):
        """Response'da `run_id` alanı olmalı."""
        response = analytics_client.post(
            "/api/reporting/generate-report",
            json={"test_run": self.VALID_TEST_RUN},
            content_type="application/json",
        )
        data = response.get_json()
        assert "run_id" in data


# ── /api/reporting/record-run ────────────────────────────────────────────────

class TestRecordRunEndpoint:
    """POST /api/reporting/record-run testleri."""

    def test_record_run_missing_run_id_returns_400(self, analytics_client):
        """`run_id` eksik → 400 dönmeli."""
        response = analytics_client.post(
            "/api/reporting/record-run",
            json={"environment": "staging", "total_tests": 10},
            content_type="application/json",
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_record_run_valid_returns_200(self, analytics_client):
        """Geçerli run_id → 200 ve success=True dönmeli."""
        response = analytics_client.post(
            "/api/reporting/record-run",
            json={
                "run_id": "run-123",
                "environment": "staging",
                "browser": "chromium",
                "total_tests": 50,
                "passed": 45,
                "failed": 5,
                "skipped": 0,
                "duration_ms": 900000,
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert data.get("run_id") == "run-123"

    def test_record_run_response_has_success_rate(self, analytics_client):
        """Response'da `success_rate` alanı olmalı."""
        response = analytics_client.post(
            "/api/reporting/record-run",
            json={"run_id": "run-456", "total_tests": 10, "passed": 8, "failed": 2},
            content_type="application/json",
        )
        data = response.get_json()
        assert "success_rate" in data


# ── /api/reporting/record-failure ────────────────────────────────────────────

class TestRecordFailureEndpoint:
    """POST /api/reporting/record-failure testleri."""

    def test_record_failure_missing_fields_returns_400(self, analytics_client):
        """`test_name` veya `run_id` eksik → 400 dönmeli."""
        response = analytics_client.post(
            "/api/reporting/record-failure",
            json={"test_name": "test_login"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_record_failure_valid_returns_200(self, analytics_client):
        """Geçerli payload → 200 ve success=True dönmeli."""
        response = analytics_client.post(
            "/api/reporting/record-failure",
            json={
                "test_name": "test_home_page_loads",
                "run_id": "run-123",
                "error_message": "Element not found",
                "duration_ms": 5000,
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data.get("success") is True
        assert data.get("test_name") == "test_home_page_loads"


# ── /api/reporting/analytics/trends ──────────────────────────────────────────

class TestTrendsEndpoint:
    """GET /api/reporting/analytics/trends testleri."""

    def test_trends_returns_200(self, analytics_client):
        """GET /analytics/trends → 200 dönmeli."""
        response = analytics_client.get("/api/reporting/analytics/trends")
        assert response.status_code == 200

    def test_trends_response_has_required_keys(self, analytics_client):
        """Response: success, lookback_hours, trends anahtarları olmalı."""
        response = analytics_client.get("/api/reporting/analytics/trends")
        data = response.get_json()
        assert data.get("success") is True
        assert "lookback_hours" in data
        assert "trends" in data

    def test_trends_default_lookback_hours(self, analytics_client):
        """Varsayılan lookback_hours 24 olmalı."""
        response = analytics_client.get("/api/reporting/analytics/trends")
        data = response.get_json()
        assert data.get("lookback_hours") == 24

    def test_trends_custom_hours_param(self, analytics_client):
        """hours=48 query param → lookback_hours=48 dönmeli."""
        response = analytics_client.get("/api/reporting/analytics/trends?hours=48")
        data = response.get_json()
        assert data.get("lookback_hours") == 48


# ── /api/reporting/analytics/risk-assessment ─────────────────────────────────

class TestRiskAssessmentEndpoint:
    """GET /api/reporting/analytics/risk-assessment testleri."""

    def test_risk_assessment_returns_200(self, analytics_client):
        response = analytics_client.get("/api/reporting/analytics/risk-assessment")
        assert response.status_code == 200

    def test_risk_assessment_response_shape(self, analytics_client):
        """Response: success=True, risk_assessment anahtarı olmalı."""
        response = analytics_client.get("/api/reporting/analytics/risk-assessment")
        data = response.get_json()
        assert data.get("success") is True
        risk = data.get("risk_assessment", {})
        for key in ("level", "score", "failing_tests", "unstable_tests", "regression_risk", "recommendations"):
            assert key in risk, f"risk_assessment içinde '{key}' bulunamadı"


# ── /api/reporting/analytics/predictions ─────────────────────────────────────

class TestPredictionsEndpoint:
    """GET /api/reporting/analytics/predictions testleri."""

    def test_predictions_returns_200(self, analytics_client):
        response = analytics_client.get("/api/reporting/analytics/predictions")
        assert response.status_code == 200

    def test_predictions_response_has_predictions_key(self, analytics_client):
        data = analytics_client.get("/api/reporting/analytics/predictions").get_json()
        assert data.get("success") is True
        assert "predictions" in data
        assert "lookback_days" in data


# ── /api/reporting/analytics/report ──────────────────────────────────────────

class TestAnalyticsReportEndpoint:
    """GET /api/reporting/analytics/report testleri."""

    def test_analytics_report_returns_200(self, analytics_client):
        response = analytics_client.get("/api/reporting/analytics/report")
        assert response.status_code == 200

    def test_analytics_report_response_shape(self, analytics_client):
        """Response: success, report_id, timestamp, risk_level anahtarları olmalı."""
        data = analytics_client.get("/api/reporting/analytics/report").get_json()
        assert data.get("success") is True
        for key in ("report_id", "timestamp", "risk_level", "recommendations", "trends_summary"):
            assert key in data, f"Response içinde '{key}' bulunamadı"
