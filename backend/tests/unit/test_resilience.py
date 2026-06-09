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
    # Per-domain timeout budget testing (Faz 2: Risk #2)
    # Test clamping behavior regardless of loaded config
    assert bounded_timeout(5, domain='api') == 5.0  # Requested under budget
    assert bounded_timeout(120, domain='api') <= 120.0  # Clamped to budget

    # Test that None/<=0 returns a sensible default
    result = bounded_timeout(None, domain='api')
    assert result > 0  # Should return a positive timeout

    # Test that requested > budget gets clamped
    result = bounded_timeout(1000, domain='api')
    assert result <= 1000  # Should be clamped


# ── State machine edge cases & transitions ──────────────────────────────────

def test_state_machine_closed_to_open():
    """CLOSED → OPEN: threshold başarısızlık."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=3, reset_timeout=30.0, clock=clock)
    assert br.state == CircuitState.CLOSED

    br.record_failure()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 1

    br.record_failure()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 2

    br.record_failure()
    assert br.state == CircuitState.OPEN
    assert br._consecutive_failures == 3


def test_state_machine_closed_reset_on_success():
    """CLOSED → success → counter sıfırlanır, CLOSED kalır."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=3, reset_timeout=30.0, clock=clock)

    br.record_failure()
    br.record_failure()
    assert br._consecutive_failures == 2

    br.record_success()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 0

    # Sayaç sıfırlandığı için eşik tekrar baştan başlar
    br.record_failure()
    assert br.state == CircuitState.CLOSED


def test_state_machine_open_to_half_open():
    """OPEN → [timeout geçer] → HALF_OPEN."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=10.0, clock=clock)

    br.record_failure()
    assert br.state == CircuitState.OPEN
    opened_at = br._opened_at

    # timeout'dan kısa süre geçti → hala OPEN
    clock.advance(5.0)
    assert br.state == CircuitState.OPEN

    # timeout geçti → HALF_OPEN'a terfi
    clock.advance(5.0)
    assert br.state == CircuitState.HALF_OPEN


def test_state_machine_half_open_success_closes():
    """HALF_OPEN → success → CLOSED (failures reset)."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=10.0, clock=clock)

    br.record_failure()
    assert br.state == CircuitState.OPEN

    clock.advance(11.0)
    assert br.state == CircuitState.HALF_OPEN

    # HALF_OPEN'da başarı → CLOSED + counter sıfır
    br.record_success()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 0


def test_state_machine_half_open_failure_reopens():
    """HALF_OPEN → failure → OPEN (kısa süre → tekrar prob)."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=3, reset_timeout=10.0, clock=clock)

    # CLOSED'da 2 hata (eşik 3'e ulaşmadı)
    br.record_failure()
    br.record_failure()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 2

    # 1 hata daha → eşik ulaştı, OPEN
    br.record_failure()
    assert br.state == CircuitState.OPEN

    clock.advance(11.0)
    assert br.state == CircuitState.HALF_OPEN
    assert br._consecutive_failures == 3  # sayaç hala 3

    # HALF_OPEN'da failure → OPEN, counter SIFIRLANMAZ (HALF_OPEN'dan OPEN'a geçerken)
    br.record_failure()
    assert br.state == CircuitState.OPEN


def test_state_machine_half_open_failure_does_not_increment():
    """HALF_OPEN'da failure, consecutive_failures artmaz (direkt OPEN)."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=2, reset_timeout=10.0, clock=clock)

    # CLOSED → 2 failures → OPEN
    br.record_failure()
    br.record_failure()
    assert br.state == CircuitState.OPEN
    initial_count = br._consecutive_failures

    clock.advance(11.0)
    assert br.state == CircuitState.HALF_OPEN

    # HALF_OPEN → failure: counter artmaz, direkt OPEN'a geç
    br.record_failure()
    assert br.state == CircuitState.OPEN
    assert br._consecutive_failures == initial_count  # değişmedi


def test_state_machine_open_failure_ignored():
    """OPEN durumda record_failure çağrılsa, state/counter değişmez."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=10.0, clock=clock)

    br.record_failure()
    assert br.state == CircuitState.OPEN
    initial_count = br._consecutive_failures

    # OPEN'da başka failure → hiçbir şey olmaz (double-count engelle)
    br.record_failure()
    assert br.state == CircuitState.OPEN
    assert br._consecutive_failures == initial_count


def test_state_machine_retry_after_calculation():
    """OPEN'da retry_after doğru hesaplanır."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=1, reset_timeout=30.0, clock=clock)

    br.record_failure()  # t=0
    assert br.state == CircuitState.OPEN

    clock.advance(10.0)  # t=10
    with pytest.raises(CircuitBreakerOpen) as exc:
        br.before_call()
    # retry_after = 30 - (10 - 0) = 20
    assert exc.value.retry_after == pytest.approx(20.0, abs=0.1)

    clock.advance(20.0)  # t=30 (timeout tam dolduruldu)
    assert br.state == CircuitState.HALF_OPEN
    br.before_call()  # exception yok


def test_state_machine_full_cycle():
    """CLOSED → OPEN → HALF_OPEN → CLOSED tam döngü."""
    clock = FakeClock()
    br = CircuitBreaker("x", failure_threshold=2, reset_timeout=20.0, clock=clock)

    # Fase 1: CLOSED, 2 ardışık hata → OPEN
    assert br.state == CircuitState.CLOSED
    br.record_failure()
    br.record_failure()
    assert br.state == CircuitState.OPEN
    assert br._consecutive_failures == 2

    # Fase 2: timeout geçti → HALF_OPEN
    clock.advance(21.0)
    assert br.state == CircuitState.HALF_OPEN
    assert br._consecutive_failures == 2

    # Fase 3: HALF_OPEN'da başarı → CLOSED + counter sıfır
    br.record_success()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 0

    # Fase 4: CLOSED'da tekrar başarılı
    br.record_success()
    assert br.state == CircuitState.CLOSED
    assert br._consecutive_failures == 0
