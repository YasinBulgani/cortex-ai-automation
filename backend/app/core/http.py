"""HTTP-layer wiring helpers for FastAPI."""

from __future__ import annotations

import uuid
from hashlib import md5
from typing import Any, Optional

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.query_deadline_middleware import QueryDeadlineMiddleware
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

    # ── Performans: Gzip sıkıştırma ─────────────────────────────────────────
    # 1KB üzerindeki JSON yanıtları otomatik gzip ile sıkıştırılır.
    # Dashboard (10-50KB), senaryo listeleri (5-30KB) ve AI yanıtları (~50KB)
    # için ağ trafiğini %60-80 azaltır.
    app.add_middleware(GZipMiddleware, minimum_size=1024, compresslevel=6)

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
    app.add_middleware(QueryDeadlineMiddleware)

    # UX-F2-203: Türkçe zengin hata mesajları — HTTPException, RequestValidationError
    # ve yakalanmamış exception'ları ortak şemaya sokar.
    register_exception_handlers(app)

    # CODE-HIGH-3: Correlation ID middleware — her request için trace ID propagation.
    # Sıralama: CORS/Auth'tan sonra, ama exception handler'dan önce eklenmeli.
    from app.domains.ai.correlation import CorrelationMiddleware
    app.add_middleware(CorrelationMiddleware)


def register_request_tracing(app: FastAPI) -> None:
    """Attach request IDs to every request and response."""

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())[:12]
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── ETag + 304 Not Modified Support (perf opt 2.2) ──────────────────────
    # Reduce bandwidth by 90% on repeated GET requests. Client sends
    # If-None-Match header with previous ETag; server responds 304 if unchanged.
    @app.middleware("http")
    async def etag_middleware(request: Request, call_next) -> Response:
        """Add ETag header and support 304 Not Modified responses."""
        if request.method != "GET":
            return await call_next(request)

        response = await call_next(request)

        # Only compute ETag for successful JSON responses
        if response.status_code >= 200 and response.status_code < 300:
            if "application/json" in response.headers.get("content-type", ""):
                try:
                    # Collect body for hashing
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk

                    # Compute ETag
                    etag = md5(body).hexdigest()
                    response.headers["ETag"] = f'"{etag}"'

                    # Check If-None-Match
                    if request.headers.get("If-None-Match") == f'"{etag}"':
                        return Response(
                            status_code=304,
                            headers=response.headers,
                        )

                    # Stream body back with ETag
                    async def stream_body():
                        yield body

                    response.body_iterator = stream_body()
                except Exception:
                    pass  # On error, return response without ETag

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
    def health(detailed: bool = False):
        """Temel canlılık kontrolü — yük dengeleyici için. (perf opt 2.8)

        Args:
            detailed: If True, perform full health checks (slower). Default: fast ping.
        """
        # Fast default check (1ms)
        if not detailed:
            return {"status": "ok", "service": "testwright-ai-backend"}

        # Detailed check with dependencies
        result = {
            "status": "ok",
            "service": "testwright-ai-backend",
            "checks": {},
        }

        # Check database
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            result["checks"]["database"] = "ok"
        except Exception as e:
            result["checks"]["database"] = f"error: {str(e)[:50]}"
            result["status"] = "degraded"

        # Check Redis (if available)
        try:
            from app.infra.redis_cache import get_redis_client

            redis = get_redis_client()
            redis.ping()
            result["checks"]["redis"] = "ok"
        except Exception:
            result["checks"]["redis"] = "unavailable"

        return result

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
