"""
metrics_routes.py — Prometheus-uyumlu /api/metrics endpoint.

Exposed metrics:
  - test_runs_total: toplam test koşumu
  - test_runs_active: şu anda koşan testler
  - api_requests_total: API istek sayısı (by endpoint)
  - llm_calls_total: LLM gateway çağrı sayısı
  - healing_events_total: self-healing olayları
  - uptime_seconds: engine uptime
"""
from __future__ import annotations
import time
from flask import Blueprint, Response, request, jsonify

metrics_bp = Blueprint("metrics", __name__)

_START_TIME = time.time()

# In-memory counters (thread-safe increment via GIL for int)
_counters = {
    "test_runs_total": 0,
    "test_runs_active": 0,
    "api_requests_total": 0,
    "llm_calls_total": 0,
    "healing_events_total": 0,
}

def increment(metric: str, by: int = 1) -> None:
    """Increment a counter. Import and call from other route modules."""
    if metric in _counters:
        _counters[metric] += by


def _build_prometheus_text() -> str:
    """Build Prometheus exposition format text."""
    uptime = time.time() - _START_TIME
    lines = []

    meta = {
        "test_runs_total": ("counter", "Total number of test runs executed"),
        "test_runs_active": ("gauge", "Number of currently active test runs"),
        "api_requests_total": ("counter", "Total number of API requests received"),
        "llm_calls_total": ("counter", "Total number of LLM gateway calls"),
        "healing_events_total": ("counter", "Total number of self-healing events triggered"),
    }

    for name, (mtype, help_text) in meta.items():
        lines.append(f"# HELP {name} {help_text}")
        lines.append(f"# TYPE {name} {mtype}")
        lines.append(f"{name} {_counters[name]}")

    lines.append("# HELP uptime_seconds Seconds since engine started")
    lines.append("# TYPE uptime_seconds gauge")
    lines.append(f"uptime_seconds {uptime:.3f}")

    return "\n".join(lines) + "\n"


@metrics_bp.route("/api/metrics", methods=["GET"])
def prometheus_metrics():
    """Prometheus text format metrics."""
    return Response(
        _build_prometheus_text(),
        status=200,
        mimetype="text/plain; version=0.0.4; charset=utf-8",
    )


@metrics_bp.route("/api/metrics/json", methods=["GET"])
def json_metrics():
    """JSON format metrics for dashboard."""
    uptime = time.time() - _START_TIME
    payload = dict(_counters)
    payload["uptime_seconds"] = round(uptime, 3)
    return jsonify(payload)
