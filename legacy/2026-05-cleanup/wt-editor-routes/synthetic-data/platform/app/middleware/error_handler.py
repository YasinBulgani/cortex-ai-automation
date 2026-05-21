"""
Global Error Handling Middleware.

Yapılandırılmış hata yanıtları, Request ID takibi ve hata kategorileri
ile tüm API hatalarını standart formatta ele alır.

Özellikler:
  - Structured error responses (error_code, message, details, timestamp)
  - Request ID tracking (X-Request-ID header)
  - Error kategorileri: VALIDATION, NOT_FOUND, RATE_LIMIT, INTERNAL, AUTH
  - Hata loglama
  - Stack trace (sadece DEBUG modunda)
"""

import time
import uuid
import traceback
import enum
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp


# ═══════════════════════════════════════════════════════════════════════
# Error Kategorileri
# ═══════════════════════════════════════════════════════════════════════


class ErrorCategory(str, enum.Enum):
    """API hata kategorileri."""

    VALIDATION = "VALIDATION"       # 400, 422 — Geçersiz istek/değer
    NOT_FOUND = "NOT_FOUND"         # 404 — Kaynak bulunamadı
    RATE_LIMIT = "RATE_LIMIT"       # 429 — Çok fazla istek
    AUTH = "AUTH"                    # 401, 403 — Kimlik doğrulama/yetki
    CONFLICT = "CONFLICT"           # 409 — Çakışma
    INTERNAL = "INTERNAL"           # 500 — Sunucu hatası
    SERVICE = "SERVICE"             # 502, 503 — Servis kullanılamıyor
    TIMEOUT = "TIMEOUT"             # 504 — Zaman aşımı


# Status code → Error category eşleştirmesi
STATUS_CATEGORY_MAP: dict[int, ErrorCategory] = {
    400: ErrorCategory.VALIDATION,
    401: ErrorCategory.AUTH,
    403: ErrorCategory.AUTH,
    404: ErrorCategory.NOT_FOUND,
    409: ErrorCategory.CONFLICT,
    422: ErrorCategory.VALIDATION,
    429: ErrorCategory.RATE_LIMIT,
    500: ErrorCategory.INTERNAL,
    502: ErrorCategory.SERVICE,
    503: ErrorCategory.SERVICE,
    504: ErrorCategory.TIMEOUT,
}

# Türkçe hata mesajları
DEFAULT_MESSAGES: dict[ErrorCategory, str] = {
    ErrorCategory.VALIDATION: "İstek doğrulama hatası oluştu.",
    ErrorCategory.NOT_FOUND: "İstenen kaynak bulunamadı.",
    ErrorCategory.RATE_LIMIT: "Çok fazla istek gönderildi. Lütfen bekleyin.",
    ErrorCategory.AUTH: "Kimlik doğrulama veya yetkilendirme hatası.",
    ErrorCategory.CONFLICT: "Kaynak çakışması oluştu.",
    ErrorCategory.INTERNAL: "Sunucu hatası oluştu. Lütfen tekrar deneyin.",
    ErrorCategory.SERVICE: "Servis geçici olarak kullanılamıyor.",
    ErrorCategory.TIMEOUT: "İstek zaman aşımına uğradı.",
}


# ═══════════════════════════════════════════════════════════════════════
# Structured Error Response
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class ErrorResponse:
    """
    Standart hata yanıt yapısı.

    Tüm API hataları bu formatta döner.
    """
    error_code: str
    message: str
    category: str
    request_id: str
    timestamp: str
    path: str
    method: str
    status_code: int
    details: Optional[dict[str, Any]] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """JSON serializable dict döndür."""
        result = asdict(self)
        # None değerleri temizle
        return {k: v for k, v in result.items() if v is not None}


