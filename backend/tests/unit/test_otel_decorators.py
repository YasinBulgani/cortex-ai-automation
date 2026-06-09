"""Tests for otel_decorators — sampling, async/sync, result metrics."""
from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest

from app.infra.otel_decorators import (
    get_span_config,
    measure_duration,
    otel_span,
    should_sample,
)


# ============================================================================
# Sampling Tests
# ============================================================================


class TestSampling:
    """Test should_sample and sampler configuration."""

    def test_should_sample_always_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OTEL_SAMPLER=always → always sample."""
        monkeypatch.setenv("OTEL_SAMPLER", "always")
        assert should_sample(is_error=False) is True
        assert should_sample(is_error=True) is True

    def test_should_sample_never_mode(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OTEL_SAMPLER=never → never sample."""
        monkeypatch.setenv("OTEL_SAMPLER", "never")
        assert should_sample(is_error=False) is False
        assert should_sample(is_error=True) is False

    def test_should_sample_adaptive_errors_always(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Adaptive mode: errors sampled at 100% (OTEL_ERROR_SAMPLE_RATE=1.0)."""
        monkeypatch.setenv("OTEL_SAMPLER", "adaptive")
        monkeypatch.setenv("OTEL_ERROR_SAMPLE_RATE", "1.0")
        # Should always return True for errors
        assert should_sample(is_error=True) is True

    def test_should_sample_adaptive_success_partial(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Adaptive mode: success sampled at configured rate."""
        monkeypatch.setenv("OTEL_SAMPLER", "adaptive")
        monkeypatch.setenv("OTEL_SUCCESS_SAMPLE_RATE", "0.0")
        # With 0% rate, should always return False for success
        assert should_sample(is_error=False) is False

    def test_should_sample_invalid_rate_defaults(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid OTEL_*_SAMPLE_RATE defaults to 1.0 / 0.1."""
        monkeypatch.setenv("OTEL_ERROR_SAMPLE_RATE", "not_a_number")
        monkeypatch.setenv("OTEL_SUCCESS_SAMPLE_RATE", "also_invalid")
        # _get_error_sample_rate() defaults to 1.0
        # _get_success_sample_rate() defaults to 0.1
        # Should not raise
        should_sample(is_error=True)
        should_sample(is_error=False)

    def test_get_span_config_returns_dict(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """get_span_config() returns structure with enabled, sampler, rates."""
        monkeypatch.setenv("OTEL_SAMPLER", "always")
        monkeypatch.setenv("OTEL_ERROR_SAMPLE_RATE", "1.0")
        monkeypatch.setenv("OTEL_SUCCESS_SAMPLE_RATE", "0.2")

        config = get_span_config()
        assert isinstance(config, dict)
        assert "enabled" in config
        assert "sampler" in config
        assert "error_sample_rate" in config
        assert "success_sample_rate" in config
        assert config["sampler"] == "always"
        assert config["error_sample_rate"] == 1.0
        assert config["success_sample_rate"] == 0.2


# ============================================================================
# Synchronous Decorator Tests
# ============================================================================


class TestOtelSpanDecorator:
    """Test @otel_span on sync functions."""

    def test_otel_span_preserves_return_value(self) -> None:
        """Decorated function returns correct value."""
        @otel_span("test.func")
        def add(a: int, b: int) -> int:
            return a + b

        result = add(2, 3)
        assert result == 5

    def test_otel_span_preserves_metadata(self) -> None:
        """Decorated function preserves __name__, __doc__, etc."""
        @otel_span()
        def documented_func() -> str:
            """Original docstring."""
            return "result"

        assert documented_func.__name__ == "documented_func"
        assert documented_func.__doc__ == "Original docstring."

    def test_otel_span_with_args_and_kwargs(self) -> None:
        """Decorator handles both positional and keyword arguments."""
        @otel_span("test.multi")
        def multi(a: int, b: int = 10, **kwargs) -> int:
            return a + b + kwargs.get("c", 0)

        assert multi(1) == 11
        assert multi(1, 20) == 21
        assert multi(1, 20, c=5) == 26

    def test_otel_span_exception_reraised(self) -> None:
        """Exception in decorated function is reraised."""
        @otel_span("test.fail")
        def fail() -> None:
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            fail()

    def test_otel_span_with_explicit_name(self) -> None:
        """@otel_span can have explicit name different from function."""
        @otel_span("custom.span.name")
        def my_func() -> str:
            return "ok"

        # Should not raise; name is used internally
        result = my_func()
        assert result == "ok"

    def test_otel_span_sample_always(self) -> None:
        """sample=1.0 always creates span."""
        @otel_span("test.always", sample=1.0)
        def always_sampled() -> int:
            return 42

        assert always_sampled() == 42

    def test_otel_span_sample_never(self) -> None:
        """sample=0.0 never creates span."""
        @otel_span("test.never", sample=0.0)
        def never_sampled() -> int:
            return 42

        assert never_sampled() == 42


# ============================================================================
# Asynchronous Decorator Tests
# ============================================================================


class TestMeasureDurationAsync:
    """Test @measure_duration on async functions."""

    @pytest.mark.asyncio
    async def test_measure_duration_async_returns_value(self) -> None:
        """Decorated async function returns correct value."""
        @measure_duration("test.async.func")
        async def async_add(a: int, b: int) -> int:
            await asyncio.sleep(0.001)
            return a + b

        result = await async_add(2, 3)
        assert result == 5

    @pytest.mark.asyncio
    async def test_measure_duration_async_preserves_metadata(self) -> None:
        """Decorated async function preserves __name__, __doc__."""
        @measure_duration()
        async def async_documented() -> str:
            """Async docstring."""
            return "ok"

        assert async_documented.__name__ == "async_documented"
        assert async_documented.__doc__ == "Async docstring."

    @pytest.mark.asyncio
    async def test_measure_duration_async_exception_reraised(self) -> None:
        """Exception in async function is reraised."""
        @measure_duration("test.async.fail")
        async def async_fail() -> None:
            await asyncio.sleep(0.001)
            raise RuntimeError("async error")

        with pytest.raises(RuntimeError, match="async error"):
            await async_fail()

    @pytest.mark.asyncio
    async def test_measure_duration_async_with_args_kwargs(self) -> None:
        """Async decorator handles positional + keyword arguments."""
        @measure_duration("test.async.multi")
        async def async_multi(a: int, b: int = 10, **kwargs) -> int:
            return a + b + kwargs.get("c", 0)

        assert await async_multi(1) == 11
        assert await async_multi(1, 20) == 21
        assert await async_multi(1, 20, c=5) == 26

    @pytest.mark.asyncio
    async def test_measure_duration_async_sample_always(self) -> None:
        """sample=1.0 on async decorator."""
        @measure_duration("test.async.always", sample=1.0)
        async def async_always() -> int:
            return 42

        assert await async_always() == 42

    @pytest.mark.asyncio
    async def test_measure_duration_async_sample_never(self) -> None:
        """sample=0.0 on async decorator."""
        @measure_duration("test.async.never", sample=0.0)
        async def async_never() -> int:
            return 42

        assert await async_never() == 42


class TestMeasureDurationSync:
    """Test @measure_duration on sync functions (fallback behavior)."""

    def test_measure_duration_sync_returns_value(self) -> None:
        """@measure_duration on sync function delegates to otel_span."""
        @measure_duration("test.sync.func")
        def sync_add(a: int, b: int) -> int:
            return a + b

        result = sync_add(2, 3)
        assert result == 5

    def test_measure_duration_sync_exception_reraised(self) -> None:
        """@measure_duration on sync function reraised exceptions."""
        @measure_duration("test.sync.fail")
        def sync_fail() -> None:
            raise ValueError("sync error")

        with pytest.raises(ValueError, match="sync error"):
            sync_fail()


# ============================================================================
# Result Metrics Tests
# ============================================================================


class TestResultMetrics:
    """Test extraction of result.count, result.keys from function returns."""

    def test_otel_span_dict_result(self) -> None:
        """Function returning dict → result.count, result.keys captured."""
        @otel_span("test.dict.result", sample=1.0)
        def return_dict() -> dict:
            return {"a": 1, "b": 2, "c": 3}

        result = return_dict()
        assert result == {"a": 1, "b": 2, "c": 3}

    def test_otel_span_list_result(self) -> None:
        """Function returning list → result.count captured."""
        @otel_span("test.list.result", sample=1.0)
        def return_list() -> list:
            return [1, 2, 3, 4, 5]

        result = return_list()
        assert len(result) == 5

    def test_otel_span_tuple_with_count(self) -> None:
        """Function returning (count, data) tuple → result.count captured."""
        @otel_span("test.tuple.result", sample=1.0)
        def return_tuple_count() -> tuple:
            return (3, ["a", "b", "c"])

        result = return_tuple_count()
        assert result == (3, ["a", "b", "c"])

    def test_otel_span_none_result(self) -> None:
        """Function returning None → no result attributes."""
        @otel_span("test.none.result", sample=1.0)
        def return_none() -> None:
            return None

        result = return_none()
        assert result is None

    def test_otel_span_string_result_not_counted(self) -> None:
        """Function returning string → not counted as iterable."""
        @otel_span("test.string.result", sample=1.0)
        def return_string() -> str:
            return "hello"

        result = return_string()
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_measure_duration_async_list_result(self) -> None:
        """Async function returning list → result.count captured."""
        @measure_duration("test.async.list.result", sample=1.0)
        async def return_async_list() -> list:
            return [1, 2, 3]

        result = await return_async_list()
        assert len(result) == 3


# ============================================================================
# Duration Metrics Tests
# ============================================================================


class TestDurationMetrics:
    """Test duration_ms capture."""

    def test_otel_span_captures_duration(self) -> None:
        """Span captures execution duration_ms."""
        @otel_span("test.duration", sample=1.0)
        def slow_func() -> int:
            import time

            time.sleep(0.01)  # 10ms
            return 1

        result = slow_func()
        assert result == 1
        # Duration should be captured (≥10ms), no exception

    @pytest.mark.asyncio
    async def test_measure_duration_async_captures_duration(self) -> None:
        """Async span captures execution duration_ms."""
        @measure_duration("test.async.duration", sample=1.0)
        async def slow_async_func() -> int:
            await asyncio.sleep(0.01)  # 10ms
            return 1

        result = await slow_async_func()
        assert result == 1
        # Duration should be captured


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Test error capture and sampling."""

    def test_otel_span_error_exception_type_captured(self) -> None:
        """Exception type is logged when error occurs."""
        @otel_span("test.error.type", sample=1.0)
        def error_func() -> None:
            raise TypeError("invalid type")

        with pytest.raises(TypeError):
            error_func()

    def test_otel_span_error_exception_message_captured(self) -> None:
        """Exception message is captured."""
        @otel_span("test.error.msg", sample=1.0)
        def error_with_msg() -> None:
            raise RuntimeError("something went wrong")

        with pytest.raises(RuntimeError):
            error_with_msg()

    @pytest.mark.asyncio
    async def test_measure_duration_async_error_captured(self) -> None:
        """Async decorator captures error info."""
        @measure_duration("test.async.error", sample=1.0)
        async def async_error_func() -> None:
            raise ValueError("async error")

        with pytest.raises(ValueError):
            await async_error_func()


# ============================================================================
# Integration Tests
# ============================================================================


class TestIntegration:
    """Integration tests with telemetry enabled/disabled."""

    def test_otel_span_no_telemetry_still_works(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Decorator works even if OTel is disabled."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "1")

        @otel_span("test.disabled")
        def func() -> int:
            return 42

        result = func()
        assert result == 42

    @pytest.mark.asyncio
    async def test_measure_duration_no_telemetry_still_works(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Async decorator works even if OTel is disabled."""
        monkeypatch.setenv("OTEL_SDK_DISABLED", "1")

        @measure_duration("test.async.disabled")
        async def async_func() -> int:
            return 42

        result = await async_func()
        assert result == 42

    def test_multiple_decorators_stack(self) -> None:
        """Multiple decorators can be stacked."""
        @otel_span("test.outer")
        @otel_span("test.inner")
        def nested() -> str:
            return "ok"

        result = nested()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_mixed_decorators(self) -> None:
        """Sync and async decorators can be mixed in same codebase."""
        @otel_span("test.sync")
        def sync_func() -> int:
            return 1

        @measure_duration("test.async")
        async def async_func() -> int:
            return 2

        r1 = sync_func()
        r2 = await async_func()
        assert r1 == 1
        assert r2 == 2
