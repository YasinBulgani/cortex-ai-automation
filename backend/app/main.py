"""Sentetik veri platformu / TestwrightAI API — giriş noktası.

Bu modül bilinçli olarak incedir: tüm bootstrap logic'i
``app.core.runtime``, HTTP-layer ``app.core.http``, ve domain router'ların
kaydı ``app.core.router_registry`` altındadır.

Uvicorn/Gunicorn ``app.main:app`` ile çağırır. ``create_app()`` testlerde
izole app örneği üretmek için de kullanılabilir.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import threading
import uuid
from pathlib import Path

# ── Sentry (Hata İzleme) ──────────────────────────────────────────────────────
import os as _os
_SENTRY_DSN = _os.getenv("SENTRY_DSN", "")

_SENSITIVE_KEYS = frozenset({
    "password", "passwd", "secret", "token", "access_token", "refresh_token",
    "authorization", "api_key", "apikey", "private_key", "client_secret",
    "credit_card", "card_number", "cvv", "ssn",
})


def _scrub_pii(obj: object, depth: int = 0) -> object:
    """Sentry event dict'inden hassas alanları siler (max 6 seviye derinlik)."""
    if depth > 6:
        return obj
    if isinstance(obj, dict):
        return {
            k: "[Filtered]" if k.lower() in _SENSITIVE_KEYS else _scrub_pii(v, depth + 1)
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_scrub_pii(i, depth + 1) for i in obj]
    return obj


def _before_send(event: dict, hint: object) -> dict:
    for section in ("request", "extra", "contexts"):
        if section in event:
            event[section] = _scrub_pii(event[section])
    return event


if _SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=_SENTRY_DSN,
            environment=_os.getenv("SENTRY_ENVIRONMENT", "production"),
            traces_sample_rate=float(_os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                LoggingIntegration(level=logging.WARNING, event_level=logging.ERROR),
            ],
            send_default_pii=False,
            before_send=_before_send,
        )
        logging.getLogger(__name__).info("Sentry aktif: environment=%s", _os.getenv("SENTRY_ENVIRONMENT", "production"))
    except ImportError:
        logging.getLogger(__name__).info("sentry-sdk kurulu değil, hata izleme devre dışı.")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.core.http import (
    configure_middlewares,
    register_probe_routes,
    register_request_tracing,
)
from app.core.openapi_config import custom_openapi_schema
from app.core.router_registry import register_api_routers
from app.core.runtime import (
    app_lifespan,
    build_rate_limiter,
    configure_prometheus,
    initialize_sentry,
)

# Startup-time side effect — Sentry DSN set edilmemişse no-op.
initialize_sentry()

# Rate limiter opsiyonel; production'da Redis'e bağlı, dev'de skip.
# Tuple: (limiter, has_rate_limit, exc_type, exc_handler)
_limiter, _has_rate_limit, _rate_limit_exc, _rate_limit_handler = build_rate_limiter()


def create_app() -> FastAPI:
    """Yeni bir FastAPI uygulaması oluştur ve bağımlılıklarını bağla.

    Testlerde app'ı fresh oluşturmak veya multi-tenant senaryolarda
    parametrik wiring için kullanılabilir.
    """
    fastapi_kwargs: dict = {
        "title": settings.app_name,
        "lifespan": app_lifespan,
    }
    if settings.is_production_like:
        # Üretimde OpenAPI/Swagger UI endpoint'leri kapalı — attack surface'u azalt.
        fastapi_kwargs.update(docs_url=None, redoc_url=None, openapi_url=None)

    app = FastAPI(**fastapi_kwargs)
    app.openapi = lambda: custom_openapi_schema(app)

    configure_prometheus(app)
    configure_middlewares(
        app,
        limiter=_limiter,
        has_rate_limit=_has_rate_limit,
        rate_limit_exception=_rate_limit_exc,
        rate_limit_handler=_rate_limit_handler,
    )
    register_request_tracing(app)
    register_probe_routes(app, has_rate_limit=_has_rate_limit)
    register_api_routers(app)
    return app


app = create_app()
