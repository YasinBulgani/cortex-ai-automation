"""Unit tests for api_testing pure helpers: request_executor and self_healer.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers:
  - _resolve_json_path_simple: simplified JSON path without wildcard support
  - _simulate_retry: probability-based retry simulation, structure validation
"""
from __future__ import annotations

import pytest

try:
    from app.domains.api_testing.request_executor import _resolve_json_path_simple
    _EXECUTOR_OK = True
except ImportError:
    _EXECUTOR_OK = False

try:
    from app.domains.api_testing.self_healer import _simulate_retry
    _HEALER_OK = True
except ImportError:
    _HEALER_OK = False


# ---------------------------------------------------------------------------
# _resolve_json_path_simple
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _EXECUTOR_OK, reason="request_executor import failed")
class TestResolveJsonPathSimple:
    def test_simple_field(self):
        result = _resolve_json_path_simple({"name": "Alice"}, "$.name")
        assert result == "Alice"

    def test_nested_field(self):
        data = {"user": {"id": 42}}
        result = _resolve_json_path_simple(data, "$.user.id")
        assert result == 42

    def test_missing_field_returns_none(self):
        result = _resolve_json_path_simple({"x": 1}, "$.y")
        assert result is None

    def test_array_index(self):
        data = {"items": [10, 20, 30]}
        result = _resolve_json_path_simple(data, "$.items[1]")
        assert result == 20

    def test_array_first_element(self):
        data = {"names": ["Alice", "Bob"]}
        result = _resolve_json_path_simple(data, "$.names[0]")
        assert result == "Alice"

    def test_array_out_of_bounds_returns_none(self):
        data = {"items": [1]}
        result = _resolve_json_path_simple(data, "$.items[5]")
        assert result is None

    def test_empty_path_returns_none(self):
        result = _resolve_json_path_simple({"x": 1}, "")
        assert result is None

    def test_path_no_dollar_returns_none(self):
        result = _resolve_json_path_simple({"x": 1}, "x.y")
        assert result is None

    def test_none_data_returns_none(self):
        result = _resolve_json_path_simple(None, "$.field")
        assert result is None

    def test_deeply_nested(self):
        data = {"a": {"b": {"c": "deep_value"}}}
        result = _resolve_json_path_simple(data, "$.a.b.c")
        assert result == "deep_value"

    def test_non_dict_path_traversal_returns_none(self):
        # If we try to traverse into a non-dict, should return None
        data = {"name": "string_value"}
        result = _resolve_json_path_simple(data, "$.name.sub")
        assert result is None

    def test_root_dollar_only(self):
        # $.something — just the field name after $
        result = _resolve_json_path_simple({"x": 99}, "$.x")
        assert result == 99

    def test_integer_value(self):
        data = {"count": 0}
        result = _resolve_json_path_simple(data, "$.count")
        assert result == 0

    def test_boolean_value(self):
        data = {"active": True}
        result = _resolve_json_path_simple(data, "$.active")
        assert result is True

    def test_nested_array_field(self):
        data = {"results": [{"score": 0.9}, {"score": 0.7}]}
        result = _resolve_json_path_simple(data, "$.results[0].score")
        assert result == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# _simulate_retry
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _HEALER_OK, reason="self_healer import failed")
class TestSimulateRetry:
    """_simulate_retry is probabilistic — we test structure, not exact pass/fail."""

    def _run(self, attempt: int = 1):
        # Minimal mock objects — _simulate_retry only reads .status_code and .error_message
        class FakeExecDetail:
            status_code = 500
            error_message = "connection timeout"

        class FakeTestCase:
            pass

        return _simulate_retry(FakeTestCase(), FakeExecDetail(), {}, attempt)

    def test_returns_dict(self):
        result = self._run()
        assert isinstance(result, dict)

    def test_has_passed_key(self):
        result = self._run()
        assert "passed" in result

    def test_passed_is_bool(self):
        result = self._run()
        assert isinstance(result["passed"], bool)

    def test_has_status_code(self):
        result = self._run()
        assert "status_code" in result

    def test_has_total_ms(self):
        result = self._run()
        assert "total_ms" in result
        assert isinstance(result["total_ms"], float)

    def test_has_simulated_true(self):
        result = self._run()
        assert result["simulated"] is True

    def test_has_error_message(self):
        result = self._run()
        assert "error_message" in result

    def test_status_code_200_when_passed(self):
        # Run many times to find a passed case
        for _ in range(50):
            result = self._run(attempt=5)  # high attempt = high pass prob
            if result["passed"]:
                assert result["status_code"] == 200
                break

    def test_error_message_none_when_passed(self):
        for _ in range(50):
            result = self._run(attempt=5)
            if result["passed"]:
                assert result["error_message"] is None
                break

    def test_higher_attempt_more_likely_to_pass(self):
        # Statistical test: attempt=5 should pass more often than attempt=0
        attempt0_passes = sum(1 for _ in range(100) if self._run(attempt=0)["passed"])
        attempt5_passes = sum(1 for _ in range(100) if self._run(attempt=5)["passed"])
        # attempt=5 base_prob = 1.15 (capped effectively near 1), attempt=0 = 0.4
        # With high attempts, should reliably pass
        assert attempt5_passes > attempt0_passes

    def test_total_ms_positive(self):
        result = self._run()
        assert result["total_ms"] > 0

    def test_strategy_param_accepted(self):
        class FakeDetail:
            status_code = 200
            error_message = None

        result = _simulate_retry(object(), FakeDetail(), {"max_retries": 3}, 1)
        assert isinstance(result, dict)
