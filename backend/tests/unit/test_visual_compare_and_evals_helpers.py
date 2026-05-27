"""Unit tests for visual compare and evals runner pure helpers.

No DB, no HTTP, no LLM — pure Python only.

Covers:
  app/domains/visual/compare.py:
    _env_float, _safe_name
  app/domains/evals/runner.py:
    _default_max_workers
"""

from __future__ import annotations

import os

import pytest

from app.domains.visual.compare import _env_float, _safe_name
from app.domains.evals.runner import _default_max_workers


# ── _env_float ────────────────────────────────────────────────────────────────


class TestEnvFloat:
    def test_returns_default_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert _env_float("TEST_FLOAT_VAR", 0.8) == pytest.approx(0.8)

    def test_reads_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_FLOAT_VAR", "0.5")
        assert _env_float("TEST_FLOAT_VAR", 0.8) == pytest.approx(0.5)

    def test_invalid_env_returns_default(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_FLOAT_VAR", "not_a_number")
        assert _env_float("TEST_FLOAT_VAR", 0.75) == pytest.approx(0.75)

    def test_returns_float_type(self, monkeypatch) -> None:
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        result = _env_float("TEST_FLOAT_VAR", 1.0)
        assert isinstance(result, float)

    def test_reads_integer_env_as_float(self, monkeypatch) -> None:
        monkeypatch.setenv("TEST_FLOAT_VAR", "3")
        assert _env_float("TEST_FLOAT_VAR", 1.0) == pytest.approx(3.0)

    def test_zero_default(self, monkeypatch) -> None:
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert _env_float("TEST_FLOAT_VAR", 0.0) == pytest.approx(0.0)


# ── _safe_name ────────────────────────────────────────────────────────────────


class TestSafeName:
    def test_simple_name_adds_png(self) -> None:
        result = _safe_name("screenshot")
        assert result == "screenshot.png"

    def test_name_with_png_unchanged(self) -> None:
        result = _safe_name("screenshot.png")
        assert result == "screenshot.png"

    def test_path_traversal_raises(self) -> None:
        with pytest.raises(ValueError):
            _safe_name("../evil")

    def test_absolute_path_raises(self) -> None:
        with pytest.raises(ValueError):
            _safe_name("/etc/passwd")

    def test_nested_path_allowed(self) -> None:
        result = _safe_name("homepage/landing.png")
        assert result == "homepage/landing.png"

    def test_backslash_normalized_to_slash(self) -> None:
        # Backslash → forward slash, then ../ check applies
        # "screenshots\page" should not contain ".." so should pass
        result = _safe_name("screenshots\\page")
        assert "/" in result

    def test_strips_whitespace(self) -> None:
        result = _safe_name("  my-screenshot  ")
        assert "  " not in result

    def test_uppercase_png_preserved(self) -> None:
        result = _safe_name("test.PNG")
        assert result.endswith(".PNG")

    def test_returns_string(self) -> None:
        assert isinstance(_safe_name("test"), str)

    def test_double_dot_in_deep_path_raises(self) -> None:
        with pytest.raises(ValueError):
            _safe_name("a/b/../c")


# ── _default_max_workers ──────────────────────────────────────────────────────


class TestDefaultMaxWorkers:
    def test_default_when_not_set(self, monkeypatch) -> None:
        monkeypatch.delenv("EVAL_MAX_WORKERS", raising=False)
        result = _default_max_workers()
        assert result == 4

    def test_reads_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("EVAL_MAX_WORKERS", "8")
        assert _default_max_workers() == 8

    def test_invalid_returns_default(self, monkeypatch) -> None:
        monkeypatch.setenv("EVAL_MAX_WORKERS", "invalid")
        assert _default_max_workers() == 4

    def test_clamped_to_min_1(self, monkeypatch) -> None:
        monkeypatch.setenv("EVAL_MAX_WORKERS", "0")
        assert _default_max_workers() >= 1

    def test_clamped_to_max_32(self, monkeypatch) -> None:
        monkeypatch.setenv("EVAL_MAX_WORKERS", "100")
        assert _default_max_workers() <= 32

    def test_returns_int(self, monkeypatch) -> None:
        monkeypatch.delenv("EVAL_MAX_WORKERS", raising=False)
        assert isinstance(_default_max_workers(), int)
