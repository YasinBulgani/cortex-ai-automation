"""Unit tests for tspm.test_runner_service pure helper functions.

All tests are self-contained: no DB, no HTTP, no threading.
Covers:
  - _convert_steps: scenario step list → engine format
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.test_runner_service import _convert_steps
    _TR_OK = True
except ImportError:
    _TR_OK = False


# ---------------------------------------------------------------------------
# _convert_steps
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TR_OK, reason="test_runner_service import failed")
class TestConvertSteps:
    def test_dict_with_action_key(self):
        steps = [{"action": "Click Login", "expected": "Button found"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "Click Login"
        assert result[0]["expected"] == "Button found"

    def test_dict_with_action_default_expected(self):
        steps = [{"action": "Click Login"}]
        result = _convert_steps(steps)
        assert result[0]["expected"] == ""

    def test_dict_with_text_key_simple(self):
        steps = [{"text": "Navigate to home page"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "Navigate to home page"
        assert result[0]["expected"] == ""

    def test_dict_with_text_arrow_separator(self):
        steps = [{"text": "Click Login → Button is active"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "Click Login"
        assert result[0]["expected"] == "Button is active"

    def test_empty_list(self):
        assert _convert_steps([]) == []

    def test_non_dict_items_ignored(self):
        steps = ["string_step", 42, None, {"action": "valid"}]
        result = _convert_steps(steps)
        # Only dict items with "action" or "text" are processed
        assert len(result) == 1
        assert result[0]["action"] == "valid"

    def test_returns_list(self):
        assert isinstance(_convert_steps([]), list)

    def test_action_and_expected_keys_present(self):
        steps = [{"action": "Do X", "expected": "Y happens"}]
        result = _convert_steps(steps)
        assert "action" in result[0]
        assert "expected" in result[0]

    def test_multiple_steps(self):
        steps = [
            {"action": "Open URL", "expected": "Page loaded"},
            {"action": "Click Submit"},
            {"text": "Verify result → Success message shown"},
        ]
        result = _convert_steps(steps)
        assert len(result) == 3

    def test_text_with_arrow_trims_whitespace(self):
        steps = [{"text": "Step A  →  Expected B"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "Step A"
        assert result[0]["expected"] == "Expected B"

    def test_text_without_arrow_empty_expected(self):
        steps = [{"text": "Just a description"}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "Just a description"
        assert result[0]["expected"] == ""

    def test_dict_without_action_or_text_skipped(self):
        steps = [{"description": "not matched"}, {"action": "valid"}]
        result = _convert_steps(steps)
        assert len(result) == 1

    def test_action_key_takes_precedence_over_text(self):
        # If "action" in step, it's used directly even if "text" also present
        steps = [{"action": "Use action key", "text": "Should be ignored", "expected": ""}]
        result = _convert_steps(steps)
        assert result[0]["action"] == "Use action key"
