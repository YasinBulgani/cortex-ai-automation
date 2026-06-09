"""FastAPI middleware to extract/inject correlation IDs.

A-MED-1: Correlation ID propagation for request tracing.
"""

import logging
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.infra.correlation_context import (
    generate_correlation_id,
    get_correlation_id,
    set_correlation_id,
)

logger = logging.getLogger(__name__)

CORRELATION_HEADER = "X-Correlation-ID"
CORRELATION_RESPONSE_HEADER = "X-Correlation-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Extract correlation ID from request header or generate new one.

    Flow:
    1. Read X-Correlation-ID from request
    2. If missing, generate new UUID
    3. Store in contextvars (async-safe)
    4. Inject into response header
    5. Available in all downstream service calls
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with correlation ID tracking."""
        # 1. Extract from header or generate
        corr_id = request.headers.get(CORRELATION_HEADER)
        if not corr_id:
            corr_id = generate_correlation_id()

        # 2. Set in context (async-safe)
        set_correlation_id(corr_id)

        # 3. Log with correlation ID
        logger.info(
            "%s %s [%s]",
            request.method,
            request.url.path,
            corr_id,
            extra={"correlation_id": corr_id},
        )

        try:
            # 4. Process request (all downstream code has access via get_correlation_id())
            response = await call_next(request)
        except Exception as exc:
            logger.exception(
                "Request failed: %s %s",
                request.method,
                request.url.path,
                extra={"correlation_id": corr_id},
            )
            raise

        # 5. Inject into response
        response.headers[CORRELATION_RESPONSE_HEADER] = corr_id

        return response
