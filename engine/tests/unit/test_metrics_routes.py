"""
test_metrics_routes.py — Unit tests for engine/routes/metrics_routes.py

10 tests covering:
  - GET /api/metrics  → 200, text/plain, Prometheus # HELP lines
  - GET /api/metrics/json → 200, JSON with expected keys
  - increment() counter mechanics
  - uptime_seconds grows over time
"""
from __future__ import annotations

import json
import time
import importlib
import sys
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_counters():
    """Reset module-level state before each test to avoid cross-test bleed."""
    import routes.metrics_routes as mod
    mod._counters = {
        "test_runs_total": 0,
        "test_runs_active": 0,
        "api_requests_total": 0,
        "llm_calls_total": 0,
        "healing_events_total": 0,
    }
    yield


@pytest.fixture()
def client():
    """Minimal Flask test client that registers only metrics_bp."""
    from flask import Flask
    from routes.metrics_routes import metrics_bp

    app = Flask(__name__)
    app.register_blueprint(metrics_bp)
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Tests — GET /api/metrics (Prometheus format)
# ---------------------------------------------------------------------------

class TestPrometheusEndpoint:
    def test_status_200(self, client):
        resp = client.get("/api/metrics")
        assert resp.status_code == 200

    def test_content_type_is_text_plain(self, client):
        resp = client.get("/api/metrics")
        assert "text/plain" in resp.content_type

    def test_response_contains_help_lines(self, client):
        resp = client.get("/api/metrics")
        body = resp.data.decode()
        assert "# HELP" in body

    def test_response_contains_type_lines(self, client):
        resp = client.get("/api/metrics")
        body = resp.data.decode()
        assert "# TYPE" in body

    def test_response_contains_uptime_seconds(self, client):
        resp = client.get("/api/metrics")
        body = resp.data.decode()
        assert "uptime_seconds" in body

    def test_response_contains_all_counter_names(self, client):
        resp = client.get("/api/metrics")
        body = resp.data.decode()
        for name in ("test_runs_total", "test_runs_active", "api_requests_total",
                     "llm_calls_total", "healing_events_total"):
            assert name in body, f"Missing metric: {name}"


# ---------------------------------------------------------------------------
# Tests — GET /api/metrics/json
# ---------------------------------------------------------------------------

class TestJsonEndpoint:
    def test_status_200(self, client):
        resp = client.get("/api/metrics/json")
        assert resp.status_code == 200

    def test_response_is_valid_json(self, client):
        resp = client.get("/api/metrics/json")
        data = json.loads(resp.data)
        assert isinstance(data, dict)

    def test_json_contains_uptime_seconds(self, client):
        resp = client.get("/api/metrics/json")
        data = json.loads(resp.data)
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_json_contains_all_counters(self, client):
        resp = client.get("/api/metrics/json")
        data = json.loads(resp.data)
        for key in ("test_runs_total", "test_runs_active", "api_requests_total",
                    "llm_calls_total", "healing_events_total"):
            assert key in data, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Tests — increment() helper
# ---------------------------------------------------------------------------

class TestIncrementHelper:
    def test_increment_increases_counter(self):
        from routes.metrics_routes import increment, _counters
        increment("test_runs_total")
        assert _counters["test_runs_total"] == 1

    def test_increment_by_custom_amount(self):
        from routes.metrics_routes import increment, _counters
        increment("llm_calls_total", by=5)
        assert _counters["llm_calls_total"] == 5

    def test_increment_unknown_metric_is_noop(self):
        from routes.metrics_routes import increment, _counters
        before = dict(_counters)
        increment("nonexistent_metric")
        assert _counters == before

    def test_increment_reflected_in_prometheus_output(self, client):
        from routes.metrics_routes import increment
        increment("healing_events_total", by=3)
        resp = client.get("/api/metrics")
        body = resp.data.decode()
        assert "healing_events_total 3" in body

    def test_increment_reflected_in_json_output(self, client):
        from routes.metrics_routes import increment
        increment("api_requests_total", by=7)
        resp = client.get("/api/metrics/json")
        data = json.loads(resp.data)
        assert data["api_requests_total"] == 7


# ---------------------------------------------------------------------------
# Test — uptime grows over time
# ---------------------------------------------------------------------------

class TestUptime:
    def test_uptime_increases_over_time(self, client):
        resp1 = client.get("/api/metrics/json")
        time.sleep(0.05)
        resp2 = client.get("/api/metrics/json")
        uptime1 = json.loads(resp1.data)["uptime_seconds"]
        uptime2 = json.loads(resp2.data)["uptime_seconds"]
        assert uptime2 > uptime1
