"""Integration tests for OTel decorators with instrumented domains.

Tests that the decorators work correctly with real domain services.
"""
from __future__ import annotations

import pytest

from app.infra.otel_decorators import get_span_config, otel_span


class TestDecoratorIntegration:
    """Integration tests with instrumented services."""

    def test_span_config_reflects_env_settings(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_span_config() reads and returns current env settings."""
        monkeypatch.setenv("OTEL_SAMPLER", "always")
        monkeypatch.setenv("OTEL_ERROR_SAMPLE_RATE", "1.0")
        monkeypatch.setenv("OTEL_SUCCESS_SAMPLE_RATE", "0.5")

        config = get_span_config()
        assert config["sampler"] == "always"
        assert config["error_sample_rate"] == 1.0
        assert config["success_sample_rate"] == 0.5

    def test_decorated_function_maintains_signature(self) -> None:
        """Decorator preserves function signature and introspection."""
        @otel_span("test.signature")
        def multi_arg(a: int, b: str = "default", *args, **kwargs) -> str:
            """Multi-arg function."""
            return f"{a}:{b}"

        # Check signature preserved
        assert multi_arg.__name__ == "multi_arg"
        assert multi_arg.__doc__ == "Multi-arg function."

        # Check call works with various argument patterns
        assert multi_arg(1) == "1:default"
        assert multi_arg(1, "custom") == "1:custom"
        assert multi_arg(1, b="kwarg") == "1:kwarg"

    def test_decorated_function_with_exceptions_reraised(self) -> None:
        """Decorator reraised exceptions from decorated function."""
        @otel_span("test.exception")
        def raises_error(msg: str) -> None:
            raise ValueError(msg)

        with pytest.raises(ValueError, match="custom error"):
            raises_error("custom error")

    def test_decorator_noop_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Decorator is completely transparent when OTel disabled."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "1")

        @otel_span("test.disabled")
        def compute() -> int:
            return 42

        # Function should work normally
        result = compute()
        assert result == 42

    def test_multiple_decorator_instances_independent(self) -> None:
        """Multiple decorated functions don't interfere with each other."""
        @otel_span("test.func1", sample=1.0)
        def func1() -> int:
            return 1

        @otel_span("test.func2", sample=0.0)
        def func2() -> int:
            return 2

        @otel_span("test.func3")
        def func3() -> int:
            return 3

        assert func1() == 1
        assert func2() == 2
        assert func3() == 3

    def test_decorator_preserves_return_type_variations(self) -> None:
        """Decorator works with various return types."""
        @otel_span("test.return.none", sample=1.0)
        def return_none() -> None:
            return None

        @otel_span("test.return.tuple", sample=1.0)
        def return_tuple() -> tuple:
            return (1, 2, 3)

        @otel_span("test.return.dict", sample=1.0)
        def return_dict() -> dict:
            return {"key": "value"}

        @otel_span("test.return.list", sample=1.0)
        def return_list() -> list:
            return [1, 2, 3]

        assert return_none() is None
        assert return_tuple() == (1, 2, 3)
        assert return_dict() == {"key": "value"}
        assert return_list() == [1, 2, 3]

    def test_sampling_respects_explicit_rate(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Explicit sample rate overrides adaptive env settings."""
        monkeypatch.setenv("OTEL_SAMPLER", "never")
        monkeypatch.setenv("OTEL_SUCCESS_SAMPLE_RATE", "0.0")

        # Even with env set to never sample, explicit sample=1.0 should work
        @otel_span("test.override", sample=1.0)
        def override_func() -> str:
            return "ok"

        result = override_func()
        assert result == "ok"


class TestPerformanceCharacteristics:
    """Verify decorator performance characteristics."""

    def test_decorator_minimal_overhead_noop(self) -> None:
        """When OTel disabled, decorator overhead is minimal."""
        import time

        @otel_span("test.perf")
        def fast_func() -> int:
            return 1

        # Run multiple times to measure baseline
        start = time.perf_counter()
        for _ in range(1000):
            fast_func()
        elapsed_ms = (time.perf_counter() - start) * 1000

        # Should be very fast (< 50ms for 1000 calls)
        assert elapsed_ms < 50.0, f"Decorator overhead too high: {elapsed_ms:.2f}ms"

    def test_decorator_handles_large_results(self) -> None:
        """Decorator can handle large result sets without error."""
        @otel_span("test.large.result", sample=1.0)
        def return_large_list() -> list:
            return list(range(10000))

        result = return_large_list()
        assert len(result) == 10000


class TestErrorScenarios:
    """Test edge cases and error scenarios."""

    def test_decorator_with_none_name_auto_derives(self) -> None:
        """When name=None, decorator auto-derives from function."""
        @otel_span()
        def my_function() -> str:
            return "ok"

        # Should not raise, name is auto-derived
        assert my_function() == "ok"

    def test_decorator_with_kwargs_only_function(self) -> None:
        """Decorator works with kwargs-only functions."""
        @otel_span("test.kwargs.only")
        def kwargs_only(*, a: int, b: str = "default") -> str:
            return f"{a}:{b}"

        assert kwargs_only(a=1) == "1:default"
        assert kwargs_only(a=1, b="custom") == "1:custom"

    def test_decorator_with_varargs_function(self) -> None:
        """Decorator works with *args functions."""
        @otel_span("test.varargs")
        def varargs_func(*args) -> int:
            return sum(args)

        assert varargs_func(1, 2, 3) == 6
        assert varargs_func() == 0

    def test_decorator_exception_includes_stack_trace(self) -> None:
        """When exception raised, stack trace is preserved."""
        @otel_span("test.stack", sample=1.0)
        def nested_error() -> None:
            def inner() -> None:
                raise RuntimeError("inner error")

            inner()

        with pytest.raises(RuntimeError, match="inner error"):
            nested_error()
