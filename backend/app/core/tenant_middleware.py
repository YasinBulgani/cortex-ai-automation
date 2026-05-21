"""
Multi-tenant middleware — sets Postgres session variable for RLS.

Flow:
  1. Extract tenant_id from JWT payload (`tenant` claim)
  2. For each DB connection in this request: `SET LOCAL app.current_tenant = '<uuid>'`
  3. All subsequent queries filtered by RLS policy automatically

Fallback: If no tenant claim → local dev tenant (all-zeros UUID).
"""

from __future__ import annotations

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_DEFAULT_TENANT = "00000000-0000-0000-0000-000000000001"
_SAFE_UUID_CHARS = frozenset("0123456789abcdefABCDEF-")


def _safe_tenant_id(raw: str | None) -> str:
    """Validate UUID format — never trust raw user input in SQL SET."""
    if not raw:
        return _DEFAULT_TENANT
    cleaned = raw.strip()
    if len(cleaned) != 36 or not all(c in _SAFE_UUID_CHARS for c in cleaned):
        logger.warning("Invalid tenant_id in token, using default: %r", cleaned)
        return _DEFAULT_TENANT
    return cleaned.lower()


def extract_tenant_from_token(token: str | None) -> str:
    """Parse JWT and extract tenant claim WITHOUT signature verification (for middleware speed).
    Full verification already done by get_current_user dependency."""
    if not token:
        return _DEFAULT_TENANT
    try:
        import base64, json
        parts = token.split(".")
        if len(parts) != 3:
            return _DEFAULT_TENANT
        # Pad base64
        payload_b64 = parts[1] + "=="
        payload = json.loads(base64.urlsafe_b64decode(payload_b64).decode())
        return _safe_tenant_id(payload.get("tenant") or payload.get("tenant_id"))
    except Exception:
        return _DEFAULT_TENANT


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Stores tenant_id in request.state so the DB session layer can pick it up.

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

        tenant_id = extract_tenant_from_token(token)
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        return response


# ─── SQLAlchemy event hook to inject SET LOCAL ───────────────────────────────
# Register this in your DB session factory to auto-set tenant for every
# connection checked out of the pool.

async def set_tenant_on_connect(dbapi_connection, tenant_id: str) -> None:
    """Execute SET LOCAL before any query in a request."""
    await dbapi_connection.execute(f"SET LOCAL app.current_tenant = '{tenant_id}'")
