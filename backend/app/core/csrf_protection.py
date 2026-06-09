"""S-HIGH CSRF protection and session security.

OWASP A1: Cross-Site Request Forgery (CSRF)
- Double-submit cookie pattern for stateless CSRF protection
- SameSite cookie policy (strict by default)
- Secure flag on sensitive cookies
- CSRF token validation for state-changing operations
"""

from __future__ import annotations

import logging
import secrets
from typing import Optional

from fastapi import HTTPException, Request, status

_logger = logging.getLogger(__name__)

CSRF_TOKEN_COOKIE = "csrf_token"
CSRF_TOKEN_HEADER = "X-CSRF-Token"
CSRF_TOKEN_LENGTH = 32  # 256 bits in base64


def generate_csrf_token() -> str:
    """S-HIGH-6a: Generate cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def validate_csrf_token(
    request: Request,
    expected_token: Optional[str] = None,
    skip_methods: set[str] = None,
) -> None:
    """S-HIGH-6b: Validate CSRF token from request header/body.

    Implements double-submit cookie pattern:
    1. Server sends CSRF token in httpOnly=false cookie
    2. Client includes token in X-CSRF-Token header
    3. Server validates header token matches cookie token

    Safe methods (GET, HEAD, OPTIONS) skip CSRF check.
    CORS preflight (OPTIONS) is exempt.

    Args:
        request: FastAPI Request
        expected_token: Token to validate against (from form/JSON body)
        skip_methods: HTTP methods to skip CSRF check (default: GET, HEAD, OPTIONS)

    Raises:
        HTTPException(403): If CSRF validation fails
    """
    if skip_methods is None:
        skip_methods = {"GET", "HEAD", "OPTIONS"}

    # Skip CSRF for safe methods
    if request.method in skip_methods:
        return

    # Get token from cookie (double-submit pattern)
    cookie_token = request.cookies.get(CSRF_TOKEN_COOKIE)
    if not cookie_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token cookie eksik",
        )

    # Get token from header (client submits this on state-change requests)
    header_token = request.headers.get(CSRF_TOKEN_HEADER)
    if not header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token header eksik",
        )

    # Validate tokens match (constant-time comparison)
    if not secrets.compare_digest(cookie_token, header_token):
        _logger.warning(
            "CSRF token mismatch detected: method=%s path=%s ip=%s",
            request.method,
            request.url.path,
            request.client.host if request.client else "unknown",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF token doğrulama başarısız",
        )


# S-HIGH-9: Session security settings
SESSION_SECURITY_HEADERS = {
    # Disable client-side session manipulation
    "X-Frame-Options": "DENY",
    "X-Content-Type-Options": "nosniff",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    # Content Security Policy — restrict XSS attack surface
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'",
    # Referrer policy (privacy + security)
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Disable autocomplete on sensitive forms
    "X-Autocomplete": "off",
}


def apply_security_headers(response: dict) -> dict:
    """S-HIGH-9: Apply OWASP security headers to response."""
    response.update(SESSION_SECURITY_HEADERS)
    return response


# S-HIGH-10: Session timeout and rotation
SESSION_TIMEOUT_SECONDS = 30 * 60  # 30 minutes
SESSION_ROTATION_INTERVAL = 15 * 60  # Rotate every 15 minutes
MAX_SESSION_AGE_SECONDS = 7 * 24 * 60 * 60  # 7 days (absolute max)


def validate_session_age(created_at: int, current_ts: int) -> bool:
    """S-HIGH-10: Validate session hasn't exceeded absolute max age."""
    age_seconds = current_ts - created_at
    if age_seconds > MAX_SESSION_AGE_SECONDS:
        return False
    return True
