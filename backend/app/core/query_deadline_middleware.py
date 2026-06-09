"""Query deadline middleware for pool exhaustion prevention.

Manages request-scoped query timeout context.
Sets deadline at request start, clears at request end.
"""

from __future__ import annotations

import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.infra.query_deadline import clear_request_deadline, set_request_deadline

logger = logging.getLogger(__name__)


class QueryDeadlineMiddleware(BaseHTTPMiddleware):
    """Track query deadline per request to prevent pool exhaustion.

    Sets request-scoped deadline context variable at the start of each
    request. Deadline is cleared after response is sent.
    """

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Set deadline, process request, clear deadline."""
        # Set deadline for this request
        set_request_deadline(settings.query_timeout_sec)

        try:
            response: Response = await call_next(request)
            return response
        finally:
            # Always clear deadline after request completes
            clear_request_deadline()
