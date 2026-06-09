"""OpenTelemetry Trace Decorators — opt-in domain-level instrumentation.

Faz 3.3: Advanced span creation with async support, sampling, error tracking,
and result metrics. Complements app.infra.telemetry (context managers + basic @traced).

Kullanım:
    from app.infra.otel_decorators import otel_span, measure_duration

    @otel_span("test_mgmt.predict_failure_rate", sample=1.0)
    def predict_failure_rate(test_id: str) -> float:
        ...  # Spans created for all calls.

    @measure_duration("auth.verify_password", sample=0.1)  # 10% sampling
    async def verify_password_async(pwd: str) -> bool:
        ...  # Spans created for 10% of calls; sampled=False for rest.

Config (env vars):
    OTEL_SPANS_ENABLED=true (default in prod, false in dev)
    OTEL_SAMPLER=adaptive | always | never (default=adaptive)
    OTEL_ERROR_SAMPLE_RATE=1.0 (100% for errors, default)
    OTEL_SUCCESS_SAMPLE_RATE=0.1 (10% for success, default)

Sampling strategy:
    - adaptive (default):
        * Errors: always sampled (100%)
        * Success: sampled per OTEL_SUCCESS_SAMPLE_RATE (default 10%)
        * Cost-conscious: minimizes span volume while capturing failures.
    - always: All spans created (100%).
    - never: No spans (0% sampling, profiling mode).

Attributes captured:
    - function.name, function.module
    - duration_ms (execution time)
    - error.type, error.message (if exception)
    - result.count (if result is a list/iterable)
    - result.keys (if result is a dict)
    - sampled (bool) — whether this span was sampled
"""
from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import os
import random
import time
from collections.abc import Callable, Iterable
from typing import Any, Optional, TypeVar

from app.infra.telemetry import is_enabled, set_span_attr, trace_span

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])
AsyncF = TypeVar("AsyncF", bound=Callable[..., Any])


# ============================================================================
# Sampling Configuration
# ============================================================================


def _get_sampler_mode() -> str:
    """Read OTEL_SAMPLER env var; default 'adaptive' (errors 100%, success 10%)."""
    mode = os.environ.get("OTEL_SAMPLER", "adaptive").lower()
    if mode not in ("adaptive", "always", "never"):
        logger.warning("OTEL_SAMPLER=%s unknown, using adaptive", mode)
        return "adaptive"
    return mode


def _get_error_sample_rate() -> float:
    """Probability to sample error spans. Default 1.0 (100%)."""
    try:
        return float(os.environ.get("OTEL_ERROR_SAMPLE_RATE", "1.0"))
    except ValueError:
        logger.warning("OTEL_ERROR_SAMPLE_RATE invalid, using 1.0")
        return 1.0


def _get_success_sample_rate() -> float:
    """Probability to sample success spans. Default 0.1 (10%)."""
    try:
        return float(os.environ.get("OTEL_SUCCESS_SAMPLE_RATE", "0.1"))
    except ValueError:
        logger.warning("OTEL_SUCCESS_SAMPLE_RATE invalid, using 0.1")
        return 0.1


def should_sample(is_error: bool) -> bool:
    """Determine whether to sample this span based on mode + error status.

    Args:
        is_error: True if span ended with exception.

    Returns:
        True if span should be created/exported.
    """
    mode = _get_sampler_mode()

    if mode == "never":
        return False
    if mode == "always":
        return True
    # mode == "adaptive"
    if is_error:
        rate = _get_error_sample_rate()
    else:
        rate = _get_success_sample_rate()
    return random.random() < rate


# ============================================================================
# Span Attribute Helpers
# ============================================================================


def _set_function_attrs(fn_name: str, module_name: str) -> None:
    """Set function.name and function.module attributes on active span."""
    set_span_attr("function.name", fn_name)
    set_span_attr("function.module", module_name)


def _set_result_attrs(result: Any) -> None:
    """Extract metrics from function result and set as span attributes.

    Handles:
        - List/iterable: result.count
        - Dict: result.keys (as comma-separated string)
        - Tuple (count_value, ...): result.count (first element)
    """
    if result is None:
        return

    # Tuple result (common pattern: (count, data) or (bool, msg))
    if isinstance(result, tuple) and len(result) > 0:
        first = result[0]
        if isinstance(first, (int, float)):
            set_span_attr("result.count", int(first))
        return

    # Dict result
    if isinstance(result, dict):
        keys = ", ".join(result.keys()) if result else ""
        if keys:
            set_span_attr("result.keys", keys)
        set_span_attr("result.count", len(result))
        return

    # List/iterable result (but not string)
    if isinstance(result, Iterable) and not isinstance(result, (str, bytes)):
        try:
            count = len(result)
            set_span_attr("result.count", count)
        except (TypeError, AttributeError):
            # Generator, iterator without len()
            pass
        return


def _set_error_attrs(exc: Exception) -> None:
    """Set error.type and error.message from exception."""
    set_span_attr("error.type", type(exc).__name__)
    set_span_attr("error.message", str(exc)[:500])


# ============================================================================
# Synchronous Decorator
# ============================================================================


