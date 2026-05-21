"""Comprehensive security middleware for TestwrightAI Banking Platform.

Provides:
- SecurityHeadersMiddleware  -- standard security response headers
- RequestSizeLimitMiddleware -- body-size enforcement (10 MB / 50 MB uploads)
- AuditLogMiddleware         -- structured JSON logging for state-changing ops
- InputSanitizer             -- utility helpers for route handlers

Complies with: KVKK, BDDK, PCI-DSS.
Python 3.9 compatible.
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.security_config import (
    API_CACHE_CONTROL,
    API_CSP,
    HSTS_HEADER,
    SECURITY_HEADERS,
    MAX_REQUEST_BODY_SIZE,
    MAX_UPLOAD_SIZE,
)

_logger = logging.getLogger("bgts.security")
_audit_logger = logging.getLogger("bgts.audit")

# ---------------------------------------------------------------------------
# 1. SecurityHeadersMiddleware
# ---------------------------------------------------------------------------


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Inject OWASP-recommended security headers into every response."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)

        # Static security headers
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value

        # HSTS only over HTTPS
        scheme = request.url.scheme
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if scheme == "https" or forwarded_proto == "https":
            response.headers["Strict-Transport-Security"] = HSTS_HEADER

        # API-specific headers (non-HTML responses)
        content_type = response.headers.get("content-type", "")
        if "text/html" not in content_type:
            response.headers["Cache-Control"] = API_CACHE_CONTROL
            response.headers["Content-Security-Policy"] = API_CSP

        return response


# ---------------------------------------------------------------------------
# 2. RequestSizeLimitMiddleware
# ---------------------------------------------------------------------------


class RequestSizeLimitMiddleware:
    """Reject requests whose Content-Length exceeds the allowed limit.

    * Regular requests: *max_body_size* (default 10 MB).
    * ``multipart/form-data`` (file uploads): *max_upload_size* (default 50 MB).

    Implemented as a pure ASGI middleware (no BaseHTTPMiddleware) so the
    body is **not** buffered -- we simply inspect the Content-Length header.
    """

    def __init__(
        self,
        app: ASGIApp,
        max_body_size: int = MAX_REQUEST_BODY_SIZE,
        max_upload_size: int = MAX_UPLOAD_SIZE,
    ) -> None:
        self.app = app
        self.max_body_size = max_body_size
        self.max_upload_size = max_upload_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(
            (k.lower(), v)
            for k, v in (
                (k.decode("latin-1"), v.decode("latin-1"))
                for k, v in scope.get("headers", [])
            )
        )

        content_length_str = headers.get("content-length", "")
        content_type = headers.get("content-type", "")

        if content_length_str:
            try:
                content_length = int(content_length_str)
            except (ValueError, TypeError):
                content_length = 0

            is_upload = "multipart/form-data" in content_type
            limit = self.max_upload_size if is_upload else self.max_body_size

            if content_length > limit:
                response = JSONResponse(
                    status_code=413,
                    content={
                        "detail": "Request body too large",
                        "max_bytes": limit,
                    },
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# 3. InputSanitizer (utility class, NOT middleware)
# ---------------------------------------------------------------------------

# Pre-compiled patterns
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_UUID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")


class InputSanitizer:
    """Stateless utility for input validation / sanitization.

    All methods are *class methods* so the class never needs instantiation.
    """

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Strip null bytes and ASCII control characters (except newline/tab)."""
        if not isinstance(value, str):
            return str(value)
        return _CONTROL_CHARS_RE.sub("", value)

    @staticmethod
    def sanitize_sql_identifier(value: str) -> str:
        """Allow only ``[A-Za-z_][A-Za-z0-9_]*``.

        Raises ``ValueError`` if the identifier is invalid.
        """
        value = value.strip()
        if not _SQL_IDENTIFIER_RE.match(value):
            raise ValueError(
                "Invalid SQL identifier: only alphanumeric and underscore allowed"
            )
        return value

    @staticmethod
    def validate_uuid(value: str) -> str:
        """Return *value* unchanged if it is a valid UUID, else raise ``ValueError``."""
        value = value.strip()
        if not _UUID_RE.match(value):
            raise ValueError("Invalid UUID format")
        return value

    @staticmethod
    def sanitize_path(value: str) -> str:
        """Prevent path traversal attacks.

        Rejects ``..`` components and absolute paths.
        Raises ``ValueError`` on violation.
        """
        if not isinstance(value, str):
            raise ValueError("Path must be a string")
        value = value.strip()
        # Reject absolute paths (Unix & Windows)
        if value.startswith("/") or value.startswith("\\"):
            raise ValueError("Absolute paths are not allowed")
        if re.match(r"^[A-Za-z]:\\", value) or re.match(r"^[A-Za-z]:/", value):
            raise ValueError("Absolute paths are not allowed")
        # Reject traversal
        parts = re.split(r"[/\\]", value)
        if ".." in parts:
            raise ValueError("Path traversal (..) is not allowed")
        return value

    @staticmethod
    def sanitize_html(value: str) -> str:
        """Strip HTML tags (basic regex-based removal)."""
        if not isinstance(value, str):
            return str(value)
        return _HTML_TAG_RE.sub("", value)


# ---------------------------------------------------------------------------
# 4. AuditLogMiddleware
# ---------------------------------------------------------------------------

_STATE_CHANGING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuditLogMiddleware(BaseHTTPMiddleware):
    """Log state-changing requests in structured JSON for banking compliance.

    Captures: timestamp, method, path, user_id (JWT), status_code, duration_ms.
    Logging is fire-and-forget -- failures never block the response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method
        if method not in _STATE_CHANGING_METHODS:
            return await call_next(request)

        start = time.monotonic()
        response: Response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 2)

        try:
            user_id = self._extract_user_id(request)
            client_ip = self._extract_client_ip(request)
            log_entry = {
                "event": "audit",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "method": method,
                "path": request.url.path,
                "user_id": user_id,
                "ip": client_ip,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "request_id": getattr(request.state, "request_id", None),
            }
            _audit_logger.info(json.dumps(log_entry, ensure_ascii=False))
        except Exception:
            # Fire-and-forget: never block the response
            pass

        return response

    @staticmethod
    def _extract_user_id(request: Request) -> Optional[str]:
        """Best-effort extraction of user_id from JWT (no verification)."""
        token = ""

        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]

        if not token:
            token = request.cookies.get("bgts_access_token", "")
        if not token:
            return None

        try:
            import base64

            # JWT is header.payload.signature -- decode the payload
            parts = token.split(".")
            if len(parts) < 2:
                return None
            # Add padding
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload = json.loads(payload_bytes)
            return payload.get("sub") or payload.get("user_id")
        except Exception:
            return None

    @staticmethod
    def _extract_client_ip(request: Request) -> Optional[str]:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            # x-forwarded-for: "<client>, <proxy>, ..."
            return forwarded_for.split(",")[0].strip()
        if request.client:
            return request.client.host
        return None
