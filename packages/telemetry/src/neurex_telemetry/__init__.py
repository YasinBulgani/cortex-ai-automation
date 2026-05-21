"""Neurex QA — shared OpenTelemetry helpers.

Minimal wrapper: if opentelemetry-api is not installed every call is a no-op.
Services opt in to the full SDK by installing the [otel] extra.

Usage:
    from neurex_telemetry import init_otel, trace_span, set_span_attr, traced

    # In your service startup (lifespan / app factory):
    init_otel(service_name="neurex-engine")

    # In domain code:
    with trace_span("my.operation", attrs={"key": "value"}):
        ...

    @traced("ai.generate")
    def generate(...):
        ...
"""

from neurex_telemetry._telemetry import (
    init_otel,
    is_enabled,
    set_span_attr,
    trace_span,
    traced,
)
from neurex_telemetry.logging import configure_logging

__all__ = [
    "configure_logging",
    "init_otel",
    "is_enabled",
    "set_span_attr",
    "trace_span",
    "traced",
]
