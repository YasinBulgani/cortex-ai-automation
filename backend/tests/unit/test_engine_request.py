"""engine_request — bounded timeout + circuit breaker birim testi (DB/Redis yok)."""

from __future__ import annotations

import httpx
import pytest

from app.core import engine_client
from app.infra.resilience import CircuitBreakerOpen, CircuitState, get_breaker, reset_all_breakers


class _Resp:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_bounded_timeout_applied(monkeypatch):
    reset_all_breakers()
    captured = {}

    def fake_request(method, url, **kwargs):
        captured["timeout"] = kwargs.get("timeout")
        captured["url"] = url
        return _Resp(200)

    monkeypatch.setattr(engine_client.httpx, "request", fake_request)
    # 120s istendi → MAX_DOWNSTREAM_TIMEOUT (30) ile sıkıştırılmalı
    engine_client.engine_request("POST", "/run", json={}, timeout=120)
    assert captured["timeout"] == 30.0
    # path baştaki / olmadan da düzgün birleşmeli
    engine_client.engine_request("GET", "ping")
    assert captured["url"].endswith("/ping")
    reset_all_breakers()


def test_breaker_opens_on_connection_errors(monkeypatch):
    reset_all_breakers()

    def boom(method, url, **kwargs):
        raise httpx.ConnectError("engine down")

    monkeypatch.setattr(engine_client.httpx, "request", boom)
    breaker = get_breaker(engine_client._ENGINE_BREAKER_NAME)
    for _ in range(5):
        with pytest.raises(httpx.ConnectError):
            engine_client.engine_request("POST", "/run", json={})
    assert breaker.state == CircuitState.OPEN

    # OPEN iken: çağrı httpx'e gitmeden CircuitBreakerOpen ile reddedilir
    def should_not_call(method, url, **kwargs):
        raise AssertionError("breaker OPEN iken downstream'e gidilmemeli")

    monkeypatch.setattr(engine_client.httpx, "request", should_not_call)
    with pytest.raises(CircuitBreakerOpen):
        engine_client.engine_request("POST", "/run", json={})
    reset_all_breakers()


def test_5xx_counts_as_failure_4xx_does_not(monkeypatch):
    reset_all_breakers()
    breaker = get_breaker(engine_client._ENGINE_BREAKER_NAME)

    monkeypatch.setattr(engine_client.httpx, "request", lambda *a, **k: _Resp(404))
    for _ in range(10):
        engine_client.engine_request("GET", "/x")
    assert breaker.state == CircuitState.CLOSED  # 4xx breaker'ı açmaz

    monkeypatch.setattr(engine_client.httpx, "request", lambda *a, **k: _Resp(500))
    for _ in range(5):
        engine_client.engine_request("GET", "/x")
    assert breaker.state == CircuitState.OPEN  # 5xx açar
    reset_all_breakers()
