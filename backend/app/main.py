"""Neurex API — giriş noktası.

Bu modül bilinçli olarak incedir: tüm bootstrap logic'i
``app.core.runtime``, HTTP-layer ``app.core.http``, ve domain router'ların
kaydı ``app.core.router_registry`` altındadır.

Uvicorn/Gunicorn ``app.main:app`` ile çağırır. ``create_app()`` testlerde
izole app örneği üretmek için de kullanılabilir.
"""

from __future__ import annotations

from fastapi import FastAPI
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

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

    # i18n middleware (locale from ?lang / X-Locale / Accept-Language)
    from app.core.i18n import LocaleMiddleware
    app.add_middleware(LocaleMiddleware)

    # ProxyHeadersMiddleware must be the outermost middleware so it rewrites
    # client IP / protocol from trusted reverse-proxy headers before any other
    # middleware (e.g. rate limiting, audit logging) reads request.client.
    # In Starlette, the last add_middleware() call becomes the outermost layer.
    # Set TRUSTED_PROXY_IPS to your load balancer IPs in production to prevent
    # IP spoofing that would bypass rate limiting and brute-force guards.
    trusted_proxy_ips = (
        ["*"] if settings.trusted_proxy_ips.strip() == "*"
        else [ip.strip() for ip in settings.trusted_proxy_ips.split(",") if ip.strip()]
    )
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=trusted_proxy_ips)

    register_probe_routes(app, has_rate_limit=_has_rate_limit)
    register_api_routers(app)

    # Production yapilandirma dogrulamalari (dev'de no-op)
    from app.infra.prod_checks import assert_production_invariants
    assert_production_invariants()

    return app


app = create_app()
