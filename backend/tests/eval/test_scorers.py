"""Scorer unit testleri — pure fonksiyonlar, dış bağımlılıksız."""
from __future__ import annotations

import pytest

from app.domains.evals.schemas import EvalCase
from app.domains.evals.scorers.exact_match import ExactMatchScorer
from app.domains.evals.scorers.retrieval_metrics import (
    MRRScorer,
    PrecisionAtKScorer,
    RecallAtKScorer,
)


def _case(**kwargs) -> EvalCase:
    return EvalCase(
        id=kwargs.pop("id", "c"),
        inputs=kwargs.pop("inputs", {}),
        expected=kwargs.pop("expected", {}),
    )


class TestExactMatch:
    def test_match(self) -> None:
        out = ExactMatchScorer().score(
            case=_case(expected={"top_1": "x"}), actual={"top_1": "x"}
        )
        assert out.passed is True
        assert out.value == 1.0

    def test_mismatch(self) -> None:
        out = ExactMatchScorer().score(
            case=_case(expected={"top_1": "x"}), actual={"top_1": "y"}
        )
        assert out.passed is False
        assert out.value == 0.0

    def test_missing_expected(self) -> None:
        out = ExactMatchScorer().score(
            case=_case(expected={}), actual={"top_1": "x"}
        )
        assert out.passed is False
        assert out.value == 0.0


class TestPrecisionAtK:
    def test_p_at_1_hit(self) -> None:
        out = PrecisionAtKScorer(k=1, name="precision_at_1").score(
            case=_case(expected={"relevant_ids": ["a"]}),
            actual={"ranked_ids": ["a", "b", "c"]},
        )
        assert out.value == 1.0
        assert out.passed is True

    def test_p_at_1_miss(self) -> None:
        out = PrecisionAtKScorer(k=1, name="precision_at_1").score(
            case=_case(expected={"relevant_ids": ["a"]}),
            actual={"ranked_ids": ["x", "a"]},
        )
        assert out.value == 0.0
        assert out.passed is False

    def test_p_at_5_partial(self) -> None:
        out = PrecisionAtKScorer(k=5, name="precision_at_5").score(
            case=_case(expected={"relevant_ids": ["a", "b"]}),
            actual={"ranked_ids": ["a", "x", "b", "y", "z"]},
        )
        assert out.value == pytest.approx(2 / 5)
        # k > 1 için "passed" kriteri value > 0 → any hit
        assert out.passed is True

    def test_empty_ranked(self) -> None:
        out = PrecisionAtKScorer(k=5, name="precision_at_5").score(
            case=_case(expected={"relevant_ids": ["a"]}),
            actual={"ranked_ids": []},
        )
        assert out.value == 0.0
        assert out.passed is False


class TestMRR:
    def test_first_rank(self) -> None:
        out = MRRScorer().score(
            case=_case(expected={"relevant_ids": ["a"]}),
            actual={"ranked_ids": ["a", "b", "c"]},
        )
        assert out.value == 1.0

    def test_third_rank(self) -> None:
        out = MRRScorer().score(
            case=_case(expected={"relevant_ids": ["c"]}),
            actual={"ranked_ids": ["a", "b", "c", "d"]},
        )
        assert out.value == pytest.approx(1 / 3)

    def test_no_relevant_in_ranked(self) -> None:
        out = MRRScorer().score(
            case=_case(expected={"relevant_ids": ["z"]}),
            actual={"ranked_ids": ["a", "b"]},
        )
        assert out.value == 0.0
        assert out.passed is False


class TestRecallAtK:
    def test_full_recall(self) -> None:
        out = RecallAtKScorer(k=5, name="recall_at_5").score(
            case=_case(expected={"relevant_ids": ["a", "b"]}),
            actual={"ranked_ids": ["a", "x", "b", "y", "z"]},
        )
        assert out.value == 1.0
        assert out.passed is True

    def test_partial(self) -> None:
        out = RecallAtKScorer(k=3, name="recall_at_3").score(
            case=_case(expected={"relevant_ids": ["a", "b", "c"]}),
            actual={"ranked_ids": ["a", "x", "b"]},
        )
        assert out.value == pytest.approx(2 / 3)

    def test_empty_relevant(self) -> None:
        out = RecallAtKScorer(k=5, name="recall_at_5").score(
            case=_case(expected={"relevant_ids": []}),
            actual={"ranked_ids": ["a"]},
        )
        assert out.value == 0.0
        assert out.passed is False
