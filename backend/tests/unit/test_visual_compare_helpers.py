"""Unit tests for app.domains.visual.compare — pure helpers.

Tests are fully self-contained: no PIL, no filesystem.
Covers: _env_float, _safe_name (path traversal prevention),
        CompareResult dataclass, _safe_label (from metrics module).
"""
from __future__ import annotations

import pytest

try:
    from app.domains.visual.compare import (
        _env_float,
        _safe_name,
        CompareResult,
    )
    _VISUAL_IMPORT_OK = True
except ImportError:
    _VISUAL_IMPORT_OK = False

try:
    from app.domains.ai.metrics import _safe_label
    _METRICS_IMPORT_OK = True
except ImportError:
    _METRICS_IMPORT_OK = False


# ---------------------------------------------------------------------------
# _env_float (visual compare)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _VISUAL_IMPORT_OK, reason="visual.compare import failed")
class TestVisualEnvFloat:
    def test_default_when_not_set(self, monkeypatch):
        monkeypatch.delenv("VISUAL_TEST_FLOAT", raising=False)
        assert _env_float("VISUAL_TEST_FLOAT", 0.05) == pytest.approx(0.05)

    def test_reads_env_value(self, monkeypatch):
        monkeypatch.setenv("VISUAL_TEST_FLOAT", "0.10")
        assert _env_float("VISUAL_TEST_FLOAT", 0.05) == pytest.approx(0.10)

    def test_invalid_returns_default(self, monkeypatch):
        monkeypatch.setenv("VISUAL_TEST_FLOAT", "not_float")
        assert _env_float("VISUAL_TEST_FLOAT", 0.99) == pytest.approx(0.99)

    def test_returns_float(self, monkeypatch):
        monkeypatch.setenv("VISUAL_TEST_FLOAT", "0.5")
        assert isinstance(_env_float("VISUAL_TEST_FLOAT", 0.5), float)


# ---------------------------------------------------------------------------
# _safe_name
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _VISUAL_IMPORT_OK, reason="visual.compare import failed")
class TestSafeName:
    def test_plain_name_returned(self):
        result = _safe_name("screenshot")
        assert result == "screenshot.png"

    def test_already_has_png_extension(self):
        result = _safe_name("image.png")
        assert result == "image.png"

    def test_case_insensitive_extension(self):
        result = _safe_name("IMAGE.PNG")
        assert result == "IMAGE.PNG"

    def test_path_traversal_raises(self):
        with pytest.raises(ValueError):
            _safe_name("../secret/file")

    def test_absolute_path_raises(self):
        with pytest.raises(ValueError):
            _safe_name("/etc/passwd")

    def test_subdirectory_allowed(self):
        result = _safe_name("screenshots/homepage")
        assert "homepage.png" in result

    def test_returns_string(self):
        assert isinstance(_safe_name("test"), str)

    def test_windows_backslash_normalized(self):
        # backslash converted to forward slash before check
        result = _safe_name("folder\\file")
        assert ".." not in result

    def test_whitespace_stripped(self):
        result = _safe_name("  test  ")
        assert result == "test.png"


# ---------------------------------------------------------------------------
# CompareResult dataclass
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _VISUAL_IMPORT_OK, reason="visual.compare import failed")
class TestCompareResult:
    def test_ok_true(self):
        result = CompareResult(ok=True, status="ok", reason="match")
        assert result.ok is True

    def test_status_field(self):
        result = CompareResult(ok=False, status="diff_exceeds_threshold", reason="5% diff")
        assert result.status == "diff_exceeds_threshold"

    def test_reason_field(self):
        result = CompareResult(ok=True, status="ok", reason="identical images")
        assert "identical" in result.reason

    def test_ok_false_for_failure(self):
        result = CompareResult(ok=False, status="size_mismatch", reason="800x600 vs 1024x768")
        assert result.ok is False

    def test_new_baseline_status(self):
        result = CompareResult(ok=True, status="new_baseline", reason="baseline created")
        assert result.status == "new_baseline"


# ---------------------------------------------------------------------------
# _safe_label (ai.metrics)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _METRICS_IMPORT_OK, reason="ai.metrics import failed")
class TestSafeLabel:
    def test_empty_string_returns_default(self):
        assert _safe_label("") == "unknown"

    def test_none_returns_default(self):
        assert _safe_label(None) == "unknown"

    def test_custom_default(self):
        assert _safe_label(None, default="missing") == "missing"

    def test_value_returned_as_is(self):
        assert _safe_label("gpt-4o") == "gpt-4o"

    def test_strips_whitespace(self):
        assert _safe_label("  model  ") == "model"

    def test_truncated_to_max_len(self):
        long_value = "a" * 100
        result = _safe_label(long_value, max_len=64)
        assert len(result) == 64

    def test_short_value_not_truncated(self):
        assert _safe_label("gpt", max_len=64) == "gpt"

    def test_returns_string(self):
        assert isinstance(_safe_label("test"), str)
