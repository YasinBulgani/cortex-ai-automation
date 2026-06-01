"""Unit tests for QA domain service — filesystem-backed functions.

Tests app/domains/qa/service.py using a temporary qa/ directory tree
so no real repo state is required.

Coverage:
- list_test_cases: empty dir, valid files, filter by suite/priority/automation/search
- get_test_case: unknown id, found id, missing cases dir
- create_test_case: unknown suite → ValueError, success path, seq numbering
- list_runs / get_run: empty dir, with runs
- health_score: returns HealthReport with all expected fields
- _build_last_status_map: empty runs, single run result
- coverage_summary: empty, mixed automation statuses
"""

from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest
import yaml

from app.domains.qa.models import CreateTestCaseRequest, HealthReport, TestCase, TestCaseListItem
from app.domains.qa import service as svc


# ── helpers ──────────────────────────────────────────────────────────────────


def _make_tc_md(
    tc_id: str,
    title: str,
    suite: str = "auth",
    priority: str = "P1",
    tc_type: str = "functional",
    status: str = "active",
    owner: str = "@qa",
    automation_status: str = "not-automated",
) -> str:
    """Return a minimal TC markdown with frontmatter."""
    return textwrap.dedent(f"""\
        ---
        id: {tc_id}
        title: {title}
        suite: {suite}
        priority: {priority}
        type:
          - {tc_type}
        status: {status}
        owner: {owner}
        created: "2026-01-01"
        updated: "2026-01-01"
        estimated_minutes: 5
        automation:
          status: {automation_status}
        requirements: []
        pre_conditions: []
        tags: []
        ---

        ## Steps
        | # | Step | Expected |
        |---|------|----------|
        | 1 | Open app | Login page |
    """)


def _make_run_yml(run_id: str, tc_id: str, status: str = "pass") -> dict:
    """Return a run YAML dict."""
    return {
        "id": run_id,
        "plan": "TP-smoke",
        "started": "2026-05-20T10:00:00+00:00",
        "ended": "2026-05-20T10:30:00+00:00",
        "executor": "@ci",
        "environment": {"branch": "main", "commit": "abc1234", "env": "staging"},
        "summary": {"total": 1, "passed": 1, "failed": 0, "blocked": 0, "skipped": 0, "untested": 0},
        "results": [{"tc": tc_id, "tc_commit": "abc1234", "status": status}],
    }


# ── list_test_cases ───────────────────────────────────────────────────────────


