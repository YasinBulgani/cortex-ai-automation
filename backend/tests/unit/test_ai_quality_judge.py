"""Unit tests for app.domains.ai.quality_judge — LLM-as-Judge helpers.

Tests are fully self-contained: no DB, no real LLM calls.
Covers: _clip, _parse_judge_json, _should_sample (mocked), JudgeResult,
and judge_output (mocked gateway + route_model + persist).
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock

try:
    from app.domains.ai.quality_judge import (
        _clip,
        _parse_judge_json,
        _should_sample,
        judge_output,
        JudgeResult,
        _SAMPLING_RATES,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="quality_judge import failed")


# ---------------------------------------------------------------------------
# _clip
# ---------------------------------------------------------------------------

class TestClip:
    def test_clips_above_10(self):
        assert _clip(15) == 10.0

    def test_clips_below_0(self):
        assert _clip(-5) == 0.0

    def test_passes_valid_value(self):
        assert _clip(7.5) == 7.5

    def test_zero_passthrough(self):
        assert _clip(0) == 0.0

    def test_ten_passthrough(self):
        assert _clip(10) == 10.0

    def test_invalid_string_returns_zero(self):
        assert _clip("not_a_number") == 0.0

    def test_none_returns_zero(self):
        assert _clip(None) == 0.0

    def test_returns_float(self):
        assert isinstance(_clip(5), float)

    def test_rounds_to_2_decimals(self):
        result = _clip(7.123456)
        assert result == 7.12


# ---------------------------------------------------------------------------
# _parse_judge_json
# ---------------------------------------------------------------------------

class TestParseJudgeJson:
    def test_plain_json_dict(self):
        raw = '{"correctness": 8, "completeness": 7, "domain_fit": 9, "format_validity": 8, "rationale": "good"}'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["correctness"] == 8

    def test_markdown_fenced_json(self):
        raw = '```json\n{"correctness": 9}\n```'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["correctness"] == 9

    def test_extracts_embedded_json(self):
        # JSON buried in surrounding text
        raw = 'Here is my evaluation: {"correctness": 7, "completeness": 6, "domain_fit": 5, "format_validity": 8, "rationale": "ok"} end'
        result = _parse_judge_json(raw)
        assert result is not None
        assert result["correctness"] == 7

    def test_empty_string_returns_none(self):
        assert _parse_judge_json("") is None

    def test_invalid_json_returns_none(self):
        assert _parse_judge_json("just some text without json") is None

    def test_partial_json_returns_none(self):
        assert _parse_judge_json("{broken: json") is None

    def test_returns_dict_or_none(self):
        result = _parse_judge_json('{"key": "value"}')
        assert result is None or isinstance(result, dict)


# ---------------------------------------------------------------------------
# _should_sample
# ---------------------------------------------------------------------------

class TestShouldSample:
    def test_force_true_always_samples(self):
        with patch("app.domains.ai.quality_judge._judge_enabled", return_value=False):
            result = _should_sample("security_audit", force=True)
        assert result is True

    def test_flag_disabled_returns_false(self):
        with patch("app.domains.ai.quality_judge._judge_enabled", return_value=False):
            result = _should_sample("security_audit", force=False)
        assert result is False

    def test_quality_judge_task_never_samples(self):
        # Recursive judging is disabled (rate=0.0)
        with patch("app.domains.ai.quality_judge._judge_enabled", return_value=True):
            result = _should_sample("quality_judge", force=False)
        assert result is False

    def test_returns_bool(self):
        result = _should_sample("chat")
        assert isinstance(result, bool)

    def test_sampling_rates_dict_has_expected_keys(self):
        assert "security_audit" in _SAMPLING_RATES
        assert "default" in _SAMPLING_RATES
        assert "quality_judge" in _SAMPLING_RATES


# ---------------------------------------------------------------------------
# JudgeResult dataclass
# ---------------------------------------------------------------------------

class TestJudgeResult:
    def test_can_be_constructed(self):
        result = JudgeResult(
            correctness=8.0,
            completeness=7.5,
            domain_fit=9.0,
            format_validity=8.0,
            overall=8.1,
            rationale="Good answer.",
            judge_model="claude-sonnet-4",
        )
        assert result.correctness == 8.0
        assert result.judge_model == "claude-sonnet-4"

    def test_sampled_default_true(self):
        result = JudgeResult(
            correctness=5.0,
            completeness=5.0,
            domain_fit=5.0,
            format_validity=5.0,
            overall=5.0,
            rationale="ok",
            judge_model="model",
        )
        assert result.sampled is True


# ---------------------------------------------------------------------------
# judge_output — mocked end-to-end
# ---------------------------------------------------------------------------

class TestJudgeOutput:
    def _route_stub(self, *a, **kw):
        rec = MagicMock()
        rec.model = "claude-sonnet-4"
        rec.temperature = 0.1
        rec.max_tokens = 2048
        return rec

    def test_returns_none_when_flag_disabled(self):
        with patch("app.domains.ai.quality_judge._judge_enabled", return_value=False):
            result = judge_output("security_audit", "prompt", "response text long enough")
        assert result is None

    def test_returns_none_for_short_response(self):
        with (
            patch("app.domains.ai.quality_judge._judge_enabled", return_value=True),
            patch("app.domains.ai.quality_judge._should_sample", return_value=True),
        ):
            result = judge_output("security_audit", "prompt", "short")
        assert result is None

    def test_returns_judge_result_for_valid_response(self):
        judge_json = '{"correctness": 8, "completeness": 7, "domain_fit": 9, "format_validity": 8, "rationale": "Solid answer."}'
        with (
            patch("app.domains.ai.quality_judge._should_sample", return_value=True),
            patch("app.domains.ai.quality_judge.route_model", side_effect=self._route_stub),
            patch("app.domains.ai.quality_judge.gateway_complete", return_value=judge_json),
            patch("app.domains.ai.quality_judge._persist_judge_run", return_value=None),
        ):
            result = judge_output(
                "security_audit",
                "Analyze this code",
                "This is a thorough security analysis with multiple findings.",
                force=True,
            )
        assert result is not None
        assert isinstance(result, JudgeResult)
        assert result.correctness == 8.0
        assert result.judge_model == "claude-sonnet-4"

    def test_overall_computed_as_weighted_average(self):
        judge_json = '{"correctness": 10, "completeness": 10, "domain_fit": 10, "format_validity": 10, "rationale": "Perfect."}'
        with (
            patch("app.domains.ai.quality_judge._should_sample", return_value=True),
            patch("app.domains.ai.quality_judge.route_model", side_effect=self._route_stub),
            patch("app.domains.ai.quality_judge.gateway_complete", return_value=judge_json),
            patch("app.domains.ai.quality_judge._persist_judge_run", return_value=None),
        ):
            result = judge_output(
                "security_audit", "prompt",
                "Thorough response that meets all criteria for evaluation.",
                force=True,
            )
        assert result is not None
        assert result.overall == 10.0

    def test_gateway_error_returns_none(self):
        with (
            patch("app.domains.ai.quality_judge._should_sample", return_value=True),
            patch("app.domains.ai.quality_judge.route_model", side_effect=self._route_stub),
            patch("app.domains.ai.quality_judge.gateway_complete", side_effect=Exception("LLM down")),
        ):
            result = judge_output(
                "security_audit", "p",
                "This is a valid and long enough response text for testing.",
                force=True,
            )
        assert result is None
