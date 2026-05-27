"""Unit tests for visual.compare pure helper functions.

All tests are self-contained: no filesystem access, no Pillow dependency.
Covers:
  - _env_float: env-var float parsing with default fallback
  - _safe_name: path-traversal guard + PNG extension enforcement
  - CompareResult: dataclass fields and defaults
"""
from __future__ import annotations

import os
import pytest

try:
    from app.domains.visual.compare import (
        _env_float,
        _safe_name,
        CompareResult,
    )
    _VC_OK = True
except ImportError:
    _VC_OK = False


# ---------------------------------------------------------------------------
# _env_float
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _VC_OK, reason="visual.compare import failed")
class TestEnvFloat:
    def test_unset_env_returns_default(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert _env_float("TEST_FLOAT_VAR", 0.5) == pytest.approx(0.5)

    def test_set_env_returns_parsed_float(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "0.1")
        assert _env_float("TEST_FLOAT_VAR", 0.5) == pytest.approx(0.1)

    def test_invalid_env_returns_default(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "not_a_float")
        assert _env_float("TEST_FLOAT_VAR", 0.7) == pytest.approx(0.7)

    def test_integer_string_parsed(self, monkeypatch):
        monkeypatch.setenv("TEST_FLOAT_VAR", "2")
        assert _env_float("TEST_FLOAT_VAR", 1.0) == pytest.approx(2.0)

    def test_returns_float(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert isinstance(_env_float("TEST_FLOAT_VAR", 1.0), float)

    def test_zero_default(self, monkeypatch):
        monkeypatch.delenv("TEST_FLOAT_VAR", raising=False)
        assert _env_float("TEST_FLOAT_VAR", 0.0) == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# _safe_name
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _VC_OK, reason="visual.compare import failed")
class TestSafeName:
    def test_plain_name_gets_png_extension(self):
        result = _safe_name("screenshot")
        assert result == "screenshot.png"

    def test_existing_png_extension_unchanged(self):
        result = _safe_name("screenshot.png")
        assert result == "screenshot.png"

    def test_uppercase_png_unchanged(self):
        result = _safe_name("screenshot.PNG")
        assert result.endswith(".PNG")

    def test_path_traversal_raises(self):
        with pytest.raises(ValueError):
            _safe_name("../../evil")

    def test_double_dot_in_path_raises(self):
        with pytest.raises(ValueError):
            _safe_name("valid/../evil")

    def test_absolute_path_raises(self):
        with pytest.raises(ValueError):
            _safe_name("/etc/passwd")

    def test_subdirectory_allowed(self):
        result = _safe_name("suite/test_name")
        assert "suite" in result
        assert "test_name" in result

    def test_returns_string(self):
        assert isinstance(_safe_name("name"), str)

    def test_leading_trailing_whitespace_stripped(self):
        result = _safe_name("  name  ")
        assert not result.startswith(" ")
        assert not result.endswith(" ")

    def test_backslash_converted_to_slash(self):
        # Windows paths backslash → forward slash, then checked
        result = _safe_name("suite\\name")
        assert "\\" not in result


# ---------------------------------------------------------------------------
# CompareResult
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _VC_OK, reason="visual.compare import failed")
class TestCompareResult:
    def test_ok_field(self):
        r = CompareResult(ok=True, status="ok", reason="match")
        assert r.ok is True

    def test_status_field(self):
        r = CompareResult(ok=False, status="diff_exceeds_threshold", reason="too many diffs")
        assert r.status == "diff_exceeds_threshold"

    def test_reason_field(self):
        r = CompareResult(ok=True, status="ok", reason="images match")
        assert r.reason == "images match"

    def test_diff_pixels_default_zero(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.diff_pixels == 0

    def test_total_pixels_default_zero(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.total_pixels == 0

    def test_diff_ratio_default_zero(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.diff_ratio == pytest.approx(0.0)

    def test_threshold_ratio_default_zero(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.threshold_ratio == pytest.approx(0.0)

    def test_width_height_default_zero(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.width == 0
        assert r.height == 0

    def test_baseline_path_default_none(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.baseline_path is None

    def test_diff_path_default_none(self):
        r = CompareResult(ok=True, status="ok", reason="")
        assert r.diff_path is None

    def test_all_fields_set(self):
        r = CompareResult(
            ok=False,
            status="diff_exceeds_threshold",
            reason="100 pixels differ",
            baseline_path="/baselines/test.png",
            diff_path="/diffs/test.png",
            diff_pixels=100,
            total_pixels=1000,
            diff_ratio=0.1,
            threshold_ratio=0.05,
            width=100,
            height=100,
        )
        assert r.diff_pixels == 100
        assert r.total_pixels == 1000
        assert r.diff_ratio == pytest.approx(0.1)
        assert r.width == 100
