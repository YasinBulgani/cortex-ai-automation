"""Unit tests — circuit breaker + bounded timeout (DB/Redis gerektirmez)."""

from __future__ import annotations

import pytest

from app.infra.resilience import (
    CircuitBreaker,
    CircuitBreakerOpen,
    CircuitState,
    bounded_timeout,
    get_breaker,
    reset_all_breakers,
)


class FakeClock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t

    def advance(self, dt: float) -> None:
        self.t += dt


def test_breaker_opens_after_threshold():
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=3, reset_timeout=30.0, clock=clock)
    assert br.state == CircuitState.CLOSED
    br.record_failure()
    br.record_failure()
    assert br.allow() is True
    br.record_failure()  # 3. ardışık hata → OPEN
    assert br.state == CircuitState.OPEN
    assert br.allow() is False


def test_before_call_raises_when_open():
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=30.0, clock=clock)
    br.record_failure()
    with pytest.raises(CircuitBreakerOpen) as exc:
        br.before_call()
    assert exc.value.retry_after <= 30.0


def test_half_open_after_reset_timeout():
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=30.0, clock=clock)
    br.record_failure()  # OPEN
    assert br.state == CircuitState.OPEN
    clock.advance(31.0)
    # reset süresi geçti → HALF_OPEN, prob isteğe izin verilir
    assert br.state == CircuitState.HALF_OPEN
    assert br.allow() is True


def test_half_open_failure_reopens():
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=30.0, clock=clock)
    br.record_failure()
    clock.advance(31.0)
    assert br.state == CircuitState.HALF_OPEN
    br.record_failure()  # prob başarısız → tekrar OPEN
    assert br.state == CircuitState.OPEN


def test_success_closes_and_resets():
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=2, reset_timeout=30.0, clock=clock)
    br.record_failure()
    br.record_success()  # sayaç sıfırlanır
    br.record_failure()
    assert br.state == CircuitState.CLOSED  # tek hata, eşik 2


def test_registry_shares_breaker():
    reset_all_breakers()
    a = get_breaker("ai-gateway")
    b = get_breaker("ai-gateway")
    assert a is b
    reset_all_breakers()


def test_bounded_timeout_clamps():
    assert bounded_timeout(None) == 10.0
    assert bounded_timeout(0) == 10.0
    assert bounded_timeout(5) == 5.0
    assert bounded_timeout(120) == 30.0  # MAX'a sıkıştırılır
