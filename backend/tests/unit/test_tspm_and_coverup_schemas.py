"""Unit tests for tspm.schemas helpers and coverup.schemas Pydantic models.

Tests are fully self-contained: no DB, no HTTP, no LLM.
Covers:
  - _strip_html: HTML tag removal, control char removal, stripping
  - ProjectCreate: name/description sanitization, min/max length, product_id
  - ScenarioCreate: status validation, tag sanitization, HTML sanitization
  - DashboardStats: defaults
  - GlobalDashboardOut: defaults, nested lists
  - coverup.schemas: FileCoverage, CoverageGapTarget, CoverageUploadRequest defaults
"""
from __future__ import annotations

import pytest

try:
    from app.domains.tspm.schemas import (
        _strip_html,
        ProjectCreate,
        ScenarioCreate,
        ScenarioUpdate,
        DashboardStats,
        GlobalDashboardOut,
        WeeklyTrendPoint,
    )
    _TSPM_OK = True
except ImportError:
    _TSPM_OK = False

try:
    from app.domains.coverup.schemas import (
        CoverageUploadRequest,
        FileCoverage,
        CoverageSummary,
        CoverageGapTarget,
        AnalyzeRequest,
    )
    _COVERUP_OK = True
except ImportError:
    _COVERUP_OK = False


