"""HTTP-layer wiring helpers for FastAPI."""

from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.security_middleware import (
    AuditLogMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.core.tenant_middleware import TenantMiddleware
from app.infra.database import engine


def configure_middlewares(
    app: FastAPI,
    limiter: Optional[Any],
    has_rate_limit: bool,
    rate_limit_exception: Optional[type],
    rate_limit_handler: Optional[Any],
) -> None:
    """Register shared middleware and optional rate limiting."""
    if has_rate_limit and limiter is not None and rate_limit_exception and rate_limit_handler:
        app.state.limiter = limiter
        app.add_exception_handler(rate_limit_exception, rate_limit_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept", "Origin"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_body_size=10 * 1024 * 1024)
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(TenantMiddleware)

    # UX-F2-203: Türkçe zengin hata mesajları — HTTPException, RequestValidationError
    # ve yakalanmamış exception'ları ortak şemaya sokar.
    register_exception_handlers(app)


def register_request_tracing(app: FastAPI) -> None:
    """Attach request IDs to every request and response."""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


def register_probe_routes(app: FastAPI, has_rate_limit: bool) -> None:
    """Register health and readiness probe endpoints."""

    @app.get(
        "/health",
        responses={
            200: {
                "description": "Servis canli durumda",
                "content": {
                    "application/json": {
                        "example": {"status": "ok", "service": "bgts-backend"}
                    }
                },
            }
        },
    )
    def health():
        """Temel canlılık kontrolü — yük dengeleyici için."""
        return {"status": "ok", "service": "testwright-ai-backend"}

    @app.get(
        "/ready",
        responses={
            200: {
                "description": "Servis hazir durumda",
                "content": {
                    "application/json": {
                        "example": {
                            "ready": True,
                            "database": "ok",
                            "checks": {
                                "database": {"status": "ok"},
                                "engine": {"status": "ok"},
                                "rate_limiter": {"status": "ok"},
                            },
                        }
                    }
                },
            },
            503: {"description": "Servis hazir degil"},
        },
    )
    def ready(_request: Request):
        """
        Hazırlık kontrolü — DB + engine bağlantı durumunu döndürür.
        Kubernetes readinessProbe ve Uptime izleme için kullanılır.
        """
        result = {"ready": True, "database": "ok", "checks": {}}

        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            result["checks"]["database"] = {"status": "ok"}
        except Exception as exc:
            result["checks"]["database"] = {"status": "error", "detail": str(exc)[:120]}
            result["database"] = "error"
            result["ready"] = False

        try:
            import httpx

            response = httpx.get(f"{settings.engine_base_url}/health", timeout=3.0)
            if response.status_code == 200:
                result["checks"]["engine"] = {"status": "ok"}
            else:
                result["checks"]["engine"] = {
                    "status": "degraded",
                    "http": response.status_code,
                }
        except Exception as exc:
            result["checks"]["engine"] = {"status": "unreachable", "detail": str(exc)[:80]}

        result["checks"]["rate_limiter"] = {"status": "ok" if has_rate_limit else "disabled"}
        status_code = 200 if result["ready"] else 503
        return JSONResponse(content=result, status_code=status_code)
