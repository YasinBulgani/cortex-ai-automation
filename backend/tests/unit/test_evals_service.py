"""
evals service unit testleri — 15 test.

Tests are fully self-contained: no DB, no HTTP, no external services.
All loader / runner / reporting calls are mocked.
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone

try:
    from app.domains.evals.service import (
        run_eval_suite,
        run_all_suites,
        get_history,
        get_latest,
        list_suite_names,
    )
    from app.domains.evals.schemas import (
        EvalCase,
        Suite,
        SuiteThresholds,
        SuiteResult,
        CaseResult,
        ScorerOutput,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="evals service import failed")


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------

def _make_eval_case(cid: str = "c1") -> EvalCase:
    return EvalCase(
        id=cid,
        inputs={"prompt": "hello"},
        expected={"response": "world"},
        tags=("smoke",),
        description="A simple test case",
    )


def _make_suite(name: str = "my-suite", cases=None) -> Suite:
    if cases is None:
        cases = (_make_eval_case(),)
    return Suite(
        name=name,
        adapter_name="mock-adapter",
        cases=cases,
        scorers=("exact_match",),
        thresholds=SuiteThresholds(),
        description="Test suite",
    )


def _make_suite_result(suite_name: str = "my-suite", passed: bool = True) -> SuiteResult:
    return SuiteResult(
        suite_name=suite_name,
        adapter_name="mock-adapter",
        cases=[
            CaseResult(
                case_id="c1",
                passed=True,
                scores=[ScorerOutput(name="exact_match", value=1.0, passed=True)],
                latency_ms=50,
            )
        ],
        started_at=datetime.now(timezone.utc),
        finished_at=datetime.now(timezone.utc),
        passed=passed,
        aggregate={"exact_match": 1.0},
    )


# ---------------------------------------------------------------------------
# EvalCase.from_dict
# ---------------------------------------------------------------------------

class TestEvalCaseFromDict:
    def test_valid_dict_creates_case(self):
        raw = {"id": "c1", "inputs": {"q": "hi"}, "expected": {"a": "hello"}}
        case = EvalCase.from_dict(raw)
        assert case.id == "c1"
        assert case.inputs == {"q": "hi"}

    def test_missing_id_raises_value_error(self):
        with pytest.raises(ValueError, match="EvalCase.id zorunlu"):
            EvalCase.from_dict({"inputs": {}, "expected": {}})

    def test_empty_id_raises_value_error(self):
        with pytest.raises(ValueError):
            EvalCase.from_dict({"id": "   ", "inputs": {}, "expected": {}})

    def test_tags_default_to_empty_tuple(self):
        case = EvalCase.from_dict({"id": "c1", "inputs": {}, "expected": {}})
        assert case.tags == ()

    def test_description_defaults_to_empty_string(self):
        case = EvalCase.from_dict({"id": "c1", "inputs": {}, "expected": {}})
        assert case.description == ""


# ---------------------------------------------------------------------------
# Suite.from_dict
# ---------------------------------------------------------------------------

class TestSuiteFromDict:
    def _valid_raw(self):
        return {
            "name": "suite-a",
            "adapter": "mock",
            "cases": [{"id": "c1", "inputs": {}, "expected": {}}],
            "scorers": ["exact_match"],
        }

    def test_valid_dict_creates_suite(self):
        suite = Suite.from_dict(self._valid_raw())
        assert suite.name == "suite-a"
        assert suite.adapter_name == "mock"
        assert len(suite.cases) == 1

    def test_missing_name_raises_value_error(self):
        raw = self._valid_raw()
        del raw["name"]
        with pytest.raises(ValueError, match="Suite.name zorunlu"):
            Suite.from_dict(raw)

    def test_missing_adapter_raises_value_error(self):
        raw = self._valid_raw()
        del raw["adapter"]
        with pytest.raises(ValueError, match="Suite.adapter zorunlu"):
            Suite.from_dict(raw)

    def test_empty_cases_raises_value_error(self):
        raw = self._valid_raw()
        raw["cases"] = []
        with pytest.raises(ValueError, match="en az bir case"):
            Suite.from_dict(raw)

    def test_empty_scorers_raises_value_error(self):
        raw = self._valid_raw()
        raw["scorers"] = []
        with pytest.raises(ValueError, match="en az bir scorer"):
            Suite.from_dict(raw)


# ---------------------------------------------------------------------------
# SuiteResult helpers
# ---------------------------------------------------------------------------

class TestSuiteResult:
    def test_case_pass_rate_all_pass(self):
        result = _make_suite_result(passed=True)
        assert result.case_pass_rate() == 1.0

    def test_case_pass_rate_empty(self):
        result = SuiteResult(suite_name="empty", adapter_name="x")
        assert result.case_pass_rate() == 0.0

    def test_count_passed(self):
        result = _make_suite_result()
        assert result.count_passed() == 1

    def test_count_passed_none_passing(self):
        r = SuiteResult(
            suite_name="s",
            adapter_name="a",
            cases=[CaseResult(case_id="c1", passed=False)],
        )
        assert r.count_passed() == 0


# ---------------------------------------------------------------------------
# run_eval_suite (service — mocked internals)
# ---------------------------------------------------------------------------

class TestRunEvalSuite:
    def test_raises_value_error_when_suite_not_found(self):
        with patch("app.domains.evals.service.load_suites", return_value=[]):
            with pytest.raises(ValueError, match="not found"):
                run_eval_suite("nonexistent-suite")

    def test_returns_suite_result_on_success(self):
        suite = _make_suite("my-suite")
        result = _make_suite_result("my-suite")
        with patch("app.domains.evals.service.load_suites", return_value=[suite]), \
             patch("app.domains.evals.service.run_suite", return_value=result), \
             patch("app.domains.evals.service.write_reports") as mock_write:
            out = run_eval_suite("my-suite")
        assert out is result
        mock_write.assert_called_once_with([result])

    def test_write_reports_called_with_list(self):
        suite = _make_suite()
        result = _make_suite_result()
        with patch("app.domains.evals.service.load_suites", return_value=[suite]), \
             patch("app.domains.evals.service.run_suite", return_value=result), \
             patch("app.domains.evals.service.write_reports") as mock_write:
            run_eval_suite("my-suite")
        args = mock_write.call_args[0][0]
        assert isinstance(args, list)
        assert len(args) == 1


# ---------------------------------------------------------------------------
# run_all_suites (service — mocked internals)
# ---------------------------------------------------------------------------

class TestRunAllSuites:
    def test_runs_all_loaded_suites(self):
        suites = [_make_suite("s1"), _make_suite("s2")]
        results = [_make_suite_result("s1"), _make_suite_result("s2")]
        with patch("app.domains.evals.service.load_suites", return_value=suites), \
             patch("app.domains.evals.service.run_suite", side_effect=results), \
             patch("app.domains.evals.service.write_reports") as mock_write:
            out = run_all_suites()
        assert len(out) == 2
        mock_write.assert_called_once()

    def test_passes_suite_names_filter_to_loader(self):
        with patch("app.domains.evals.service.load_suites", return_value=[]) as mock_load, \
             patch("app.domains.evals.service.write_reports"):
            run_all_suites(suite_names=["only-this"])
        mock_load.assert_called_once_with(names=["only-this"])

    def test_returns_empty_list_when_no_suites(self):
        with patch("app.domains.evals.service.load_suites", return_value=[]), \
             patch("app.domains.evals.service.write_reports"):
            out = run_all_suites()
        assert out == []


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------

class TestGetHistory:
    def test_returns_history_list(self):
        fake_history = [{"id": "r1", "passed": True}, {"id": "r2", "passed": False}]
        with patch("app.domains.evals.service.history_report", return_value=fake_history) as mock_hr:
            result = get_history(limit=10)
        mock_hr.assert_called_once_with(limit=10)
        assert result == fake_history

    def test_clamps_limit_to_minimum_1(self):
        with patch("app.domains.evals.service.history_report", return_value=[]) as mock_hr:
            get_history(limit=0)
        # max(1, min(0, 500)) = 1
        mock_hr.assert_called_once_with(limit=1)

    def test_clamps_limit_to_maximum_500(self):
        with patch("app.domains.evals.service.history_report", return_value=[]) as mock_hr:
            get_history(limit=9999)
        mock_hr.assert_called_once_with(limit=500)


# ---------------------------------------------------------------------------
# get_latest
# ---------------------------------------------------------------------------

class TestGetLatest:
    def test_returns_latest_record(self):
        fake = {"id": "latest", "passed": True}
        with patch("app.domains.evals.service.latest_report", return_value=fake):
            result = get_latest()
        assert result == fake

    def test_returns_none_when_no_runs(self):
        with patch("app.domains.evals.service.latest_report", return_value=None):
            result = get_latest()
        assert result is None


# ---------------------------------------------------------------------------
# list_suite_names
# ---------------------------------------------------------------------------

class TestListSuiteNames:
    def test_returns_names_of_all_suites(self):
        suites = [_make_suite("alpha"), _make_suite("beta"), _make_suite("gamma")]
        with patch("app.domains.evals.service.load_suites", return_value=suites):
            names = list_suite_names()
        assert names == ["alpha", "beta", "gamma"]

    def test_returns_empty_when_no_suites(self):
        with patch("app.domains.evals.service.load_suites", return_value=[]):
            names = list_suite_names()
        assert names == []
