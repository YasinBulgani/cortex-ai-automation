"""Global FastAPI exception handler'ları — zengin hata cevabı şeması.

``app.core.error_messages`` kataloğuyla birlikte çalışır. Tüm HTTPException'lar
(hem ``AppError`` hem klasik ``HTTPException``) aynı JSON şemasında döner:

    {
      "error": {
        "code": "...",
        "title": "...",
        "message": "...",
        "suggestion": "...",
        "doc_url": null
      },
      "request_id": "..."
    }

Kayıt:
    ``register_exception_handlers(app)`` — FastAPI create_app içinde çağrılır.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.error_messages import ERROR_CATALOG, _format_message, enrich_legacy_detail

logger = logging.getLogger(__name__)


def _request_id(request: Request) -> str | None:
    """Middleware tarafından set edildiyse request_id'yi al."""
    return getattr(getattr(request, "state", None), "request_id", None)


def _get_correlation_id() -> str | None:
    """Contextvar'dan correlation ID'yi al. Yoksa None."""
    try:
        from app.domains.ai.correlation import get_correlation_id
        return get_correlation_id()
    except (ImportError, Exception):
        return None


def _build_body(error_detail: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": error_detail, "request_id": request_id}
    # Backward compat: expose top-level "detail" so existing tests don't break
    if "message" in error_detail:
        body["detail"] = error_detail["message"]
    return body


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException + AppError → zenginleştirilmiş JSON."""
    enriched = enrich_legacy_detail(exc.detail, exc.status_code)
    body = _build_body(enriched, _request_id(request))
    # Backward compat: preserve original exc.detail (dict or str) under "detail"
    body["detail"] = exc.detail
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
        headers=exc.headers or None,
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic/FastAPI input validation hatalarını kataloğa uygun biçime sok."""
    # Kullanıcıya yararlı özet: ilk 3 hatadan alan + mesaj
    parts: list[str] = []
    for err in exc.errors()[:3]:
        loc = ".".join(str(x) for x in err.get("loc", []) if x not in ("body",))
        msg = err.get("msg", "")
        if loc:
            parts.append(f"{loc}: {msg}")
        else:
            parts.append(msg)
    summary = "; ".join(parts) or "Gönderilen veri doğrulanamadı."
    entry = ERROR_CATALOG["validation.invalid_input"]
    detail = {
        "code": "validation.invalid_input",
        "title": entry["title"],
        "message": _format_message(entry["message"], {"detail": summary}),
        "suggestion": entry["suggestion"],
        "doc_url": entry.get("doc_url"),
        "field_errors": json.loads(json.dumps(exc.errors(), default=str)),
    }
    body = _build_body(detail, _request_id(request))
    body["detail"] = body["error"].get("field_errors", [])
    return JSONResponse(status_code=422, content=body)


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Hiçbir yerde yakalanmamış exception — 500 + katalog varsayılanı.

    S-HIGH-5: Do NOT expose exception details to client (stack trace leak prevention).
    Exception is logged server-side, but response is generic (no traceback to user).
    """
    correlation_id = _get_correlation_id()
    logger.exception("Yakalanmamış hata: %s (correlation_id=%s)", exc, correlation_id)
    entry = ERROR_CATALOG["internal.unexpected"]
    detail = {
        "code": "internal.unexpected",
        "title": entry["title"],
        "message": entry["message"],  # Generic message only
        "suggestion": entry["suggestion"],
        "doc_url": entry.get("doc_url"),
        # Never include: str(exc), traceback, or exception type details
    }
    return JSONResponse(
        status_code=500,
        content=_build_body(detail, _request_id(request)),
    )


async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    """Service layer ValueError → 400 Bad Request."""
    detail = {
        "code": "client.bad_request",
        "title": "Bad Request",
        "message": str(exc),
        "suggestion": "İstek parametrelerini kontrol edin.",
        "doc_url": None,
    }
    return JSONResponse(
        status_code=400,
        content=_build_body(detail, _request_id(request)),
    )


async def key_error_handler(request: Request, exc: KeyError) -> JSONResponse:
    """Service layer KeyError → 404 Not Found."""
    message = str(exc).strip("'\"")
    detail = {
        "code": "client.not_found",
        "title": "Not Found",
        "message": message,
        "suggestion": "Belirtilen kayıt bulunamadı.",
        "doc_url": None,
    }
    return JSONResponse(
        status_code=404,
        content=_build_body(detail, _request_id(request)),
    )


async def permission_error_handler(request: Request, exc: PermissionError) -> JSONResponse:
    """Service layer PermissionError → 403 Forbidden."""
    detail = {
        "code": "client.forbidden",
        "title": "Forbidden",
        "message": str(exc),
        "suggestion": "Bu işlem için yetkiniz bulunmamaktadır.",
        "doc_url": None,
    }
    return JSONResponse(
        status_code=403,
        content=_build_body(detail, _request_id(request)),
    )


async def runtime_error_handler(request: Request, exc: RuntimeError) -> JSONResponse:
    """Service layer RuntimeError → 500 Internal Server Error.

    S-HIGH-5: Do NOT expose exception details (str(exc) can leak sensitive info).
    Log server-side, return generic message to client.
    """
    correlation_id = _get_correlation_id()
    logger.error("Service RuntimeError: %s (correlation_id=%s)", exc, correlation_id)
    detail = {
        "code": "internal.service_error",
        "title": "Internal Server Error",
        "message": "Bir sistem hatası oluştu. Lütfen destek ekibiyle iletişime geçin.",
        "suggestion": "Lütfen daha sonra tekrar deneyin.",
        "doc_url": None,
    }
    return JSONResponse(
        status_code=500,
        content=_build_body(detail, _request_id(request)),
    )


async def rate_limit_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Service layer RateLimitError → 429 Too Many Requests."""
    retry_after = getattr(exc, "retry_after_seconds", 60)
    detail = {
        "code": "client.rate_limit_exceeded",
        "title": "Too Many Requests",
        "message": str(exc),
        "suggestion": f"Lütfen {retry_after} saniye bekleyin ve tekrar deneyin.",
        "doc_url": None,
    }
    return JSONResponse(
        status_code=429,
        content=_build_body(detail, _request_id(request)),
        headers={"Retry-After": str(retry_after)},
    )


async def circuit_breaker_open_handler(request: Request, exc: Exception) -> JSONResponse:
    """Downstream circuit breaker OPEN → 503 Service Unavailable + Retry-After.

    engine_request()/gateway_client breaker'ı OPEN iken bu fırlatılır. İstek
    downstream'e hiç gitmeden hızlıca 503 döner — pool exhaustion önlenir.
    """
    retry_after = int(getattr(exc, "retry_after", 30)) or 30
    detail = {
        "code": "downstream.unavailable",
        "title": "Service Unavailable",
        "message": str(exc),
        "suggestion": f"Bağlı servis geçici olarak yanıt vermiyor. {retry_after} saniye sonra tekrar deneyin.",
        "doc_url": None,
    }
    return JSONResponse(
        status_code=503,
        content=_build_body(detail, _request_id(request)),
        headers={"Retry-After": str(retry_after)},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Tüm exception handler'ları FastAPI uygulamasına kaydet.

    ``create_app()`` içinde çağrılmalıdır.

    Sıralama önemli: Daha spesifik exception'lar genel olanlardan ÖNCE
    kaydedilmeli (FastAPI LIFO/last-match-first uyguladığı için).
    """
    from fastapi.exceptions import RequestValidationError

    from app.core.exceptions import RateLimitError
    from app.infra.resilience import CircuitBreakerOpen

    # Spesifik HTTP/API exception'ları önce
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)

    # Custom application exception'ları
    app.add_exception_handler(RateLimitError, rate_limit_error_handler)
    app.add_exception_handler(CircuitBreakerOpen, circuit_breaker_open_handler)

    # Service layer exception'ları (ValueError, KeyError, vb)
    # — daha spesifik olanları genel Exception'ından önce
    app.add_exception_handler(PermissionError, permission_error_handler)
    app.add_exception_handler(KeyError, key_error_handler)
    app.add_exception_handler(ValueError, value_error_handler)
    app.add_exception_handler(RuntimeError, runtime_error_handler)

    # En son: catch-all exception handler
    app.add_exception_handler(Exception, unhandled_exception_handler)
