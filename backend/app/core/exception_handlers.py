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
    """Hiçbir yerde yakalanmamış exception — 500 + katalog varsayılanı."""
    logger.exception("Yakalanmamış hata: %s", exc)
    entry = ERROR_CATALOG["internal.unexpected"]
    detail = {
        "code": "internal.unexpected",
        "title": entry["title"],
        "message": entry["message"],
        "suggestion": entry["suggestion"],
        "doc_url": entry.get("doc_url"),
    }
    return JSONResponse(
        status_code=500,
        content=_build_body(detail, _request_id(request)),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """FastAPI app'a tüm özel handler'ları bağla."""
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