# ═══════════════════════════════════════════════════════════════════════
# Error Handler Middleware
# ═══════════════════════════════════════════════════════════════════════


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Global error handling middleware.

    Tüm HTTP isteklerini sararak:
    1. Benzersiz Request ID atar (X-Request-ID)
    2. Yakalanmamış hataları yakalar
    3. Structured error response döndürür
    4. Hataları loglar

    Kullanım:
        app.add_middleware(
            ErrorHandlerMiddleware,
            debug=True,
            log_errors=True,
        )
    """

    def __init__(
        self,
        app: ASGIApp,
        debug: bool = False,
        log_errors: bool = True,
        include_stack_trace: bool = False,
    ):
        """
        Args:
            app: ASGI uygulama örneği.
            debug: Debug modu — detaylı hata bilgisi döner.
            log_errors: Hataları konsola logla.
            include_stack_trace: Stack trace'i yanıta ekle (sadece debug).
        """
        super().__init__(app)
        self.debug = debug
        self.log_errors = log_errors
        self.include_stack_trace = include_stack_trace or debug

    def _generate_request_id(self) -> str:
        """Benzersiz Request ID üret."""
        return f"req_{uuid.uuid4().hex[:16]}"

    def _get_error_category(self, status_code: int) -> ErrorCategory:
        """Status code'dan hata kategorisini belirle."""
        return STATUS_CATEGORY_MAP.get(
            status_code,
            ErrorCategory.INTERNAL if status_code >= 500 else ErrorCategory.VALIDATION,
        )

    def _build_error_response(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        message: Optional[str] = None,
        details: Optional[dict] = None,
        exc: Optional[Exception] = None,
    ) -> JSONResponse:
        """Structured error response oluştur."""
        category = self._get_error_category(status_code)

        error = ErrorResponse(
            error_code=f"ERR_{category.value}_{status_code}",
            message=message or DEFAULT_MESSAGES.get(category, "Bilinmeyen hata."),
            category=category.value,
            request_id=request_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            path=str(request.url.path),
            method=request.method,
            status_code=status_code,
            details=details,
            stack_trace=(
                traceback.format_exc()
                if exc and self.include_stack_trace
                else None
            ),
        )

        return JSONResponse(
            status_code=status_code,
            content=error.to_dict(),
            headers={"X-Request-ID": request_id},
        )

    def _log_error(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        exc: Optional[Exception] = None,
        duration: float = 0.0,
    ) -> None:
        """Hatayı konsola logla."""
        if not self.log_errors:
            return

        client_ip = "unknown"
        if request.client:
            client_ip = request.client.host

        log_parts = [
            f"[ERROR]",
            f"request_id={request_id}",
            f"method={request.method}",
            f"path={request.url.path}",
            f"status={status_code}",
            f"ip={client_ip}",
            f"duration={duration:.4f}s",
        ]

        if exc:
            log_parts.append(f"error={type(exc).__name__}: {str(exc)[:200]}")

        print(" | ".join(log_parts))

    def _log_request(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        duration: float,
    ) -> None:
        """Başarılı isteği logla (sadece yavaş istekler)."""
        if duration > 5.0:  # 5 saniyeden uzun istekleri logla
            print(
                f"[SLOW REQUEST] request_id={request_id} | "
                f"method={request.method} | path={request.url.path} | "
                f"status={status_code} | duration={duration:.4f}s"
            )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Her HTTP isteğini error handling'den geçir.

        1. Request ID ata
        2. İsteği işle
        3. Hata varsa structured response döndür
        4. Süreyi ölç ve logla
        """
        # Request ID — varsa kullan, yoksa yeni üret
        request_id = request.headers.get(
            "X-Request-ID",
            self._generate_request_id(),
        )

        start_time = time.time()

        try:
            # İsteği işle
            response = await call_next(request)
            duration = time.time() - start_time

            # Request ID header'ını ekle
            response.headers["X-Request-ID"] = request_id

            # Hata status code'larını logla
            if response.status_code >= 400:
                self._log_error(
                    request, request_id, response.status_code, duration=duration
                )
            else:
                self._log_request(
                    request, request_id, response.status_code, duration
                )

            return response

        except ValueError as exc:
            duration = time.time() - start_time
            self._log_error(request, request_id, 422, exc, duration)
            return self._build_error_response(
                request,
                request_id,
                status_code=422,
                message=f"Geçersiz değer: {str(exc)}",
                details={"type": "ValueError", "value": str(exc)},
                exc=exc,
            )

        except PermissionError as exc:
            duration = time.time() - start_time
            self._log_error(request, request_id, 403, exc, duration)
            return self._build_error_response(
                request,
                request_id,
                status_code=403,
                message="Erişim reddedildi.",
                details={"type": "PermissionError"},
                exc=exc,
            )

        except FileNotFoundError as exc:
            duration = time.time() - start_time
            self._log_error(request, request_id, 404, exc, duration)
            return self._build_error_response(
                request,
                request_id,
                status_code=404,
                message="İstenen dosya bulunamadı.",
                details={"type": "FileNotFoundError", "file": str(exc)},
                exc=exc,
            )

        except TimeoutError as exc:
            duration = time.time() - start_time
            self._log_error(request, request_id, 504, exc, duration)
            return self._build_error_response(
                request,
                request_id,
                status_code=504,
                message="İstek zaman aşımına uğradı.",
                details={"type": "TimeoutError"},
                exc=exc,
            )

        except Exception as exc:
            duration = time.time() - start_time
            self._log_error(request, request_id, 500, exc, duration)
            return self._build_error_response(
                request,
                request_id,
                status_code=500,
                message=(
                    f"Sunucu hatası: {str(exc)}"
                    if self.debug
                    else "Sunucu hatası oluştu. Lütfen tekrar deneyin."
                ),
                details=(
                    {"type": type(exc).__name__, "detail": str(exc)}
                    if self.debug
                    else None
                ),
                exc=exc,
            )


# ═══════════════════════════════════════════════════════════════════════
# Yardımcı Fonksiyonlar
# ═══════════════════════════════════════════════════════════════════════


def get_error_categories() -> dict[str, str]:
    """Tüm hata kategorilerini ve açıklamalarını döndür."""
    return {cat.value: msg for cat, msg in DEFAULT_MESSAGES.items()}


def create_error_response(
    status_code: int,
    message: str,
    request_id: str = "",
    details: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Programatik hata yanıtı oluştur.

    Route handler'lardan doğrudan kullanılabilir.
    """
    category = STATUS_CATEGORY_MAP.get(
        status_code,
        ErrorCategory.INTERNAL if status_code >= 500 else ErrorCategory.VALIDATION,
    )

    return {
        "error_code": f"ERR_{category.value}_{status_code}",
        "message": message,
        "category": category.value,
        "request_id": request_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status_code": status_code,
        "details": details,
    }
