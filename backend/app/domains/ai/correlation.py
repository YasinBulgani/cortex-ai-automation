"""
Correlation ID — bir kullanıcı istegi -> N LLM cagrisi trace'lerini baglar.

Mimari:
    1) FastAPI middleware (``CorrelationMiddleware``) her request'te
       ``X-Correlation-ID`` header'i okur; yoksa UUID4 uretir.
    2) ContextVar ile tüm async/sync kod path'inde erisilebilir.
    3) gateway_client bu ID'yi AI Gateway'e header olarak iletir ve
       llm_traces tablosuna yazilir (correlation_id kolonu).
    4) Response'da ayni header echo edilir — frontend/debug aracinda
       kullanıcı bir tek ID ile Jaeger/DB sorgulari yapabilir.

Bu sayede:
    - Bir chat mesajinin altindaki 3-5 LLM cagrisini tek query ile cek
    - Debug: "Neden bu response geldi?" -> correlation_id ile trace cikart
    - Regression cross-reference: eval_runs -> judge_runs -> traces zincirlenir
"""

from __future__ import annotations

import logging
import uuid
from contextvars import ContextVar
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

HEADER_NAME = "X-Correlation-ID"

# ContextVar: her async task'a/request'e ozel deger
_correlation_id_ctx: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> Optional[str]:
    """Aktif correlation ID'yi dondur. Yoksa None."""
    return _correlation_id_ctx.get()


def set_correlation_id(correlation_id: Optional[str]) -> None:
    """Explicit set — test veya worker context'i için."""
    _correlation_id_ctx.set(correlation_id)


def ensure_correlation_id() -> str:
    """Yoksa UUID üret ve set et. Background job'lar için yardimci."""
    current = _correlation_id_ctx.get()
    if current:
        return current
    new_id = str(uuid.uuid4())
    _correlation_id_ctx.set(new_id)
    return new_id


class CorrelationMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware: her request için correlation ID set/echo.

    Siralama: CORS ve auth middleware'lerinden SONRA (ya da paralel) eklenmeli —
    contextvar async task boyunca yasar. Response header'i client'a doner.
    """

    async def dispatch(self, request: Request, call_next):
        # Client verdiyse onu kullan, yoksa yeni üret
        incoming = request.headers.get(HEADER_NAME) or request.headers.get(HEADER_NAME.lower())
        correlation_id = (incoming or str(uuid.uuid4())).strip()[:64]

        token = _correlation_id_ctx.set(correlation_id)
        try:
            response: Response = await call_next(request)
        finally:
            _correlation_id_ctx.reset(token)

        # Echo response'a
        response.headers[HEADER_NAME] = correlation_id
        return response
