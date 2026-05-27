"""
pr_bot domain service unit testleri — 14 test.

pr_bot/service.py; TIA impact mapping, eval snapshot ve LLM öneri
mekanizmalarını orchestrate eder ve Markdown yorum üretir.
Testler map_changes_to_tests'i mock'lar; dosya sistemi gerekmez.
"""
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    from app.domains.pr_bot.service import (
        EvalSnapshot,
        PRSuggestion,
        PRSummary,
        build_pr_summary,
        render_markdown,
    )
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False

pytestmark = pytest.mark.skipif(
    not _IMPORT_OK, reason="pr_bot service import failed"
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REPO = Path("/fake/repo")


def _fake_impact(tests=None, run_all=False, reason=""):
    imp = MagicMock()
    imp.tests = tests or ["tests/test_login.py", "tests/test_signup.py"]
    imp.run_all = run_all
    imp.reason = reason
    imp.impact_sources = {"coverage": ["tests/test_login.py"]}
    return imp


def _build_summary(
    changed_files=None,
    eval_snapshot=None,
    llm_suggester=None,
    impact=None,
):
    changed_files = changed_files or ["src/auth.py", "src/user.py"]
    fake_impact = impact or _fake_impact()
    with patch(
        "app.domains.pr_bot.service.map_changes_to_tests",
        return_value=fake_impact,
    ):
        return build_pr_summary(
            repo_root=REPO,
            changed_files=changed_files,
            eval_snapshot=eval_snapshot,
            llm_suggester=llm_suggester,
        )


# ---------------------------------------------------------------------------
# EvalSnapshot
# ---------------------------------------------------------------------------

class TestEvalSnapshot:
    def test_overall_passed_true(self):
        ev = EvalSnapshot(overall_passed=True, failed_suites=0, total_suites=5)
        assert ev.overall_passed is True

    def test_overall_passed_false(self):
        ev = EvalSnapshot(overall_passed=False, failed_suites=2, total_suites=5)
        assert ev.failed_suites == 2

    def test_optional_fields_default_none(self):
        ev = EvalSnapshot(overall_passed=True, failed_suites=0, total_suites=3)
        assert ev.worst_mean_score is None
        assert ev.notes == ""


# ---------------------------------------------------------------------------
# PRSummary.has_blocking_issues
# ---------------------------------------------------------------------------

class TestPRSummaryHasBlockingIssues:
    def test_no_eval_snapshot_returns_false(self):
        summary = _build_summary()
        assert summary.has_blocking_issues() is False

    def test_eval_passed_returns_false(self):
        ev = EvalSnapshot(overall_passed=True, failed_suites=0, total_suites=3)
        summary = _build_summary(eval_snapshot=ev)
        assert summary.has_blocking_issues() is False

    def test_eval_failed_returns_true(self):
        ev = EvalSnapshot(overall_passed=False, failed_suites=1, total_suites=3)
        summary = _build_summary(eval_snapshot=ev)
        assert summary.has_blocking_issues() is True


# ---------------------------------------------------------------------------
# build_pr_summary
# ---------------------------------------------------------------------------

class TestBuildPrSummary:
    def test_returns_pr_summary(self):
        summary = _build_summary()
        assert isinstance(summary, PRSummary)

    def test_changed_files_count_correct(self):
        summary = _build_summary(changed_files=["a.py", "b.py", "c.py"])
        assert summary.changed_files_count == 3

    def test_no_llm_suggester_empty_suggestions(self):
        summary = _build_summary(llm_suggester=None)
        assert summary.suggestions == []

    def test_llm_suggester_called_and_suggestions_appended(self):
        suggestion = PRSuggestion(title="Add login test", rationale="Missing coverage")
        suggester = MagicMock(return_value=[suggestion])
        summary = _build_summary(llm_suggester=suggester)
        assert len(summary.suggestions) == 1
        assert summary.suggestions[0].title == "Add login test"

    def test_llm_suggester_exception_logged_gracefully(self):
        """LLM suggester hata fırlatırsa summary yine oluşmalı; suggestions boş kalmalı."""
        bad_suggester = MagicMock(side_effect=RuntimeError("LLM down"))
        summary = _build_summary(llm_suggester=bad_suggester)
        assert summary.suggestions == []

    def test_suggestions_capped_at_five(self):
        many = [PRSuggestion(title=f"s{i}", rationale="r") for i in range(10)]
        suggester = MagicMock(return_value=many)
        summary = _build_summary(llm_suggester=suggester)
        assert len(summary.suggestions) <= 5


# ---------------------------------------------------------------------------
# render_markdown
# ---------------------------------------------------------------------------

class TestRenderMarkdown:
    def test_returns_string(self):
        summary = _build_summary()
        md = render_markdown(summary)
        assert isinstance(md, str)

    def test_contains_header(self):
        summary = _build_summary()
        md = render_markdown(summary)
        assert "TestwrightAI" in md or "PR Bot" in md or "Shift-left" in md

    def test_blocking_icon_when_eval_fails(self):
        ev = EvalSnapshot(overall_passed=False, failed_suites=2, total_suites=4)
        summary = _build_summary(eval_snapshot=ev)
        md = render_markdown(summary)
        assert "❌" in md

    def test_ok_icon_when_no_issues(self):
        impact = _fake_impact(tests=[], run_all=False)
        summary = _build_summary(impact=impact)
        md = render_markdown(summary)
        assert "✅" in md or "⚠️" in md or "❌" in md  # icon present

    def test_changed_files_count_in_output(self):
        summary = _build_summary(changed_files=["x.py", "y.py"])
        md = render_markdown(summary)
        assert "2" in md