class TestListTestCases:
    def test_empty_cases_dir_returns_empty_list(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        (qa_root / "cases").mkdir()
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases()
        assert result == []

    def test_missing_cases_dir_returns_empty_list(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.list_test_cases()
        assert result == []

    def test_single_valid_file_returned(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-login.md").write_text(
            _make_tc_md("TC-AUTH-001", "Login with valid credentials"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases()
        assert len(result) == 1
        assert result[0].id == "TC-AUTH-001"
        assert isinstance(result[0], TestCaseListItem)

    def test_filter_by_suite(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        for suite, tc_id in [("auth", "TC-AUTH-001"), ("billing", "TC-BIL-001")]:
            d = qa_root / "cases" / suite
            d.mkdir(parents=True)
            (d / f"{tc_id}-test.md").write_text(
                _make_tc_md(tc_id, f"{suite} test", suite=suite), encoding="utf-8"
            )
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases(suite="auth")
        assert len(result) == 1
        assert result[0].id == "TC-AUTH-001"

    def test_filter_by_priority(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-p0.md").write_text(
            _make_tc_md("TC-AUTH-001", "P0 test", priority="P0"), encoding="utf-8"
        )
        (cases / "TC-AUTH-002-p2.md").write_text(
            _make_tc_md("TC-AUTH-002", "P2 test", priority="P2"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases(priority="P0")
        assert len(result) == 1
        assert result[0].id == "TC-AUTH-001"

    def test_filter_by_automation_status(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-manual.md").write_text(
            _make_tc_md("TC-AUTH-001", "Manual test", automation_status="not-automated"), encoding="utf-8"
        )
        (cases / "TC-AUTH-002-auto.md").write_text(
            _make_tc_md("TC-AUTH-002", "Auto test", automation_status="automated"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases(automation_status="automated")
        assert len(result) == 1
        assert result[0].id == "TC-AUTH-002"

    def test_search_by_title(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-login.md").write_text(
            _make_tc_md("TC-AUTH-001", "Login with valid credentials"), encoding="utf-8"
        )
        (cases / "TC-AUTH-002-logout.md").write_text(
            _make_tc_md("TC-AUTH-002", "Logout session"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases(search="login")
        assert len(result) == 1
        assert result[0].id == "TC-AUTH-001"

    def test_files_without_frontmatter_are_skipped(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-empty.md").write_text("No frontmatter here", encoding="utf-8")
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.list_test_cases()
        assert result == []


# ── get_test_case ─────────────────────────────────────────────────────────────


class TestGetTestCase:
    def test_unknown_id_returns_none(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-login.md").write_text(
            _make_tc_md("TC-AUTH-001", "Login test"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.get_test_case("TC-AUTH-999")
        assert result is None

    def test_missing_cases_dir_returns_none(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.get_test_case("TC-AUTH-001")
        assert result is None

    def test_found_id_returns_test_case_object(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-login.md").write_text(
            _make_tc_md("TC-AUTH-001", "Login with valid credentials"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.get_test_case("TC-AUTH-001")
        assert result is not None
        assert isinstance(result, TestCase)
        assert result.id == "TC-AUTH-001"
        assert result.title == "Login with valid credentials"

    def test_automation_field_defaults_when_missing(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        # Frontmatter without automation field
        md = textwrap.dedent("""\
            ---
            id: TC-AUTH-002
            title: No automation field
            suite: auth
            priority: P2
            type:
              - functional
            status: active
            owner: "@qa"
            created: "2026-01-01"
            updated: "2026-01-01"
            ---
            body
        """)
        (cases / "TC-AUTH-002-test.md").write_text(md, encoding="utf-8")
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.get_test_case("TC-AUTH-002")
        assert result is not None
        assert result.automation.status == "not-automated"


# ── create_test_case ──────────────────────────────────────────────────────────


class TestCreateTestCase:
    def test_unknown_suite_raises_value_error(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        req = CreateTestCaseRequest(suite="unknown-suite", title="Test")
        with patch.object(svc, "QA_ROOT", qa_root):
            with pytest.raises(ValueError, match="Unknown suite"):
                svc.create_test_case(req)

    def test_missing_title_creates_with_provided_title(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        req = CreateTestCaseRequest(suite="auth", title="My new test case")
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.create_test_case(req)
        assert result.title == "My new test case"
        assert result.suite == "auth"
        assert result.id.startswith("TC-AUTH-")

    def test_creates_file_on_disk(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        req = CreateTestCaseRequest(suite="billing", title="Invoice generation")
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.create_test_case(req)
        suite_dir = qa_root / "cases" / "billing"
        files = list(suite_dir.glob("TC-BIL-*.md"))
        assert len(files) == 1
        assert result.id in files[0].name

    def test_sequential_numbering(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        req1 = CreateTestCaseRequest(suite="auth", title="First test")
        req2 = CreateTestCaseRequest(suite="auth", title="Second test")
        with patch.object(svc, "QA_ROOT", qa_root):
            tc1 = svc.create_test_case(req1)
            tc2 = svc.create_test_case(req2)
        assert tc1.id == "TC-AUTH-001"
        assert tc2.id == "TC-AUTH-002"

    def test_returns_test_case_with_draft_status(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        req = CreateTestCaseRequest(suite="api-tests", title="API endpoint test")
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.create_test_case(req)
        assert result.status == "draft"
        assert result.automation.status == "not-automated"


# ── list_runs / get_run ───────────────────────────────────────────────────────


class TestListRuns:
    def test_empty_runs_dir_returns_empty_list(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "runs").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.list_runs()
        assert result == []

    def test_missing_runs_dir_returns_empty_list(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.list_runs()
        assert result == []

    def test_single_run_file_returned(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        run_dir = qa_root / "runs" / "2026" / "05"
        run_dir.mkdir(parents=True)
        run_data = _make_run_yml("TR-2026-05-20-SMOKE-001", "TC-AUTH-001")
        run_file = run_dir / "TR-2026-05-20-SMOKE-001.yml"
        run_file.write_text(yaml.safe_dump(run_data), encoding="utf-8")
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.list_runs()
        assert len(result) == 1
        assert result[0].id == "TR-2026-05-20-SMOKE-001"

    def test_get_run_returns_none_for_unknown_id(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "runs").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.get_run("TR-DOES-NOT-EXIST")
        assert result is None

    def test_get_run_returns_test_run_for_known_id(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        run_dir = qa_root / "runs" / "2026" / "05"
        run_dir.mkdir(parents=True)
        run_data = _make_run_yml("TR-2026-05-20-SMOKE-001", "TC-AUTH-001")
        run_file = run_dir / "TR-2026-05-20-SMOKE-001.yml"
        run_file.write_text(yaml.safe_dump(run_data), encoding="utf-8")
        with patch.object(svc, "QA_ROOT", qa_root):
            result = svc.get_run("TR-2026-05-20-SMOKE-001")
        assert result is not None
        assert result.id == "TR-2026-05-20-SMOKE-001"
        assert result.plan == "TP-smoke"


# ── health_score ──────────────────────────────────────────────────────────────


class TestHealthScore:
    def test_returns_health_report_instance(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        (qa_root / "runs").mkdir(parents=True)
        (qa_root / "requirements").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(20, "0 fail")):
                report = svc.health_score()
        assert isinstance(report, HealthReport)

    def test_health_report_has_all_fields(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        (qa_root / "runs").mkdir(parents=True)
        (qa_root / "requirements").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(20, "0 fail")):
                report = svc.health_score()
        assert hasattr(report, "total")
        assert hasattr(report, "max")
        assert hasattr(report, "grade")
        assert hasattr(report, "components")
        assert hasattr(report, "stats")
        assert hasattr(report, "generated_at")

    def test_health_report_max_is_100(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        (qa_root / "runs").mkdir(parents=True)
        (qa_root / "requirements").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(20, "0 fail")):
                report = svc.health_score()
        assert report.max == 100

    def test_health_report_grade_is_valid(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        (qa_root / "runs").mkdir(parents=True)
        (qa_root / "requirements").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(20, "0 fail")):
                report = svc.health_score()
        assert report.grade in ("A", "B", "C", "D", "F")

    def test_health_report_components_coverage_fields(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        (qa_root / "runs").mkdir(parents=True)
        (qa_root / "requirements").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(20, "0 fail")):
                report = svc.health_score()
        expected_keys = {"validation", "automation", "requirements", "pre_conditions", "run_freshness", "flakiness", "open_defects"}
        assert expected_keys.issubset(report.components.keys())

    def test_health_stats_contains_counts(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        (qa_root / "runs").mkdir(parents=True)
        (qa_root / "requirements").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(20, "0 fail")):
                report = svc.health_score()
        assert "test_cases" in report.stats
        assert "requirements" in report.stats
        assert "runs" in report.stats

    def test_empty_qa_root_gives_grade_without_crash(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        qa_root.mkdir()
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_run_validate", return_value=(0, "node not available")):
                report = svc.health_score()
        # Should not crash, grade must be assigned
        assert report.grade in ("A", "B", "C", "D", "F")


# ── coverage_summary ──────────────────────────────────────────────────────────


class TestCoverageSummary:
    def test_empty_returns_zero_totals(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        (qa_root / "cases").mkdir(parents=True)
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.coverage_summary()
        assert result.total_tcs == 0
        assert result.automated_count == 0
        assert result.automation_pct == 0

    def test_counts_automated_correctly(self, tmp_path: Path) -> None:
        qa_root = tmp_path / "qa"
        cases = qa_root / "cases" / "auth"
        cases.mkdir(parents=True)
        (cases / "TC-AUTH-001-auto.md").write_text(
            _make_tc_md("TC-AUTH-001", "Auto test", automation_status="automated"), encoding="utf-8"
        )
        (cases / "TC-AUTH-002-manual.md").write_text(
            _make_tc_md("TC-AUTH-002", "Manual test", automation_status="not-automated"), encoding="utf-8"
        )
        with patch.object(svc, "QA_ROOT", qa_root):
            with patch.object(svc, "_build_last_status_map", return_value={}):
                result = svc.coverage_summary()
        assert result.total_tcs == 2
        assert result.automated_count == 1
        assert result.automation_pct == 50