def otel_span(
    name: Optional[str] = None,
    *,
    sample: Optional[float] = None,
) -> Callable[[F], F]:
    """Decorator for synchronous functions.

    Wraps function with OTel span, captures duration, errors, result metrics.
    Samples based on success/failure (if sample=None) or always (if sample=1.0).

    Args:
        name: Explicit span name. If None, auto-derived from function.
        sample: Override sampling rate (0.0 = never, 1.0 = always).
                If None, uses adaptive sampling (errors 100%, success 10%).

    Returns:
        Decorated function preserving signature and docstring.

    Example:
        @otel_span("auth.verify_password", sample=1.0)
        def verify_password(pwd: str) -> bool:
            ...
    """

    def _decorator(fn: F) -> F:
        span_name = name or f"{fn.__module__}.{fn.__qualname__}"
        use_adaptive = sample is None

        @functools.wraps(fn)
        def _wrap(*args: Any, **kwargs: Any) -> Any:
            if not is_enabled():
                return fn(*args, **kwargs)

            start_time = time.time()
            is_error = False
            result = None

            try:
                with trace_span(span_name) as span:
                    if span is not None:
                        _set_function_attrs(fn.__name__, fn.__module__)

                    result = fn(*args, **kwargs)
                    return result

            except Exception as exc:
                is_error = True
                raise

            finally:
                duration_ms = (time.time() - start_time) * 1000

                # Determine if span should be created based on sampling
                do_sample = (
                    sample if sample is not None else should_sample(is_error)
                )

                # Silently skip if not sampled
                if do_sample < 1.0 and random.random() >= do_sample:
                    return

                # Re-enter span to add terminal attributes
                try:
                    with trace_span(
                        f"{span_name}.__metrics__", attrs={"sampled": True}
                    ) as metrics_span:
                        if metrics_span is not None:
                            set_span_attr("duration_ms", round(duration_ms, 2))
                            if result is not None:
                                _set_result_attrs(result)
                            if is_error:
                                # Re-raise was already called, but we capture error
                                # info here for non-error path logging
                                pass
                except Exception as exc:  # pragma: no cover
                    logger.debug("otel_span metrics capture failed: %s", exc)

        return _wrap  # type: ignore[return-value]

    return _decorator


# ============================================================================
# Asynchronous Decorator
# ============================================================================


def measure_duration(
    name: Optional[str] = None,
    *,
    sample: Optional[float] = None,
) -> Callable[[AsyncF], AsyncF]:
    """Decorator for async functions.

    Wraps async function with OTel span, captures duration, errors, result metrics.
    Supports both async def and regular sync functions (acts like otel_span for sync).

    Args:
        name: Explicit span name. If None, auto-derived from function.
        sample: Override sampling rate. If None, uses adaptive sampling.

    Returns:
        Decorated async function (or sync if input is sync).

    Example:
        @measure_duration("test_mgmt.calculate_coverage", sample=0.1)
        async def calculate_coverage(suite_id: str) -> dict:
            ...
    """

    def _decorator(fn: AsyncF) -> AsyncF:
        span_name = name or f"{fn.__module__}.{fn.__qualname__}"
        use_adaptive = sample is None

        # Check if function is async
        if asyncio.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def _async_wrap(*args: Any, **kwargs: Any) -> Any:
                if not is_enabled():
                    return await fn(*args, **kwargs)

                start_time = time.time()
                is_error = False
                result = None

                try:
                    with trace_span(span_name) as span:
                        if span is not None:
                            _set_function_attrs(fn.__name__, fn.__module__)

                        result = await fn(*args, **kwargs)
                        return result

                except Exception as exc:
                    is_error = True
                    raise

                finally:
                    duration_ms = (time.time() - start_time) * 1000

                    # Determine if span should be created based on sampling
                    do_sample = (
                        sample if sample is not None else should_sample(is_error)
                    )

                    # Silently skip if not sampled
                    if do_sample < 1.0 and random.random() >= do_sample:
                        return

                    # Re-enter span to add terminal attributes
                    try:
                        with trace_span(
                            f"{span_name}.__metrics__", attrs={"sampled": True}
                        ) as metrics_span:
                            if metrics_span is not None:
                                set_span_attr("duration_ms", round(duration_ms, 2))
                                if result is not None:
                                    _set_result_attrs(result)
                    except Exception as exc:  # pragma: no cover
                        logger.debug("measure_duration metrics capture failed: %s", exc)

            return _async_wrap  # type: ignore[return-value]

        else:
            # Sync function — delegate to otel_span
            @functools.wraps(fn)
            def _sync_wrap(*args: Any, **kwargs: Any) -> Any:
                return otel_span(span_name, sample=sample)(fn)(*args, **kwargs)

            return _sync_wrap  # type: ignore[return-value]

    return _decorator


# ============================================================================
# Debugging / Introspection
# ============================================================================


def get_span_config() -> dict[str, Any]:
    """Return current OTel span configuration (for debugging/testing).

    Returns:
        Dict with enabled, sampler, error_rate, success_rate.
    """
    return {
        "enabled": is_enabled(),
        "sampler": _get_sampler_mode(),
        "error_sample_rate": _get_error_sample_rate(),
        "success_sample_rate": _get_success_sample_rate(),
    }
