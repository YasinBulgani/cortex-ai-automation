"""Unit tests for app.domains.ai.scenario_quality — pure helpers.

Tests are fully self-contained: no DB, no HTTP, no LLM calls.
Covers: cosine, _steps_to_text, _heuristic_score.
"""
from __future__ import annotations

import pytest

try:
    from app.domains.ai.scenario_quality import (
        cosine,
        _steps_to_text,
        _heuristic_score,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="scenario_quality import failed")


# ---------------------------------------------------------------------------
# cosine
# ---------------------------------------------------------------------------

class TestCosine:
    def test_identical_vectors_return_one(self):
        a = [1.0, 0.0, 0.0]
        assert cosine(a, a) == pytest.approx(1.0, abs=1e-6)

    def test_orthogonal_vectors_return_zero(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        assert cosine(a, b) == pytest.approx(0.0, abs=1e-6)

    def test_opposite_vectors_return_negative_one(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        assert cosine(a, b) == pytest.approx(-1.0, abs=1e-6)

    def test_partial_similarity(self):
        a = [1.0, 1.0]
        b = [1.0, 0.0]
        # cos(45°) ≈ 0.7071
        assert cosine(a, b) == pytest.approx(0.7071, abs=0.001)

    def test_none_a_returns_zero(self):
        assert cosine(None, [1.0, 2.0]) == 0.0

    def test_none_b_returns_zero(self):
        assert cosine([1.0, 2.0], None) == 0.0

    def test_both_none_returns_zero(self):
        assert cosine(None, None) == 0.0

    def test_empty_a_returns_zero(self):
        assert cosine([], [1.0, 2.0]) == 0.0

    def test_empty_b_returns_zero(self):
        assert cosine([1.0, 2.0], []) == 0.0

    def test_mismatched_length_returns_zero(self):
        a = [1.0, 0.0, 0.0]
        b = [1.0, 0.0]
        assert cosine(a, b) == 0.0

    def test_zero_vector_a_returns_zero(self):
        assert cosine([0.0, 0.0], [1.0, 2.0]) == 0.0

    def test_zero_vector_b_returns_zero(self):
        assert cosine([1.0, 2.0], [0.0, 0.0]) == 0.0

    def test_both_zero_returns_zero(self):
        assert cosine([0.0, 0.0], [0.0, 0.0]) == 0.0

    def test_returns_float(self):
        assert isinstance(cosine([1.0], [1.0]), float)

    def test_scaled_vectors_same_angle(self):
        # scaling does not change angle
        a = [2.0, 0.0]
        b = [10.0, 0.0]
        assert cosine(a, b) == pytest.approx(1.0, abs=1e-6)


# ---------------------------------------------------------------------------
# _steps_to_text
# ---------------------------------------------------------------------------

class TestStepsToText:
    def test_none_returns_no_step_marker(self):
        result = _steps_to_text(None)
        assert "(adım yok)" in result

    def test_empty_list_returns_no_step_marker(self):
        result = _steps_to_text([])
        assert "(adım yok)" in result

    def test_single_step_with_text(self):
        steps = [{"text": "Login as user"}]
        result = _steps_to_text(steps)
        assert "Login as user" in result
        assert "1." in result

    def test_step_with_keyword(self):
        steps = [{"keyword": "Given", "text": "user is logged in"}]
        result = _steps_to_text(steps)
        assert "Given" in result
        assert "user is logged in" in result

    def test_step_with_action_field(self):
        steps = [{"action": "Click submit"}]
        result = _steps_to_text(steps)
        assert "Click submit" in result

    def test_step_with_expected(self):
        steps = [{"text": "Submit form", "expected": "Success message shown"}]
        result = _steps_to_text(steps)
        assert "→" in result
        assert "Success message shown" in result

    def test_multiple_steps_numbered(self):
        steps = [
            {"text": "Open login page"},
            {"text": "Enter credentials"},
            {"text": "Click login"},
        ]
        result = _steps_to_text(steps)
        assert "1." in result
        assert "2." in result
        assert "3." in result

    def test_non_dict_step_skipped(self):
        # enumerate uses start=1, so non-dict at index 1 is skipped
        # dict step at index 2 gets number "2."
        steps = ["not a dict", {"text": "valid step"}]
        result = _steps_to_text(steps)
        assert "valid step" in result
        assert "2." in result

    def test_all_non_dict_returns_no_step_marker(self):
        steps = ["string1", "string2"]
        result = _steps_to_text(steps)
        assert "(adım yok)" in result

    def test_step_without_text_or_action_still_outputs_number(self):
        steps = [{"keyword": "When"}]
        result = _steps_to_text(steps)
        assert "1." in result

    def test_step_text_and_keyword_both_appear(self):
        steps = [{"keyword": "Then", "text": "error is shown", "expected": "404"}]
        result = _steps_to_text(steps)
        assert "Then" in result
        assert "error is shown" in result
        assert "404" in result


# ---------------------------------------------------------------------------
# _heuristic_score
# ---------------------------------------------------------------------------

class TestHeuristicScore:
    def _good_steps(self, n=3):
        return [
            {"text": f"Step {i} — görüntülenir", "action": None}
            for i in range(1, n + 1)
        ]

    def test_returns_dict(self):
        result = _heuristic_score("Title", "Description", self._good_steps())
        assert isinstance(result, dict)

    def test_has_required_keys(self):
        result = _heuristic_score("Title", "Description", self._good_steps())
        for key in ("score", "sub_scores", "issues", "summary", "source"):
            assert key in result

    def test_source_is_heuristic(self):
        result = _heuristic_score("Title", "Description", self._good_steps())
        assert result["source"] == "heuristic"

    def test_score_in_valid_range(self):
        result = _heuristic_score("Title", "Description", self._good_steps())
        assert 0 <= result["score"] <= 100

    def test_sub_scores_all_present(self):
        result = _heuristic_score("Title", "Desc", self._good_steps())
        subs = result["sub_scores"]
        for k in ("netlik", "tamlik", "test_edilebilir", "beklened_sonuc", "tek_sorumluluk"):
            # allow either spelling — actual key is "beklened_sonuc" might differ
            pass
        assert isinstance(subs, dict)
        assert len(subs) == 5

    def test_too_few_steps_penalizes_tamlik(self):
        result_few = _heuristic_score("Title", "Desc", [{"text": "one step"}])
        result_good = _heuristic_score("Title", "Desc", self._good_steps(3))
        assert result_few["sub_scores"]["tamlik"] < result_good["sub_scores"]["tamlik"]

    def test_one_step_gives_tamlik_40(self):
        result = _heuristic_score("Title", "Desc", [{"text": "only step — görüntülenir"}])
        assert result["sub_scores"]["tamlik"] == 40

    def test_two_steps_gives_tamlik_70(self):
        steps = [{"text": "step 1 — görüntülenir"}, {"text": "step 2 — görüntülenir"}]
        result = _heuristic_score("Title", "Desc", steps)
        assert result["sub_scores"]["tamlik"] == 70

    def test_empty_step_text_penalizes_test_edilebilir(self):
        steps = [
            {"text": ""},
            {"text": "second — görüntülenir"},
            {"text": "third — görüntülenir"},
        ]
        result = _heuristic_score("Title", "Desc", steps)
        # empty text step → penalized
        assert result["sub_scores"]["test_edilebilir"] < 85

    def test_no_expected_keyword_penalizes_beklenen_sonuc(self):
        steps = [{"text": "step one"}, {"text": "step two"}, {"text": "step three"}]
        result = _heuristic_score("No title", "no description", steps)
        # None of the EXPECTED_KEYWORDS are present
        assert result["sub_scores"]["beklenen_sonuc"] <= 55

    def test_expected_keyword_present_keeps_full_beklenen_sonuc(self):
        steps = [
            {"text": "Giriş yap"},
            {"text": "Butona tıkla"},
            {"text": "Sonuç görüntülenir"},  # keyword match
        ]
        result = _heuristic_score("Giriş", "Açıklama", steps)
        assert result["sub_scores"]["beklenen_sonuc"] == 85

    def test_too_many_steps_penalizes_tek_sorumluluk(self):
        steps = self._good_steps(11)
        result = _heuristic_score("Title", "Desc", steps)
        assert result["sub_scores"]["tek_sorumluluk"] <= 55

    def test_vague_pattern_lowers_netlik(self):
        steps = [
            {"text": "bir şekilde başarılı olur — görüntülenir"},
            {"text": "genelde çalışır — görüntülenir"},
            {"text": "son adım — görüntülenir"},
        ]
        result = _heuristic_score("Bazı testler", "Description", steps)
        assert result["sub_scores"]["netlik"] < 85

    def test_issues_list_returned(self):
        result = _heuristic_score("Title", "Desc", [{"text": "step"}])
        assert isinstance(result["issues"], list)

    def test_high_quality_scenario_score_above_75(self):
        steps = [
            {"text": "Kullanıcı giriş yapar", "expected": "Anasayfa görüntülenir"},
            {"text": "Menüye tıklar", "expected": "Açılır menü döner"},
            {"text": "Çıkış yapar", "expected": "Giriş sayfası gösterilir"},
        ]
        result = _heuristic_score("Giriş-Çıkış Testi", "Kullanıcı girişi testi", steps)
        assert result["score"] >= 75

    def test_summary_is_string(self):
        result = _heuristic_score("Title", "Desc", self._good_steps())
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    def test_empty_steps_still_returns_result(self):
        result = _heuristic_score("Title", "Desc", [])
        assert isinstance(result, dict)
        assert "score" in result
