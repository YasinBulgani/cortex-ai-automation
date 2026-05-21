"""Telemetry helpers — noop fallback + OTel varsa span davranışı."""
from __future__ import annotations

import pytest

from app.infra import telemetry as tel


def test_is_enabled_returns_bool() -> None:
    assert isinstance(tel.is_enabled(), bool)


def test_disabled_by_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "1")
    assert tel.is_enabled() is False


def test_trace_span_is_context_manager() -> None:
    with tel.trace_span("x") as span:
        assert span is None or hasattr(span, "set_attribute")


def test_trace_span_attrs_dont_raise() -> None:
    with tel.trace_span(
        "x", attrs={"a": 1, "b": "y", "c": True, "d": None, "e": [1, 2]}
    ):
        pass


def test_set_span_attr_outside_span_noop() -> None:
    tel.set_span_attr("orphan", "value")


def test_traced_decorator_preserves_return() -> None:
    @tel.traced("test.fn")
    def _fn(x: int) -> int:
        return x * 2

    assert _fn(5) == 10


def test_traced_preserves_metadata() -> None:
    @tel.traced()
    def original_fn():
        """docstring"""
        return 1

    assert original_fn.__name__ == "original_fn"
    assert original_fn.__doc__ == "docstring"


def test_exception_inside_span_reraised() -> None:
    with pytest.raises(ValueError, match="boom"):
        with tel.trace_span("bomb"):
            raise ValueError("boom")


def test_exception_in_traced_decorator_reraised() -> None:
    @tel.traced("fail")
    def _f():
        raise RuntimeError("x")

    with pytest.raises(RuntimeError):
        _f()


def test_init_returns_bool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    tel._TRACER = None  # noqa: SLF001
    result = tel.init_otel(service_name="test")
    assert isinstance(result, bool)


def test_init_disabled_when_env_disables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OTEL_SDK_DISABLED", "1")
    # Span yine açılmaz — is_enabled False
    with tel.trace_span("disabled") as span:
        assert span is None


def test_safe_set_handles_complex_values() -> None:
    # _safe_set exception atmasın — complex/list/dict/None
    class _FakeSpan:
        def __init__(self) -> None:
            self.attrs: dict = {}

        def set_attribute(self, k, v):
            self.attrs[k] = v

    span = _FakeSpan()
    tel._safe_set(span, "none", None)
    tel._safe_set(span, "int", 42)
    tel._safe_set(span, "str", "ok")
    tel._safe_set(span, "list", [1, 2, 3])
    tel._safe_set(span, "nested", {"a": 1})

    assert "none" not in span.attrs  # None atlanır
    assert span.attrs["int"] == 42
    assert span.attrs["str"] == "ok"
    assert isinstance(span.attrs["list"], str)
    assert isinstance(span.attrs["nested"], str)
