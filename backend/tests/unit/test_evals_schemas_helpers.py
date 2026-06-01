"""Unit tests for app.domains.evals.schemas — pure data types and helpers.

Tests are fully self-contained: no DB, no HTTP, no AI.
Covers: EvalCase.from_dict, SuiteThresholds.from_dict, Suite.from_dict,
        SuiteResult.case_pass_rate/count_passed, _default_max_workers (runner),
        _aggregate (runner).
"""
from __future__ import annotations

import os
import pytest

try:
    from app.domains.evals.schemas import (
        EvalCase,
        SuiteThresholds,
        Suite,
        SuiteResult,
        CaseResult,
        ScorerOutput,
    )
    from app.domains.evals.runner import (
        _default_max_workers,
        _aggregate,
    )
    _IMPORT_OK = True
except ImportError:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="evals schemas import failed")


# ---------------------------------------------------------------------------
# EvalCase.from_dict
# ---------------------------------------------------------------------------

class TestEvalCaseFromDict:
    def test_basic_case(self):
        raw = {"id": "case-1", "inputs": {"query": "test"}, "expected": {"answer": "ok"}}
        case = EvalCase.from_dict(raw)
        assert case.id == "case-1"
        assert case.inputs == {"query": "test"}
        assert case.expected == {"answer": "ok"}

    def test_missing_id_raises(self):
        with pytest.raises(ValueError, match="id"):
            EvalCase.from_dict({"inputs": {}, "expected": {}})

    def test_empty_id_raises(self):
        with pytest.raises(ValueError):
            EvalCase.from_dict({"id": "  ", "inputs": {}, "expected": {}})

    def test_default_tags_empty_tuple(self):
        case = EvalCase.from_dict({"id": "c1", "inputs": {}, "expected": {}})
        assert case.tags == ()

    def test_tags_parsed(self):
        case = EvalCase.from_dict({"id": "c1", "inputs": {}, "expected": {}, "tags": ["smoke", "auth"]})
        assert "smoke" in case.tags
        assert "auth" in case.tags

    def test_description_default_empty(self):
        case = EvalCase.from_dict({"id": "c1", "inputs": {}, "expected": {}})
        assert case.description == ""

    def test_returns_eval_case(self):
        case = EvalCase.from_dict({"id": "x", "inputs": {}, "expected": {}})
        assert isinstance(case, EvalCase)

    def test_none_inputs_becomes_empty_dict(self):
        case = EvalCase.from_dict({"id": "c1", "inputs": None, "expected": None})
        assert case.inputs == {}
        assert case.expected == {}


# ---------------------------------------------------------------------------
# SuiteThresholds.from_dict
# ---------------------------------------------------------------------------

class TestSuiteThresholdsFromDict:
    def test_none_returns_defaults(self):
        st = SuiteThresholds.from_dict(None)
        assert st.mean_thresholds == {}
        assert st.min_case_pass_rate == pytest.approx(1.0)

    def test_empty_dict_returns_defaults(self):
        st = SuiteThresholds.from_dict({})
        assert st.mean_thresholds == {}

    def test_mean_thresholds_parsed(self):
        st = SuiteThresholds.from_dict({"mean": {"precision": 0.8, "recall": 0.7}})
        assert st.mean_thresholds["precision"] == pytest.approx(0.8)
        assert st.mean_thresholds["recall"] == pytest.approx(0.7)

    def test_min_case_pass_rate_parsed(self):
        st = SuiteThresholds.from_dict({"min_case_pass_rate": 0.9})
        assert st.min_case_pass_rate == pytest.approx(0.9)

    def test_returns_suite_thresholds(self):
        assert isinstance(SuiteThresholds.from_dict(None), SuiteThresholds)


# ---------------------------------------------------------------------------
# Suite.from_dict
# ---------------------------------------------------------------------------

