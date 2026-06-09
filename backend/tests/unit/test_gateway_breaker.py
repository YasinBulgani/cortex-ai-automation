"""gateway_complete + circuit breaker entegrasyon testi (DB/Redis gerektirmez)."""

from __future__ import annotations

import httpx
import pytest

from app.domains.ai import gateway_client as gc
from app.infra.resilience import CircuitState, get_breaker, reset_all_breakers


class _BoomClient:
    """Her post'ta bağlantı hatası fırlatan sahte httpx client."""

    def __init__(self) -> None:
        self.post_calls = 0

    def post(self, *args, **kwargs):
        self.post_calls += 1
        raise httpx.ConnectError("downstream down")


def test_breaker_opens_then_fast_fails(monkeypatch):
    reset_all_breakers()
    boom = _BoomClient()
    monkeypatch.setattr(gc, "_get_http_client", lambda: boom)
    monkeypatch.setattr(gc.time, "sleep", lambda *_: None)  # retry backoff'u hızlandır

    # Breaker OPEN olana kadar çağır (her çağrı _MAX_RETRIES kez post dener).
    breaker = get_breaker(gc._AI_BREAKER_NAME)
    for _ in range(5):
        with pytest.raises(RuntimeError):
            gc.gateway_complete("chat", "merhaba", use_cache=False)
        if breaker.state == CircuitState.OPEN:
            break

    assert breaker.state == CircuitState.OPEN

    # Breaker OPEN iken: bir sonraki çağrı post YAPMADAN hızlıca reddedilmeli.
    posts_before = boom.post_calls
    with pytest.raises(RuntimeError, match="geçici olarak devre dışı"):
        gc.gateway_complete("chat", "merhaba", use_cache=False)
    assert boom.post_calls == posts_before  # downstream'e hiç gidilmedi

    reset_all_breakers()
