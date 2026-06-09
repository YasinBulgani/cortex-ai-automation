"""CircuitBreakerOpen → 503 exception handler testi (DB/Redis yok)."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.exception_handlers import register_exception_handlers
from app.infra.resilience import CircuitBreakerOpen


def _app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom():
        raise CircuitBreakerOpen("engine", retry_after=12.0)

    return app


def test_circuit_breaker_open_returns_503_with_retry_after():
    client = TestClient(_app(), raise_server_exceptions=False)
    resp = client.get("/boom")
    assert resp.status_code == 503
    assert resp.headers.get("Retry-After") == "12"
    body = resp.json()
    # _build_body sarmalı — code alanı downstream.unavailable olmalı
    payload = body.get("error", body)
    assert "downstream.unavailable" in str(payload)