# ---------------------------------------------------------------------------
# _strip_html
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TSPM_OK, reason="tspm.schemas import failed")
class TestStripHtml:
    def test_plain_text_unchanged(self):
        assert _strip_html("hello world") == "hello world"

    def test_script_tag_removed(self):
        result = _strip_html("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "alert('xss')" in result

    def test_anchor_tag_removed(self):
        result = _strip_html('<a href="http://evil.com">click</a>')
        assert "<a" not in result
        assert "click" in result

    def test_nested_tags_removed(self):
        result = _strip_html("<div><b>bold text</b></div>")
        assert "<div>" not in result
        assert "<b>" not in result
        assert "bold text" in result

    def test_null_byte_removed(self):
        result = _strip_html("hello\x00world")
        assert "\x00" not in result

    def test_control_char_removed(self):
        result = _strip_html("test\x01value")
        assert "\x01" not in result

    def test_newline_preserved(self):
        # \n is NOT a control char in _CONTROL_RE (range is \x0b-\x0c, not \n=\x0a)
        result = _strip_html("line1\nline2")
        assert "\n" in result

    def test_whitespace_stripped(self):
        assert _strip_html("  hello  ") == "hello"

    def test_empty_string(self):
        assert _strip_html("") == ""

    def test_returns_string(self):
        assert isinstance(_strip_html("test"), str)


# ---------------------------------------------------------------------------
# ProjectCreate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TSPM_OK, reason="tspm.schemas import failed")
class TestProjectCreate:
    def test_minimal_creation(self):
        p = ProjectCreate(name="Banking Tests")
        assert p.name == "Banking Tests"

    def test_description_default_empty(self):
        p = ProjectCreate(name="Test")
        assert p.description == ""

    def test_base_url_default_empty(self):
        p = ProjectCreate(name="Test")
        assert p.base_url == ""

    def test_product_tags_default_empty(self):
        p = ProjectCreate(name="Test")
        assert p.product_tags == []

    def test_html_stripped_from_name(self):
        p = ProjectCreate(name="<b>Banking</b>")
        assert "<b>" not in p.name
        assert "Banking" in p.name

    def test_html_stripped_from_description(self):
        p = ProjectCreate(name="Test", description="<script>xss</script>desc")
        assert "<script>" not in p.description

    def test_html_stripped_from_base_url(self):
        p = ProjectCreate(name="Test", base_url="http://bank.com/<b>")
        assert "<b>" not in p.base_url

    def test_name_min_length_enforced(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProjectCreate(name="")

    def test_name_max_length_enforced(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProjectCreate(name="x" * 201)

    def test_description_max_length_enforced(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ProjectCreate(name="Test", description="x" * 2001)


# ---------------------------------------------------------------------------
# ScenarioCreate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TSPM_OK, reason="tspm.schemas import failed")
class TestScenarioCreate:
    def test_minimal_creation(self):
        s = ScenarioCreate(title="Login Test")
        assert s.title == "Login Test"

    def test_status_default_draft(self):
        s = ScenarioCreate(title="Test")
        assert s.status == "draft"

    def test_valid_statuses(self):
        for status in ("draft", "active", "deprecated", "pending", "approved", "rejected"):
            s = ScenarioCreate(title="T", status=status)
            assert s.status == status

    def test_invalid_status_falls_back_to_draft(self):
        s = ScenarioCreate(title="T", status="unknown_status")
        assert s.status == "draft"

    def test_html_stripped_from_title(self):
        s = ScenarioCreate(title="<b>Test</b>")
        assert "<b>" not in s.title
        assert "Test" in s.title

    def test_tags_sanitized(self):
        s = ScenarioCreate(title="T", tags=["<b>tag1</b>", "tag2"])
        assert "<b>" not in s.tags[0]
        assert "tag2" in s.tags

    def test_tags_truncated_to_30(self):
        s = ScenarioCreate(title="T", tags=[f"tag{i}" for i in range(50)])
        assert len(s.tags) == 30

    def test_tag_text_length_truncated_to_50(self):
        long_tag = "x" * 100
        s = ScenarioCreate(title="T", tags=[long_tag])
        assert len(s.tags[0]) <= 50

    def test_invalid_tags_replaced_by_empty_list(self):
        s = ScenarioCreate(title="T", tags="not_a_list")  # type: ignore
        assert isinstance(s.tags, list)

    def test_steps_default_empty(self):
        s = ScenarioCreate(title="T")
        assert s.steps == []

    def test_title_min_length(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ScenarioCreate(title="")

    def test_description_html_stripped(self):
        s = ScenarioCreate(title="T", description="<img src=x onerror=alert(1)>desc")
        assert "<img" not in s.description


# ---------------------------------------------------------------------------
# ScenarioUpdate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TSPM_OK, reason="tspm.schemas import failed")
class TestScenarioUpdate:
    def test_all_fields_optional(self):
        su = ScenarioUpdate()
        assert su.title is None
        assert su.description is None
        assert su.status is None
        assert su.steps is None
        assert su.tags is None

    def test_partial_update_allowed(self):
        su = ScenarioUpdate(title="New Title")
        assert su.title == "New Title"
        assert su.description is None

    def test_html_stripped_from_title(self):
        su = ScenarioUpdate(title="<script>evil</script>Title")
        assert "<script>" not in su.title  # type: ignore[operator]

    def test_tags_none_passthrough(self):
        su = ScenarioUpdate(tags=None)
        assert su.tags is None


# ---------------------------------------------------------------------------
# DashboardStats
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TSPM_OK, reason="tspm.schemas import failed")
class TestDashboardStats:
    def test_all_defaults_zero(self):
        d = DashboardStats()
        assert d.scenario_count == 0
        assert d.pending_approvals == 0
        assert d.import_count == 0
        assert d.ai_run_pending == 0
        assert d.execution_count == 0

    def test_latest_run_pass_rate_default_none(self):
        d = DashboardStats()
        assert d.latest_run_pass_rate is None

    def test_creation_with_values(self):
        d = DashboardStats(scenario_count=10, execution_count=5)
        assert d.scenario_count == 10
        assert d.execution_count == 5


# ---------------------------------------------------------------------------
# GlobalDashboardOut
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _TSPM_OK, reason="tspm.schemas import failed")
class TestGlobalDashboardOut:
    def test_all_defaults(self):
        g = GlobalDashboardOut()
        assert g.total_projects == 0
        assert g.total_scenarios == 0
        assert g.active_executions == 0
        assert g.overall_pass_rate == pytest.approx(0.0)
        assert g.pending_approvals == 0

    def test_empty_lists_default(self):
        g = GlobalDashboardOut()
        assert g.weekly_trend == []
        assert g.projects == []
        assert g.activities == []

    def test_weekly_trend_point(self):
        p = WeeklyTrendPoint(day="Monday", runs=5, passed=4)
        g = GlobalDashboardOut(weekly_trend=[p])
        assert g.weekly_trend[0].day == "Monday"
        assert g.weekly_trend[0].runs == 5


# ---------------------------------------------------------------------------
# FileCoverage (coverup.schemas)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERUP_OK, reason="coverup.schemas import failed")
class TestFileCoverage:
    def test_creation_with_file_path(self):
        f = FileCoverage(file_path="src/login.py")
        assert f.file_path == "src/login.py"

    def test_defaults_zero(self):
        f = FileCoverage(file_path="f.py")
        assert f.total_lines == 0
        assert f.covered_lines == 0
        assert f.missed_lines == 0
        assert f.line_rate == pytest.approx(0.0)
        assert f.branch_rate == pytest.approx(0.0)

    def test_complexity_default_none(self):
        f = FileCoverage(file_path="f.py")
        assert f.complexity is None

    def test_lists_default_empty(self):
        f = FileCoverage(file_path="f.py")
        assert f.missed_line_numbers == []
        assert f.missed_branch_lines == []
        assert f.uncovered_functions == []

    def test_with_values(self):
        f = FileCoverage(
            file_path="app.py",
            total_lines=100,
            covered_lines=80,
            missed_lines=20,
            line_rate=0.8,
        )
        assert f.line_rate == pytest.approx(0.8)


# ---------------------------------------------------------------------------
# CoverageGapTarget
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERUP_OK, reason="coverup.schemas import failed")
class TestCoverageGapTarget:
    def test_creation(self):
        gap = CoverageGapTarget(
            file_path="src/login.py",
            start_line=10,
            end_line=20,
            gap_type="line",
        )
        assert gap.file_path == "src/login.py"
        assert gap.gap_type == "line"

    def test_function_name_default_none(self):
        gap = CoverageGapTarget(file_path="f.py", start_line=1, end_line=5, gap_type="branch")
        assert gap.function_name is None

    def test_risk_score_default(self):
        gap = CoverageGapTarget(file_path="f.py", start_line=1, end_line=5, gap_type="line")
        assert gap.risk_score == pytest.approx(0.5)

    def test_risk_score_min_bound(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CoverageGapTarget(file_path="f.py", start_line=1, end_line=5, gap_type="line", risk_score=-0.1)

    def test_risk_score_max_bound(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            CoverageGapTarget(file_path="f.py", start_line=1, end_line=5, gap_type="line", risk_score=1.1)

    def test_risk_factors_default_empty(self):
        gap = CoverageGapTarget(file_path="f.py", start_line=1, end_line=5, gap_type="function")
        assert gap.risk_factors == []


# ---------------------------------------------------------------------------
# CoverageUploadRequest
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERUP_OK, reason="coverup.schemas import failed")
class TestCoverageUploadRequest:
    def test_creation(self):
        req = CoverageUploadRequest(
            project_id="proj-123",
            format="lcov",
            report_data="TN:\nSF:src/app.js\nend_of_record",
        )
        assert req.project_id == "proj-123"
        assert req.format == "lcov"

    def test_defaults(self):
        req = CoverageUploadRequest(
            project_id="p",
            format="istanbul",
            report_data="{}",
        )
        assert req.project_name == ""
        assert req.commit_sha == ""
        assert req.branch == "main"


# ---------------------------------------------------------------------------
# AnalyzeRequest
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _COVERUP_OK, reason="coverup.schemas import failed")
class TestAnalyzeRequest:
    def test_creation(self):
        req = AnalyzeRequest(report_id="rpt-001")
        assert req.report_id == "rpt-001"

    def test_focus_paths_default_empty(self):
        req = AnalyzeRequest(report_id="rpt-001")
        assert req.focus_paths == []
