"""Core OTel helpers — no-op when SDK is absent."""

from __future__ import annotations

import contextlib
import functools
import logging
import os
from typing import Any, Callable, Dict, Iterator, Optional, TypeVar

logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])

_OTEL_AVAILABLE: Optional[bool] = None
_TRACER: Any = None
_SERVICE_NAME: str = "neurex-service"


def _is_available() -> bool:
    global _OTEL_AVAILABLE
    if _OTEL_AVAILABLE is not None:
        return _OTEL_AVAILABLE
    try:
        from opentelemetry import trace  # noqa: F401
        _OTEL_AVAILABLE = True
    except ImportError:
        _OTEL_AVAILABLE = False
    return _OTEL_AVAILABLE


def _get_tracer() -> Any:
    global _TRACER
    if _TRACER is not None:
        return _TRACER
    if not _is_available():
        return None
    try:
        from opentelemetry import trace
        _TRACER = trace.get_tracer(_SERVICE_NAME)
        return _TRACER
    except Exception as exc:
        logger.debug("otel tracer unavailable: %s", exc)
        return None


def is_enabled() -> bool:
    if os.environ.get("OTEL_SDK_DISABLED", "").lower() in ("1", "true", "yes"):
        return False
    return _is_available()


@contextlib.contextmanager
def trace_span(
    name: str, *, attrs: Optional[Dict[str, Any]] = None
) -> Iterator[Any]:
    if not is_enabled():
        yield None
        return
    tracer = _get_tracer()
    if tracer is None:
        yield None
        return
    try:
        with tracer.start_as_current_span(name) as span:
            if attrs:
                for k, v in attrs.items():
                    _safe_set(span, k, v)
            try:
                yield span
            except Exception as exc:
                try:
                    from opentelemetry.trace import Status, StatusCode
                    span.set_status(Status(StatusCode.ERROR, description=str(exc)[:200]))
                    span.record_exception(exc)
                except Exception:
                    pass
                raise
    except Exception as exc:
        logger.debug("otel span error (silent): %s", exc)
        yield None


def set_span_attr(key: str, value: Any) -> None:
    if not is_enabled():
        return
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span:
            _safe_set(span, key, value)
    except Exception as exc:
        logger.debug("otel set_span_attr error: %s", exc)


def _safe_set(span: Any, key: str, value: Any) -> None:
    if value is None:
        return
    try:
        if isinstance(value, (bool, int, float, str)):
            span.set_attribute(key, value)
        else:
            span.set_attribute(key, str(value)[:1000])
    except Exception:
        pass


def traced(name: Optional[str] = None) -> Callable[[F], F]:
    def _decorator(fn: F) -> F:
        span_name = name or f"{fn.__module__}.{fn.__qualname__}"

        @functools.wraps(fn)
        def _wrap(*args: Any, **kwargs: Any) -> Any:
            with trace_span(span_name):
                return fn(*args, **kwargs)

        return _wrap  # type: ignore[return-value]

    return _decorator


def init_otel(
    *,
    service_name: str = "neurex-service",
    endpoint: Optional[str] = None,
    instrument_fastapi: bool = False,
    instrument_flask: bool = False,
    instrument_sqlalchemy: bool = False,
    instrument_redis: bool = False,
    fastapi_app: Any = None,
    flask_app: Any = None,
) -> bool:
    """Initialize OTel SDK. Returns False if SDK is not installed."""
    global _SERVICE_NAME, _TRACER
    _SERVICE_NAME = service_name
    _TRACER = None  # reset so _get_tracer picks up new service name

    if not _is_available():
        logger.info("otel: api package not installed, skipping init")
        return False

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

        resource = Resource.create({
            "service.name": service_name,
            "deployment.environment": os.environ.get("APP_ENV", "development"),
        })
        provider = TracerProvider(resource=resource)

        otlp_endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            except ImportError:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        if instrument_fastapi and fastapi_app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(fastapi_app)
            except ImportError:
                pass

        if instrument_flask and flask_app is not None:
            try:
                from opentelemetry.instrumentation.flask import FlaskInstrumentor
                FlaskInstrumentor().instrument_app(flask_app)
            except ImportError:
                pass

        if instrument_sqlalchemy:
            try:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                SQLAlchemyInstrumentor().instrument()
            except ImportError:
                pass

        if instrument_redis:
            try:
                from opentelemetry.instrumentation.redis import RedisInstrumentor
                RedisInstrumentor().instrument()
            except ImportError:
                pass

        logger.info(
            "otel: init OK (service=%s, endpoint=%s)",
            service_name,
            otlp_endpoint or "console",
        )
        return True

    except Exception as exc:
        logger.warning("otel init failed: %s", exc)
        return False
