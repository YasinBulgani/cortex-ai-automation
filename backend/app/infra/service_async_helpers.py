"""Helpers for async service layer refactoring.

A-MED-2: Service layer async patterns for 6 hot-path domains.

Pattern: Convert sync service methods to async with proper
- Database operation awaiting
- External call timeout handling
- Correlation ID propagation
- Structured logging
"""

import asyncio
import logging
from typing import Any, Awaitable, Callable, Optional, TypeVar

from app.infra.correlation_context import get_correlation_id

logger = logging.getLogger(__name__)

T = TypeVar('T')


class ServiceAsyncContext:
    """Track async operation context (correlation ID, start time, etc.)."""

    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.correlation_id = get_correlation_id()
        self.start_time: Optional[float] = None

    async def __aenter__(self):
        """Enter async context (start timing)."""
        import time
        self.start_time = time.time()
        logger.debug(
            "Async op START: %s [%s]",
            self.operation_name,
            self.correlation_id,
            extra={"correlation_id": self.correlation_id},
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context (log duration)."""
        if self.start_time:
            import time
            duration_ms = (time.time() - self.start_time) * 1000
            status = "OK" if exc_type is None else f"ERROR({exc_type.__name__})"
            logger.info(
                "Async op %s: %s [%s] %.1fms",
                status,
                self.operation_name,
                self.correlation_id,
                duration_ms,
                extra={"correlation_id": self.correlation_id},
            )


async def with_timeout(
    coro: Awaitable[T],
    timeout_sec: float = 30.0,
    operation: str = "operation",
) -> T:
    """Execute coroutine with timeout.

    Args:
        coro: Coroutine to execute
        timeout_sec: Timeout in seconds (clamped to [0.1, 120])
        operation: Name for logging

    Raises:
        asyncio.TimeoutError: If timeout exceeded
    """
    # Clamp timeout to reasonable bounds (prevent abuse)
    clamped = max(0.1, min(timeout_sec, 120.0))

    try:
        return await asyncio.wait_for(coro, timeout=clamped)
    except asyncio.TimeoutError:
        logger.warning(
            "Async timeout: %s after %.1fs [%s]",
            operation,
            clamped,
            get_correlation_id(),
        )
        raise


async def gather_with_correlation(*coros: Awaitable[Any], **kwargs) -> list[Any]:
    """Run multiple coroutines with correlation ID propagated.

    Preserves correlation_id in all sub-tasks.

    Args:
        *coros: Coroutines to gather
        **kwargs: Passed to asyncio.gather (return_exceptions, etc.)

    Returns:
        List of results (or exceptions if return_exceptions=True)
    """
    return await asyncio.gather(*coros, **kwargs)


def log_service_call(
    method_name: str,
    service_name: str,
    args: Optional[dict] = None,
) -> None:
    """Log service method call with correlation ID."""
    logger.debug(
        "Service call: %s.%s%s [%s]",
        service_name,
        method_name,
        f" args={args}" if args else "",
        get_correlation_id(),
        extra={
            "correlation_id": get_correlation_id(),
            "service": service_name,
            "method": method_name,
        },
    )
