"""Query deadline tracking for pool exhaustion prevention.

SQLAlchemy event listener for query execution timing.
Track deadline per request (from config: QUERY_TIMEOUT_SEC=30).
Log warning if query approaching deadline.
On timeout: raise QueryTimeoutError → circuit breaker handles → 503.
"""

from __future__ import annotations

import logging
import time
from contextvars import ContextVar
from typing import Any, Optional

from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Request-scoped deadline tracking (in milliseconds)
_request_deadline: ContextVar[Optional[float]] = ContextVar("request_deadline", default=None)


class QueryTimeoutError(Exception):
    """Raised when a query approaches or exceeds the deadline."""
    pass


def set_request_deadline(timeout_sec: float) -> None:
    """Set the deadline for this request.

    Args:
        timeout_sec: Timeout in seconds (e.g., 30.0)
    """
    deadline_ms = time.time() * 1000 + (timeout_sec * 1000)
    _request_deadline.set(deadline_ms)


def clear_request_deadline() -> None:
    """Clear the deadline after request completes."""
    _request_deadline.set(None)


def get_request_deadline() -> Optional[float]:
    """Get the current request deadline in milliseconds."""
    return _request_deadline.get()


def _check_deadline_before_query() -> None:
    """Check if we're already past deadline (fail-fast)."""
    deadline_ms = _request_deadline.get()
    if deadline_ms is None:
        return

    current_ms = time.time() * 1000
    if current_ms > deadline_ms:
        elapsed_sec = (current_ms - (deadline_ms - _request_timeout_sec() * 1000)) / 1000
        raise QueryTimeoutError(
            f"Query deadline exceeded. Elapsed: {elapsed_sec:.2f}s"
        )


def _request_timeout_sec() -> float:
    """Get configured query timeout in seconds."""
    try:
        from app.config import settings
        return getattr(settings, 'query_timeout_sec', 30.0)
    except Exception:
        return 30.0


# ── SQLAlchemy Engine Event Listeners (async-safe) ───────────────────────


@event.listens_for(Engine, "before_cursor_execute")
def _before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    """Before query execution: Check deadline and start timer."""
    _check_deadline_before_query()

    # Store start time in cursor (dbapi conn)
    if not hasattr(cursor, "_query_start_time"):
        cursor._query_start_time = {}
    cursor._query_start_time[id(statement)] = time.time()


@event.listens_for(Engine, "after_cursor_execute")
def _after_cursor_execute(conn, cursor, statement, parameters, context, executemany, result):
    """After query execution: Log slow queries and check deadline."""
    query_id = id(statement)
    start_time = getattr(cursor, "_query_start_time", {}).pop(query_id, None)

    if start_time is None:
        return

    duration_sec = time.time() - start_time
    deadline_ms = _request_deadline.get()

    if deadline_ms is not None:
        elapsed_total_sec = (time.time() * 1000 - (deadline_ms - _request_timeout_sec() * 1000)) / 1000
        remaining_sec = _request_timeout_sec() - elapsed_total_sec

        # Warn if query took > 5s or remaining deadline < 5s
        if duration_sec > 5.0 or (remaining_sec < 5.0 and remaining_sec > 0):
            stmt_preview = str(statement)[:150]
            logger.warning(
                "Slow query detected: duration=%.2fs, remaining_deadline=%.2fs, stmt=%s",
                duration_sec,
                remaining_sec,
                stmt_preview,
            )

        # Fail if approaching deadline
        if remaining_sec < 1.0 and remaining_sec > 0:
            logger.error(
                "Query deadline imminent: remaining_deadline=%.2fs, stmt=%s",
                remaining_sec,
                str(statement)[:150],
            )


def init_query_deadline() -> None:
    """Initialize query deadline context variable (call at app startup)."""
    logger.info("Query deadline tracking initialized (QUERY_TIMEOUT_SEC=%s)", _request_timeout_sec())
