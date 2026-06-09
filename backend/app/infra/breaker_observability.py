"""Circuit breaker observability with OTel spans (Faz 3.4).

Decorators + context managers to emit OTel spans for:
    - Circuit state transitions (CLOSED → OPEN → HALF_OPEN)
    - Failure counts + last failure timestamp
    - Retry-after duration
    - Per-breaker resource + error metrics

USAGE:
    from app.infra.breaker_observability import track_breaker_span

    breaker = get_breaker("ai-gateway")
    with track_breaker_span(breaker, "ai.complete_prompt"):
        try:
            breaker.before_call()
            response = await ai_gateway.complete(...)
            breaker.record_success()
            return response
        except Exception as exc:
            breaker.record_failure()
            raise

OTel Attributes emitted:
    - circuit.name: Breaker identifier
    - circuit.state: "closed" | "open" | "half_open"
    - circuit.failure_count: Number of consecutive failures
    - circuit.failure_threshold: Threshold for OPEN
    - circuit.reset_timeout: Duration before HALF_OPEN transition
    - circuit.last_failure_time: ISO timestamp or null
    - circuit.retry_after: Seconds to wait if OPEN
    - circuit.resource: e.g., "ai-gateway", "engine"
    - error.type: Exception class name if failure
    - error.message: Exception message if failure
"""

from __future__ import annotations

import asyncio
import contextlib
import functools
import logging
import time
from collections.abc import Callable, Iterator
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


@contextlib.contextmanager
def track_breaker_span(
    breaker: Any,  # CircuitBreaker instance
    operation_name: str,
    resource: Optional[str] = None,
) -> Iterator[Any]:
    """Context manager to emit OTel span for circuit breaker operation.

    Emits attributes before + after call:
        Before: circuit.state, circuit.failure_count, circuit.reset_timeout
        After: circuit.state (if changed), error.type, error.message

    Args:
        breaker: CircuitBreaker instance (from app.infra.resilience).
        operation_name: Span name, e.g., "ai.complete_prompt".
        resource: Resource identifier (e.g., "ai-gateway"). If None, uses breaker.name.

    Yields:
        The span object (or None if OTel disabled).

    Example:
        with track_breaker_span(breaker, "ai.complete", resource="ai-gateway"):
            breaker.before_call()
            response = await ai_gateway.call(...)
            breaker.record_success()
    """
    from app.infra.telemetry import set_span_attr, trace_span

    resource_name = resource or getattr(breaker, "name", "unknown")
    start_time = time.monotonic()

    with trace_span(
        operation_name,
        attrs={
            "circuit.name": getattr(breaker, "name", "unknown"),
            "circuit.resource": resource_name,
        },
    ) as span:
        # Record pre-call state
        try:
            state = breaker.state.value if hasattr(breaker.state, "value") else str(breaker.state)
            set_span_attr("circuit.state", state)
            set_span_attr(
                "circuit.failure_count",
                getattr(breaker, "_consecutive_failures", 0),
            )
            set_span_attr(
                "circuit.failure_threshold",
                getattr(breaker, "failure_threshold", 5),
            )
            set_span_attr(
                "circuit.reset_timeout",
                getattr(breaker, "reset_timeout", 30.0),
            )
        except Exception:
            pass

        try:
            yield span
        except Exception as exc:
            # Record exception in span
            try:
                set_span_attr("error.type", type(exc).__name__)
                set_span_attr("error.message", str(exc)[:200])
            except Exception:
                pass
            raise
        finally:
            # Record post-call state + duration
            try:
                state = breaker.state.value if hasattr(breaker.state, "value") else str(breaker.state)
                set_span_attr("circuit.state_final", state)
                duration_ms = (time.monotonic() - start_time) * 1000
                set_span_attr("duration_ms", duration_ms)
            except Exception:
                pass


def otel_breaker_call(
    breaker_name: str = "default",
    operation_name: Optional[str] = None,
) -> Callable[[F], F]:
    """Decorator to wrap function call with circuit breaker observability.

    Automatically:
    1. Gets breaker by name (from registry)
    2. Checks before_call() + emits span
    3. Records success/failure
    4. Handles CircuitBreakerOpen exception

    Args:
        breaker_name: Registered circuit breaker name (e.g., "ai-gateway").
        operation_name: Span name (default: f"{module}.{function_name}").

    Returns:
        Decorator function.

    Example:
        @otel_breaker_call("ai-gateway", "ai.complete_prompt")
        async def call_ai_gateway(prompt: str) -> str:
            return await ai_gateway.complete(prompt)
    """

    def _decorator(fn: F) -> F:
        from app.infra.resilience import CircuitBreakerOpen, get_breaker

        span_name = (
            operation_name
            or f"{fn.__module__}.{fn.__qualname__}"
        )

        @functools.wraps(fn)
        def _sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            breaker = get_breaker(breaker_name)
            with track_breaker_span(breaker, span_name, resource=breaker_name):
                try:
                    breaker.before_call()
                    result = fn(*args, **kwargs)
                    breaker.record_success()
                    return result
                except CircuitBreakerOpen:
                    raise
                except Exception:
                    breaker.record_failure()
                    raise

        @functools.wraps(fn)
        async def _async_wrapper(*args: Any, **kwargs: Any) -> Any:
            from app.infra.resilience import CircuitBreakerOpen, get_breaker

            breaker = get_breaker(breaker_name)
            with track_breaker_span(breaker, span_name, resource=breaker_name):
                try:
                    breaker.before_call()
                    result = await fn(*args, **kwargs)
                    breaker.record_success()
                    return result
                except CircuitBreakerOpen:
                    raise
                except Exception:
                    breaker.record_failure()
                    raise

        # Return correct wrapper based on async/sync
        if asyncio.iscoroutinefunction(fn):
            return _async_wrapper  # type: ignore[return-value]
        else:
            return _sync_wrapper  # type: ignore[return-value]

    return _decorator


@contextlib.contextmanager
def breaker_call(
    breaker: Any,  # CircuitBreaker instance
    *,
    operation_name: str = "breaker_call",
    reraise_open: bool = True,
) -> Iterator[None]:
    """Simple context manager for circuit breaker call tracking.

    Calls before_call() + records success/failure + emits span.

    Args:
        breaker: CircuitBreaker instance.
        operation_name: Span name.
        reraise_open: If True, reraise CircuitBreakerOpen; else swallow it.

    Yields:
        None.

    Raises:
        CircuitBreakerOpen if breaker is OPEN (and reraise_open=True).

    Example:
        try:
            with breaker_call(breaker, operation_name="ai.complete"):
                response = await ai_gateway.complete(prompt)
        except CircuitBreakerOpen:
            return cached_response()  # Fallback
    """
    from app.infra.resilience import CircuitBreakerOpen
    from app.infra.telemetry import trace_span

    with track_breaker_span(breaker, operation_name) as span:
        try:
            breaker.before_call()
            yield
            breaker.record_success()
        except CircuitBreakerOpen:
            if reraise_open:
                raise
            else:
                # Swallow CircuitBreakerOpen exception
                pass
        except Exception:
            breaker.record_failure()
            raise
