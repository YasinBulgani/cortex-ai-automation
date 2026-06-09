"""
Multi-tenant middleware — sets Postgres session variable for RLS.

Flow:
  1. Extract tenant_id from JWT payload (`tenant` claim)
  2. For each DB connection in this request: `SET LOCAL app.current_tenant = '<uuid>'`
  3. All subsequent queries filtered by RLS policy automatically

Security:
  - Authenticated requests MUST contain a tenant claim; missing claim raises ValueError
  - Unauthenticated requests (no token) fall back to default tenant for health checks, etc.
  - Invalid tenant UUIDs are rejected and logged
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"
_SAFE_UUID_CHARS = frozenset("0123456789abcdefABCDEF-")


def _safe_tenant_id(raw: str | None, allow_missing: bool = False) -> str:
    """Validate UUID format — never trust raw user input in SQL SET.

    Args:
        raw: The tenant ID string to validate
        allow_missing: If False, raise ValueError when raw is None or empty.
                       If True, return DEFAULT_TENANT when missing.

    Raises:
        ValueError: If allow_missing=False and tenant claim is missing/invalid
    """
    if not raw:
        if not allow_missing:
            raise ValueError("Tenant claim is missing from authenticated request")
        return _DEFAULT_TENANT
    cleaned = raw.strip()
    if len(cleaned) != 36 or not all(c in _SAFE_UUID_CHARS for c in cleaned):
        logger.error("Invalid tenant_id format in token: %r", cleaned)
        if not allow_missing:
            raise ValueError(f"Invalid tenant UUID format: {cleaned}")
        return _DEFAULT_TENANT
    return cleaned.lower()


def extract_tenant_from_token(token: str | None) -> str:
    """Parse JWT and extract tenant claim WITHOUT signature verification (for middleware speed).
    Full verification already done by get_current_user dependency.

    Args:
        token: The JWT token string (from Authorization header or cookie)

    Returns:
        Tenant ID (either from token claim or DEFAULT_TENANT)

    Raises:
        ValueError: If token exists but is malformed or lacks tenant claim
    """
    if not token:
        # No token = unauthenticated request (public endpoint, health check, etc.)
        return _DEFAULT_TENANT

    try:
        import base64
        import json
        parts = token.split(".")
        if len(parts) != 3:
            logger.error("SECURITY: Malformed JWT in request (expected 3 parts, got %d)", len(parts))
            raise ValueError(f"Malformed JWT: expected 3 parts, got {len(parts)}")

        # Pad base64
        payload_b64 = parts[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        tenant = payload.get("tenant") or payload.get("tenant_id")

        if not tenant:
            # Authenticated request (token provided) but missing tenant claim
            logger.error("SECURITY: Authenticated request missing tenant claim in JWT payload")
            raise ValueError("Tenant claim missing from JWT")

        # Validate the tenant UUID format
        cleaned = tenant.strip()
        if len(cleaned) != 36 or not all(c in _SAFE_UUID_CHARS for c in cleaned):
            logger.error("SECURITY: Invalid tenant UUID format in JWT: %r", cleaned)
            raise ValueError(f"Invalid tenant UUID format: {cleaned}")

        return cleaned.lower()
    except ValueError:
        # Re-raise ValueError (our validation errors)
        raise
    except Exception as e:
        logger.error("SECURITY: Unable to parse JWT for tenant extraction: %s", e)
        raise ValueError(f"Invalid JWT: {e}")


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Stores tenant_id in request.state so the DB session layer can pick it up.

    Security:
    - Unauthenticated requests get DEFAULT_TENANT (for health checks, public endpoints)
    - Authenticated requests (token provided) MUST have valid tenant claim or request is rejected
    - This prevents silent fallback to default tenant for authenticated users

    Usage in route:
        async def my_route(request: Request, session: AsyncSession = Depends(get_session)):
            tenant = request.state.tenant_id
            await session.execute(text(f"SET LOCAL app.current_tenant = :t"), {"t": tenant})
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Extract from Authorization header (Bearer token)
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip() if auth.startswith("Bearer ") else None

        # Fall back to HttpOnly access-token cookie (set by /auth/login)
        if not token:
            token = request.cookies.get("bgts_access_token") or request.cookies.get("access_token")

        try:
            tenant_id = extract_tenant_from_token(token)
            request.state.tenant_id = tenant_id
        except ValueError as e:
            # Token exists but is invalid or missing tenant claim
            # This indicates a security issue or malformed token
            logger.error("SECURITY: Rejecting request due to invalid tenant claim: %s", e)
            from starlette.responses import JSONResponse
            return JSONResponse(
                {"detail": "Invalid or missing tenant claim in authentication token"},
                status_code=403
            )

        response = await call_next(request)
        return response


# ─── SQLAlchemy event hook to inject SET LOCAL ───────────────────────────────
# Register this in your DB session factory to auto-set tenant for every
# connection checked out of the pool.

async def set_tenant_on_connect(dbapi_connection, tenant_id: str) -> None:
    """Execute SET LOCAL before any query in a request.

    Validates tenant_id format before SQL execution — defence-in-depth.
    """
    try:
        # Validate UUID format before interpolation — allow missing (fallback to default)
        safe_id = _safe_tenant_id(tenant_id, allow_missing=True)
        await dbapi_connection.execute(f"SET LOCAL app.current_tenant = '{safe_id}'")
    except Exception as e:
        logger.error("Failed to set tenant on connection: %s", e)
        raise
