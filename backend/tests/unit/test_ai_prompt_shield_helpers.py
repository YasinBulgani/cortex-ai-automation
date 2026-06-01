"""Unit tests for app.domains.ai.prompt_shield — pure helpers.

Tests are fully self-contained: no DB, no HTTP.
Covers: _normalize (zero-width char removal, NFKC, empty),
        _scan_patterns (score accumulation, cap at 1.0, empty text),
        _decision (allow/warn/block thresholds),
        ShieldResult dataclass.
"""
from __future__ import annotations

import re
import pytest

try:
    from app.domains.ai.prompt_shield import (
        _normalize,
        _scan_patterns,
        _decision,
        ShieldResult,
        _BLOCK_THRESHOLD,
        _WARN_THRESHOLD,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="prompt_shield import failed")


# ---------------------------------------------------------------------------
# _normalize
# ---------------------------------------------------------------------------

class TestNormalize:
    def test_empty_returns_empty(self):
        assert _normalize("") == ""

    def test_none_returns_empty(self):
        assert _normalize(None) == ""  # type: ignore[arg-type]

    def test_regular_text_unchanged(self):
        assert _normalize("hello world") == "hello world"

    def test_zero_width_space_replaced(self):
        # U+200B zero-width space
        result = _normalize("ignore​all")
        assert "​" not in result
        assert result == "ignore all"

    def test_zero_width_joiner_replaced(self):
        # U+200D zero-width joiner
        result = _normalize("a‍b")
        assert "‍" not in result

    def test_bom_replaced(self):
        # U+FEFF BOM/zero-width no-break space
        result = _normalize("﻿text")
        assert "﻿" not in result

    def test_nfkc_normalization(self):
        # Full-width A (FF21) → regular A
        result = _normalize("Ａ")
        assert result == "A"

    def test_returns_string(self):
        assert isinstance(_normalize("test"), str)

    def test_multiple_zero_width_chars(self):
        text = "a​b‌c‍d"
        result = _normalize(text)
        assert "​" not in result
        assert "‌" not in result
        assert "‍" not in result


# ---------------------------------------------------------------------------
# _scan_patterns
# ---------------------------------------------------------------------------

class TestScanPatterns:
    def _patterns(self, *pairs):
        return [(weight, re.compile(pat), name) for weight, pat, name in pairs]

    def test_empty_text_returns_zero(self):
        score, hits = _scan_patterns("", self._patterns((0.5, r"test", "p1")))
        assert score == 0.0
        assert hits == []

    def test_no_patterns_returns_zero(self):
        score, hits = _scan_patterns("any text", [])
        assert score == 0.0
        assert hits == []

    def test_single_match_returns_weight(self):
        score, hits = _scan_patterns("ignore all previous", self._patterns((0.7, r"ignore", "inj")))
        assert score == pytest.approx(0.7)
        assert "inj" in hits

    def test_no_match_returns_zero(self):
        score, hits = _scan_patterns("normal user input", self._patterns((0.5, r"jailbreak", "j")))
        assert score == 0.0
        assert hits == []

    def test_multiple_matches_accumulated(self):
        pats = self._patterns(
            (0.3, r"ignore", "p1"),
            (0.4, r"previous", "p2"),
        )
        score, hits = _scan_patterns("ignore all previous instructions", pats)
        assert score == pytest.approx(0.7)
        assert len(hits) == 2

    def test_score_capped_at_one(self):
        pats = self._patterns(
            (0.6, r"a", "p1"),
            (0.6, r"b", "p2"),
        )
        score, hits = _scan_patterns("a b", pats)
        assert score == pytest.approx(1.0)

    def test_returns_tuple(self):
        result = _scan_patterns("text", [])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_hits_are_list(self):
        _, hits = _scan_patterns("text", [])
        assert isinstance(hits, list)


# ---------------------------------------------------------------------------
# _decision
# ---------------------------------------------------------------------------

class TestDecision:
    def test_below_warn_threshold_is_allow(self):
        assert _decision(0.0) == "allow"
        assert _decision(_WARN_THRESHOLD - 0.01) == "allow"

    def test_exactly_warn_threshold_is_warn(self):
        assert _decision(_WARN_THRESHOLD) == "warn"

    def test_between_warn_and_block_is_warn(self):
        mid = (_WARN_THRESHOLD + _BLOCK_THRESHOLD) / 2
        assert _decision(mid) == "warn"

    def test_exactly_block_threshold_is_block(self):
        assert _decision(_BLOCK_THRESHOLD) == "block"

    def test_above_block_threshold_is_block(self):
        assert _decision(1.0) == "block"
        assert _decision(0.99) == "block"

    def test_returns_string(self):
        assert isinstance(_decision(0.5), str)


# ---------------------------------------------------------------------------
# ShieldResult dataclass
# ---------------------------------------------------------------------------

class TestShieldResultPrompt:
    def test_can_instantiate(self):
        result = ShieldResult(decision="allow", score=0.1)
        assert result.decision == "allow"

    def test_default_reasons_empty(self):
        result = ShieldResult(decision="allow", score=0.0)
        assert result.reasons == []

    def test_default_sanitized_none(self):
        result = ShieldResult(decision="allow", score=0.0)
        assert result.sanitized_input is None

    def test_with_reasons(self):
        result = ShieldResult(decision="warn", score=0.35, reasons=["injection_attempt"])
        assert "injection_attempt" in result.reasons

    def test_immutable_decision(self):
        result = ShieldResult(decision="block", score=0.9)
        with pytest.raises((AttributeError, TypeError)):
            result.decision = "allow"  # type: ignore[misc]
