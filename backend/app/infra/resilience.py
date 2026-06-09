"""Dayanıklılık primitifleri — circuit breaker + bounded timeout helper'ları.

NEDEN (panel kararı, Faz 0):
Engine ve AI-gateway'e yapılan dış çağrılarda sınırsız/yüksek timeout + circuit
breaker yokluğu, tek bir yavaş sağlayıcının (Groq/Gemini/vLLM) connection
havuzunu doyurup TÜM tenant'ları aynı anda 503'e düşürmesine yol açar
(pool-exhaustion → availability uçurumu). Bu modül, bu sınıf çağrılara hızlı
"open" davranışı kazandırır: bir downstream art arda N kez başarısız olursa,
breaker `reset_timeout` boyunca anında `CircuitBreakerOpen` fırlatır — istek
havuzda beklemez, kullanıcı hızlı degrade yanıt (503) alır.

Bağımsız ve dependency-free; saat enjekte edilebilir (test için).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, Optional


class CircuitState(str, Enum):
    CLOSED = "closed"        # normal — istekler geçer
    OPEN = "open"            # downstream çökük — istekler hızlıca reddedilir
    HALF_OPEN = "half_open"  # deneme — tek bir prob isteğe izin verilir


class CircuitBreakerOpen(Exception):
    """Breaker OPEN durumdayken çağrı denenmeden fırlatılır."""

    def __init__(self, name: str, retry_after: float) -> None:
        self.name = name
        self.retry_after = retry_after
        super().__init__(
            f"Circuit breaker '{name}' OPEN — downstream geçici olarak devre dışı "
            f"(~{retry_after:.0f}s sonra tekrar denenecek)"
        )


@dataclass
class CircuitBreaker:
    """Art arda hata sayan basit circuit breaker.

    failure_threshold: kaç ardışık hatadan sonra OPEN'a geçilir.
    reset_timeout: OPEN durumda ne kadar beklenip HALF_OPEN'a geçileceği (sn).
    clock: monotonic saat (test için enjekte edilebilir).
    """

    name: str
    failure_threshold: int = 5
    reset_timeout: float = 30.0
    clock: Callable[[], float] = time.monotonic

    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _consecutive_failures: int = field(default=0, init=False)
    _opened_at: float = field(default=0.0, init=False)
    _lock: threading.Lock = field(default_factory=threading.Lock, init=False)

    @property
    def state(self) -> CircuitState:
        with self._lock:
            return self._current_state()

    def _current_state(self) -> CircuitState:
        # OPEN ve reset süresi dolduysa HALF_OPEN'a terfi et (lock çağıran tutar).
        if self._state == CircuitState.OPEN:
            if self.clock() - self._opened_at >= self.reset_timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state

    def allow(self) -> bool:
        """OPEN değilse True. Çağrıdan ÖNCE kontrol edilmeli."""
        with self._lock:
            return self._current_state() != CircuitState.OPEN

    def before_call(self) -> None:
        """OPEN ise CircuitBreakerOpen fırlatır; aksi halde geçer."""
        with self._lock:
            state = self._current_state()
            if state == CircuitState.OPEN:
                retry_after = self.reset_timeout - (self.clock() - self._opened_at)
                raise CircuitBreakerOpen(self.name, max(0.0, retry_after))

    def record_success(self) -> None:
        """Başarılı çağrı — consecutive_failures sıfırla, HALF_OPEN'dan CLOSED'a geç.

        State machine:
        - CLOSED/HALF_OPEN → CLOSED (failures reset)
        - OPEN → ignored (success during OPEN shouldn't occur in practice)
        """
        with self._lock:
            self._consecutive_failures = 0
            # HALF_OPEN'dan CLOSED'a terfi; CLOSED zaten CLOSED kalır
            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.CLOSED

    def record_failure(self) -> None:
        """Başarısız çağrı — failure sayacını artır, eşik aşılırsa OPEN'a geç.

        State machine:
        - CLOSED: consecutive_failures artır; eşik aşılırsa → OPEN
        - HALF_OPEN: hata sayaç artmaz (prob başarısız), direkt OPEN'a geç
        - OPEN: hiçbir şey yapma (zaten OPEN)
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Zaten OPEN, ekstra başarısızlık kayda alınmaz
                return

            if self._state == CircuitState.HALF_OPEN:
                # HALF_OPEN'da tek bir başarısızlık → OPEN'a geri dön
                self._state = CircuitState.OPEN
                self._opened_at = self.clock()
            else:
                # CLOSED state
                self._consecutive_failures += 1
                if self._consecutive_failures >= self.failure_threshold:
                    self._state = CircuitState.OPEN
                    self._opened_at = self.clock()


# ── Global registry ─────────────────────────────────────────────────────────
_registry: Dict[str, CircuitBreaker] = {}
_registry_lock = threading.Lock()


def get_breaker(
    name: str,
    *,
    failure_threshold: int = 5,
    reset_timeout: float = 30.0,
) -> CircuitBreaker:
    """İsme göre paylaşılan breaker döndür (yoksa oluştur).

    Aynı downstream'i (ör. "ai-gateway", "engine") kullanan tüm çağrılar aynı
    breaker'ı paylaşmalı ki hata sayımı global olsun.
    """
    with _registry_lock:
        br = _registry.get(name)
        if br is None:
            br = CircuitBreaker(
                name=name,
                failure_threshold=failure_threshold,
                reset_timeout=reset_timeout,
            )
            _registry[name] = br
        return br


def reset_all_breakers() -> None:
    """Test yardımcı — tüm breaker state'lerini sıfırla."""
    with _registry_lock:
        _registry.clear()


# ── Bounded timeout helper ───────────────────────────────────────────────────
# Engine/AI-gateway çağrıları için ÜST SINIR. Bireysel call-site'lar daha düşük
# verebilir ama bunu AŞMAMALI — yavaş downstream connect/read'de takılıp
# havuzu tüketmesin diye.
#
# Per-domain timeout budgets: config.py'den TIMEOUT_BUDGETS oku.
# - api: AI gateway (Groq/Gemini default) → 30s
# - engine: Engine RPC → 30s
# - mobile: Appium/Selenium (uzun cihaz işlemleri) → 60s
# - tspm: Live test stream → 120s
# - default: fallback → 30s
DEFAULT_DOWNSTREAM_TIMEOUT = 10.0
MAX_DOWNSTREAM_TIMEOUT = 30.0


def bounded_timeout(requested: Optional[float] = None, domain: str = 'api') -> float:
    """İstenen timeout'u domain budget'ına sıkıştır.

    Args:
        requested: İstemci istediği timeout (saniye), None/<=0 ise budget default'u
        domain: Domain adı (api/engine/mobile/tspm/default)

    Returns:
        min(requested, domain_budget)

    Örnek:
        bounded_timeout(None, domain='api') → 30s (api budget)
        bounded_timeout(None, domain='mobile') → 60s (mobile budget)
        bounded_timeout(100, domain='mobile') → min(100, 60) = 60s
    """
    budget = None
    try:
        # Lazy import to avoid circular dependencies
        from app.config import settings
        budgets = getattr(settings, 'timeout_budgets', None)
        if budgets and isinstance(budgets, dict):
            budget = budgets.get(domain)
            if budget is None:
                budget = budgets.get('default', MAX_DOWNSTREAM_TIMEOUT)
    except Exception:
        pass

    # Fallback if import failed or config issue
    if budget is None:
        budget = MAX_DOWNSTREAM_TIMEOUT

    if requested is None or requested <= 0:
        return float(budget)
    return min(requested, float(budget))
