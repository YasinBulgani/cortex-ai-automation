"""Unit tests for neurex_telemetry package."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for local dev (installed via pip -e in CI)
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from neurex_telemetry import trace_span, set_span_attr, traced, is_enabled


def test_trace_span_noop_without_sdk():
    """trace_span should be a no-op context manager when OTel SDK is absent."""
    import neurex_telemetry._telemetry as _t
    original = _t._OTEL_AVAILABLE
    _t._OTEL_AVAILABLE = False
    try:
        with trace_span("test.span") as span:
            assert span is None
    finally:
        _t._OTEL_AVAILABLE = original


def test_set_span_attr_noop_without_sdk():
    import neurex_telemetry._telemetry as _t
    original = _t._OTEL_AVAILABLE
    _t._OTEL_AVAILABLE = False
    try:
        set_span_attr("key", "value")  # must not raise
    finally:
        _t._OTEL_AVAILABLE = original


def test_traced_decorator_preserves_return():
    @traced("test.fn")
    def add(a, b):
        return a + b

    assert add(2, 3) == 5


def test_traced_decorator_propagates_exception():
    @traced("test.fn.raise")
    def boom():
        raise ValueError("expected")

    with pytest.raises(ValueError, match="expected"):
        boom()


def test_is_enabled_respects_env_var(monkeypatch):
    monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
    assert is_enabled() is False
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)


import pytest  # noqa: E402 (must be after test fns use pytest.raises)