class TestSuiteFromDict:
    def _raw(self, **overrides):
        base = {
            "name": "my_suite",
            "adapter": "dsl_retrieval",
            "cases": [{"id": "c1", "inputs": {"q": "test"}, "expected": {"score": 1}}],
            "scorers": ["exact_match"],
        }
        base.update(overrides)
        return base

    def test_basic_suite(self):
        suite = Suite.from_dict(self._raw())
        assert suite.name == "my_suite"
        assert suite.adapter_name == "dsl_retrieval"

    def test_missing_name_raises(self):
        with pytest.raises(ValueError, match="name"):
            Suite.from_dict({"adapter": "x", "cases": [{"id": "c1", "inputs": {}, "expected": {}}], "scorers": ["s"]})

    def test_missing_adapter_raises(self):
        with pytest.raises(ValueError, match="adapter"):
            Suite.from_dict({"name": "s", "cases": [{"id": "c1", "inputs": {}, "expected": {}}], "scorers": ["s"]})

    def test_empty_cases_raises(self):
        with pytest.raises(ValueError):
            Suite.from_dict({"name": "s", "adapter": "a", "cases": [], "scorers": ["s"]})

    def test_empty_scorers_raises(self):
        with pytest.raises(ValueError):
            Suite.from_dict(self._raw(scorers=[]))

    def test_cases_are_eval_cases(self):
        suite = Suite.from_dict(self._raw())
        assert all(isinstance(c, EvalCase) for c in suite.cases)

    def test_scorers_tuple_of_strings(self):
        suite = Suite.from_dict(self._raw())
        assert all(isinstance(s, str) for s in suite.scorers)


# ---------------------------------------------------------------------------
# SuiteResult.case_pass_rate / count_passed
# ---------------------------------------------------------------------------

class TestSuiteResult:
    def _result(self, passed_cases=None):
        cases = [
            CaseResult(case_id=f"c{i}", passed=p, scores=[])
            for i, p in enumerate(passed_cases or [])
        ]
        return SuiteResult(suite_name="test", adapter_name="x", cases=cases)

    def test_empty_cases_pass_rate_zero(self):
        result = self._result([])
        assert result.case_pass_rate() == 0.0

    def test_all_passed_rate_one(self):
        result = self._result([True, True, True])
        assert result.case_pass_rate() == pytest.approx(1.0)

    def test_partial_pass_rate(self):
        result = self._result([True, False, True, False])
        assert result.case_pass_rate() == pytest.approx(0.5)

    def test_count_passed_correct(self):
        result = self._result([True, False, True])
        assert result.count_passed() == 2

    def test_count_passed_all_failed(self):
        result = self._result([False, False])
        assert result.count_passed() == 0


# ---------------------------------------------------------------------------
# _default_max_workers (runner)
# ---------------------------------------------------------------------------

class TestDefaultMaxWorkers:
    def test_default_value_four(self, monkeypatch):
        monkeypatch.delenv("EVAL_MAX_WORKERS", raising=False)
        assert _default_max_workers() == 4

    def test_reads_env(self, monkeypatch):
        monkeypatch.setenv("EVAL_MAX_WORKERS", "8")
        assert _default_max_workers() == 8

    def test_invalid_falls_back_to_four(self, monkeypatch):
        monkeypatch.setenv("EVAL_MAX_WORKERS", "bad")
        assert _default_max_workers() == 4

    def test_min_one(self, monkeypatch):
        monkeypatch.setenv("EVAL_MAX_WORKERS", "0")
        assert _default_max_workers() >= 1

    def test_max_32(self, monkeypatch):
        monkeypatch.setenv("EVAL_MAX_WORKERS", "100")
        assert _default_max_workers() <= 32


# ---------------------------------------------------------------------------
# _aggregate (runner)
# ---------------------------------------------------------------------------

class TestAggregate:
    def _suite_result(self, cases_data):
        """cases_data: list of (case_id, passed, scores_list) where scores_list is list of (name, value, passed)"""
        cases = []
        for case_id, passed, scores in cases_data:
            scorer_outputs = [
                ScorerOutput(name=n, value=v, passed=p)
                for n, v, p in scores
            ]
            cases.append(CaseResult(case_id=case_id, passed=passed, scores=scorer_outputs))
        return SuiteResult(suite_name="test", adapter_name="x", cases=cases)

    def test_empty_cases_no_aggregate(self):
        result = SuiteResult(suite_name="test", adapter_name="x", cases=[])
        _aggregate(result)
        assert result.aggregate == {}

    def test_aggregate_has_case_pass_rate(self):
        result = self._suite_result([("c1", True, [("exact", 1.0, True)])])
        _aggregate(result)
        assert "case_pass_rate" in result.aggregate

    def test_aggregate_mean_scorer(self):
        result = self._suite_result([
            ("c1", True, [("precision", 0.8, True)]),
            ("c2", True, [("precision", 0.6, True)]),
        ])
        _aggregate(result)
        assert result.aggregate.get("mean_precision") == pytest.approx(0.7, abs=1e-4)

    def test_total_latency_ms(self):
        result = self._suite_result([("c1", True, [])])
        result.cases[0].latency_ms = 500
        _aggregate(result)
        assert result.total_latency_ms == 500
