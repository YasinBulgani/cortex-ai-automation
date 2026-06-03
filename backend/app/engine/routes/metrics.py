"""
Metrics routes — Flask engine'den port edilmiş.

ÖNCE (Flask):
  /engine/routes/metrics_routes.py — Blueprint, port 5001

SONRA (FastAPI):
  /backend/app/engine/routes/metrics.py — APIRouter, port 8000 (consolidated)

Exposed metrics (Prometheus exposition format):
  - test_runs_total      : toplam test koşumu
  - test_runs_active     : şu anda koşan testler
  - api_requests_total   : API istek sayısı
  - llm_calls_total      : LLM gateway çağrı sayısı
  - healing_events_total : self-healing olayları
  - uptime_seconds       : engine uptime
"""

from __future__ import annotations

import time

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

router = APIRouter(prefix="/api/metrics", tags=["engine", "metrics"])

_START_TIME = time.time()

# In-memory counters — thread-safe for simple int increments under GIL.
_counters: dict[str, int] = {
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
    lines: list[str] = []

    meta: dict[str, tuple[str, str]] = {
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


# ─── Routes ──────────────────────────────────────────────────────────────────


@router.get(
    "",
    response_class=PlainTextResponse,
    responses={200: {"content": {"text/plain": {}}}},
    summary="Prometheus text format metrics",
)
def prometheus_metrics() -> PlainTextResponse:
    """Prometheus text format metrics."""
    return PlainTextResponse(
        content=_build_prometheus_text(),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )


@router.get("/json", summary="JSON format metrics for dashboard")
def json_metrics() -> dict:
    """JSON format metrics for dashboard."""
    uptime = time.time() - _START_TIME
    payload: dict = dict(_counters)
    payload["uptime_seconds"] = round(uptime, 3)
    return payload
