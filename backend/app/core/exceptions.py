"""Custom exception hierarchy for the Neurex backend.

All domain services raise these instead of FastAPI HTTPException.
Exception handlers in app/core/exception_handlers.py map them to HTTP responses.

Mapping:
    ValueError        → 400 Bad Request
    KeyError          → 404 Not Found
    PermissionError   → 403 Forbidden
    RateLimitError    → 429 Too Many Requests
    RuntimeError      → 500 Internal Server Error
"""
from __future__ import annotations


class RateLimitError(Exception):
    """Raised when a user exceeds request or token rate limits.

    Maps to HTTP 429 Too Many Requests via exception_handlers.py.
    """

    def __init__(self, message: str, retry_after_seconds: int = 60) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds
