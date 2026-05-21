"""OpenTelemetry helpers — opsiyonel bağımlılık, noop fallback.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §6 / E4.5 (cross-cutting).

Felsefe:
    ``opentelemetry-api`` kurulu değilse veya tracer kayıtlı değilse TÜM
    çağrılar sessizce noop. Hiçbir domain kodu import'un varlığını
    kontrol etmek zorunda kalmaz.

Kullanım:
    from app.infra.telemetry import trace_span, set_span_attr, traced

    with trace_span("coverup.heal.run", attrs={"run_id": rid}):
        set_span_attr("proposals_count", len(props))

    @traced("ai.record_usage")
    def record_usage(...):
        ...

Setup (main.py startup'ta opsiyonel):
    init_otel(service_name="testwright-backend")
"""
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


def _is_available() -> bool:
    global _OTEL_AVAILABLE
    if _OTEL_AVAILABLE is not None:
        return _OTEL_AVAILABLE
    try:
        from opentelemetry import trace  # type: ignore  # noqa: F401

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
        from opentelemetry import trace  # type: ignore

        _TRACER = trace.get_tracer("testwright-ai")
        return _TRACER
    except Exception as exc:  # pragma: no cover
        logger.debug("otel tracer alınamadı: %s", exc)
        return None


def is_enabled() -> bool:
    """OTel kurulu + ENV'de kapatılmamış mı?"""
    if os.environ.get("OTEL_SDK_DISABLED", "").lower() in ("1", "true", "yes"):
        return False
    return _is_available()


@contextlib.contextmanager
def trace_span(
    name: str, *, attrs: Optional[Dict[str, Any]] = None
) -> Iterator[Any]:
    """Context manager — OTel varsa span açar, yoksa noop."""
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
                    from opentelemetry.trace import Status, StatusCode  # type: ignore

                    span.set_status(Status(StatusCode.ERROR, description=str(exc)[:200]))
                    span.record_exception(exc)
                except Exception:
                    pass
                raise
    except Exception as exc:  # pragma: no cover
        logger.debug("otel span hata (sessiz): %s", exc)
        raise


def set_span_attr(key: str, value: Any) -> None:
    """Aktif span'e attribute ekle. Span yoksa noop."""
    if not is_enabled():
        return
    try:
        from opentelemetry import trace  # type: ignore

        span = trace.get_current_span()
        if span is None:
            return
        _safe_set(span, key, value)
    except Exception as exc:  # pragma: no cover
        logger.debug("otel set_span_attr hata: %s", exc)


def _safe_set(span: Any, key: str, value: Any) -> None:
    """OTel attribute değer tiplerine döndür."""
    if value is None:
        return
    if isinstance(value, (bool, int, float, str)):
        try:
            span.set_attribute(key, value)
        except Exception:
            pass
        return
    try:
        span.set_attribute(key, str(value)[:1000])
    except Exception:
        pass


def traced(name: Optional[str] = None) -> Callable[[F], F]:
    """Dekoratör — fonksiyon çağrısını span'e sar."""

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
    service_name: str = "testwright-backend",
    endpoint: Optional[str] = None,
) -> bool:
    """OTel SDK kurulumunu yap. SDK yoksa False."""
    if not _is_available():
        logger.info("otel: api paketi yok, init atlandı")
        return False
    try:
        from opentelemetry import trace  # type: ignore
        from opentelemetry.sdk.resources import Resource  # type: ignore
        from opentelemetry.sdk.trace import TracerProvider  # type: ignore
        from opentelemetry.sdk.trace.export import (  # type: ignore
            BatchSpanProcessor,
            ConsoleSpanExporter,
        )

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)

        otlp_endpoint = endpoint or os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if otlp_endpoint:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (  # type: ignore
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            except ImportError:
                from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # type: ignore
                    OTLPSpanExporter,
                )

                exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        else:
            exporter = ConsoleSpanExporter()

        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        logger.info(
            "otel: init OK (service=%s, endpoint=%s)",
            service_name,
            otlp_endpoint or "console",
        )
        return True
    except Exception as exc:  # pragma: no cover
        logger.warning("otel init başarısız: %s", exc)
        return False
