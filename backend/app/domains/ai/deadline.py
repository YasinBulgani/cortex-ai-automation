"""
Deadline Propagation — bir request'in toplam sure butcesi tüm LLM zincirine tasinir.

Ihtiyac:
    Kullanıcı 10s bekleyip vazgeciyor. Biz:
    - Retries yapiyoruz (3 x 6s = 18s)
    - Self-refine yapiyoruz (+10-15s)
    - RAG + few-shot lookup yapiyoruz (+2-5s)
    Toplamda 30s sonrasi bir cevap doneriz — kullaniciya ulasmayacak + para yandi.

Çözüm:
    1) Middleware request'te X-Deadline-Ms header'i okur veya default hesaplar
    2) Absolute deadline ContextVar'a yazilir
    3) gateway_complete her attempt oncesi check:
       - deadline gecmisse DeadlineExceededError firlat
       - remaining time < retry wait ise retry yapmadan at
    4) self_refine deadline checks second pass oncesi
"""

from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

HEADER_NAME = "X-Deadline-Ms"
DEFAULT_DEADLINE_MS = 60_000  # 60s — UI zaten genelde 30s bekliyor


_deadline_ctx: ContextVar[Optional[float]] = ContextVar("llm_deadline_abs", default=None)


class DeadlineExceededError(RuntimeError):
    """Deadline asildi — caller bu cevabi client'a dondurmeli/cancel etmeli."""


# ── Public API ───────────────────────────────────────────────────────────


def set_deadline_ms(remaining_ms: int) -> None:
    """Caller (worker, test, background job) kendi deadline'ini set edebilir."""
    if remaining_ms <= 0:
        _deadline_ctx.set(None)
        return
    _deadline_ctx.set(time.monotonic() + remaining_ms / 1000.0)


def get_deadline_abs() -> Optional[float]:
    """Absolute deadline (monotonic seconds). Yoksa None."""
    return _deadline_ctx.get()


def remaining_ms() -> Optional[int]:
    """Kalan ms. Deadline yoksa None."""
    d = _deadline_ctx.get()
    if d is None:
        return None
    return max(0, int((d - time.monotonic()) * 1000))


def is_exceeded() -> bool:
    """Deadline geçmiş mi?"""
    r = remaining_ms()
    return r is not None and r <= 0


def check_deadline(operation: str = "llm") -> None:
    """Deadline gecmisse DeadlineExceededError firlat.

    Caller sik sik check etmeli (her retry oncesi, her pass oncesi).
    """
    if is_exceeded():
        raise DeadlineExceededError(
            f"Deadline asildi ({operation}): kalan {remaining_ms()}ms"
        )


def budget_for_attempt(attempt_number: int, total_attempts: int = 3) -> Optional[float]:
    """Kalan sureyi N retry arasinda adilce boluştur.

    Returns: Bu attempt için izin verilen saniye. Deadline yoksa None (sinirsiz).
    """
    r = remaining_ms()
    if r is None:
        return None
    remaining_attempts = max(1, total_attempts - attempt_number + 1)
    # Bu attempt'e dusen pay, minimum 500ms
    return max(0.5, (r / 1000.0) / remaining_attempts)


# ── Middleware ──────────────────────────────────────────────────────────


class DeadlineMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware: X-Deadline-Ms header varsa set et, yoksa default.

    Siralama: CorrelationMiddleware ile yan yana eklenebilir, sırası onemli degil.
    """

    def __init__(self, app, default_deadline_ms: int = DEFAULT_DEADLINE_MS):
        super().__init__(app)
        self._default_ms = default_deadline_ms

    async def dispatch(self, request: Request, call_next):
        header_val = request.headers.get(HEADER_NAME) or request.headers.get(HEADER_NAME.lower())
        deadline_ms = self._default_ms
        if header_val:
            try:
                parsed = int(float(str(header_val).strip()))
                # Makul sinirlar: 1s - 5dk
                deadline_ms = max(1_000, min(parsed, 300_000))
            except (ValueError, TypeError):
                pass

        token = _deadline_ctx.set(time.monotonic() + deadline_ms / 1000.0)
        try:
            response = await call_next(request)
        finally:
            _deadline_ctx.reset(token)

        # Echo — client kalan sureyi gorur (diagnostik)
        # Dikkat: remaining_ms contextvar'i reset ettik, hesaplayamayiz artik.
        response.headers[HEADER_NAME] = str(deadline_ms)
        return response
