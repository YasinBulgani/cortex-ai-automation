"""Unit tests for ai.scenario_quality and ai.roi_service pure helper functions.

All tests are self-contained: no DB, no HTTP, no LLM.
Covers:
  - scenario_quality._steps_to_text: step list → numbered text
  - scenario_quality._scenario_as_embedding_text: title+steps → embedding string
  - roi_service._env_float: env-var float with default fallback
  - roi_service._range_bounds: date range tuple from days count
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import pytest

try:
    from app.domains.ai.scenario_quality import (
        _steps_to_text,
        _scenario_as_embedding_text,
    )
    _SQ_OK = True
except ImportError:
    _SQ_OK = False

try:
    from app.domains.ai.roi_service import _env_float, _range_bounds
    _ROI_OK = True
except ImportError:
    _ROI_OK = False


# ---------------------------------------------------------------------------
# _steps_to_text
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SQ_OK, reason="scenario_quality import failed")
class TestStepsToText:
    def test_none_returns_default(self):
        result = _steps_to_text(None)
        assert "(adım yok)" in result

    def test_empty_list_returns_default(self):
        assert "(adım yok)" in _steps_to_text([])

    def test_step_numbered(self):
        steps = [{"text": "login"}]
        result = _steps_to_text(steps)
        assert "1." in result

    def test_step_text_included(self):
        steps = [{"text": "Click Login Button"}]
        result = _steps_to_text(steps)
        assert "Click Login Button" in result

    def test_step_action_fallback(self):
        steps = [{"action": "Submit Form"}]
        result = _steps_to_text(steps)
        assert "Submit Form" in result

    def test_step_keyword_prepended(self):
        steps = [{"keyword": "Given", "text": "user is logged in"}]
        result = _steps_to_text(steps)
        assert "Given" in result

    def test_expected_with_arrow(self):
        steps = [{"text": "click", "expected": "button visible"}]
        result = _steps_to_text(steps)
        assert "→" in result
        assert "button visible" in result

    def test_multiple_steps_numbered_sequentially(self):
        steps = [{"text": "step one"}, {"text": "step two"}, {"text": "step three"}]
        result = _steps_to_text(steps)
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_non_dict_steps_skipped(self):
        steps = ["not a dict", {"text": "valid step"}]
        result = _steps_to_text(steps)
        assert "valid step" in result

    def test_returns_string(self):
        assert isinstance(_steps_to_text([{"text": "step"}]), str)


# ---------------------------------------------------------------------------
# _scenario_as_embedding_text
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _SQ_OK, reason="scenario_quality import failed")
class TestScenarioAsEmbeddingText:
    def test_title_included(self):
        result = _scenario_as_embedding_text("Login Test", None, None)
        assert "Login Test" in result

    def test_description_included_if_present(self):
        result = _scenario_as_embedding_text("Title", "Some description", None)
        assert "Some description" in result

    def test_no_description_ok(self):
        result = _scenario_as_embedding_text("Title", None, None)
        assert isinstance(result, str)

    def test_steps_included(self):
        steps = [{"text": "click login"}, {"text": "enter password"}]
        result = _scenario_as_embedding_text("Title", None, steps)
        assert "click login" in result

    def test_max_6_steps(self):
        steps = [{"text": f"step {i}"} for i in range(10)]
        result = _scenario_as_embedding_text("Title", None, steps)
        assert "step 6" not in result
        assert "step 7" not in result

    def test_empty_steps_no_adimlar_section(self):
        result = _scenario_as_embedding_text("Title", None, [])
        assert "Adımlar" not in result

    def test_returns_string(self):
        assert isinstance(_scenario_as_embedding_text("Title", None, None), str)

    def test_description_truncated_at_300(self):
        long_desc = "a" * 400
        result = _scenario_as_embedding_text("Title", long_desc, None)
        assert long_desc not in result  # truncated
        assert "a" * 300 in result


# ---------------------------------------------------------------------------
# roi_service._env_float
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ROI_OK, reason="roi_service import failed")
class TestRoiEnvFloat:
    def test_unset_returns_default(self, monkeypatch):
        monkeypatch.delenv("ROI_TEST_VAR", raising=False)
        assert _env_float("ROI_TEST_VAR", 40.0) == pytest.approx(40.0)

    def test_set_env_parsed(self, monkeypatch):
        monkeypatch.setenv("ROI_TEST_VAR", "55.5")
        assert _env_float("ROI_TEST_VAR", 40.0) == pytest.approx(55.5)

    def test_invalid_env_returns_default(self, monkeypatch):
        monkeypatch.setenv("ROI_TEST_VAR", "not_a_number")
        assert _env_float("ROI_TEST_VAR", 40.0) == pytest.approx(40.0)

    def test_returns_float(self, monkeypatch):
        monkeypatch.delenv("ROI_TEST_VAR", raising=False)
        assert isinstance(_env_float("ROI_TEST_VAR", 1.0), float)


# ---------------------------------------------------------------------------
# roi_service._range_bounds
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _ROI_OK, reason="roi_service import failed")
class TestRangeBounds:
    def test_returns_tuple(self):
        result = _range_bounds(7)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_start_before_end(self):
        start, end = _range_bounds(30)
        assert start < end

    def test_difference_matches_days(self):
        start, end = _range_bounds(7)
        delta = end - start
        assert delta.days == 7

    def test_returns_datetime_objects(self):
        start, end = _range_bounds(7)
        assert isinstance(start, datetime)
        assert isinstance(end, datetime)

    def test_both_are_utc(self):
        start, end = _range_bounds(7)
        assert start.tzinfo is not None
        assert end.tzinfo is not None

    def test_one_day_range(self):
        start, end = _range_bounds(1)
        delta = end - start
        assert delta.days == 1

    def test_larger_range_larger_delta(self):
        start7, end7 = _range_bounds(7)
        start30, end30 = _range_bounds(30)
        assert (end30 - start30) > (end7 - start7)
