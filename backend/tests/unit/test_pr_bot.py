"""PR bot service — build + render davranışı."""
from __future__ import annotations

from pathlib import Path
from typing import List

import pytest

from app.domains.pr_bot.service import (
    EvalSnapshot,
    PRSuggestion,
    build_pr_summary,
    render_markdown,
)


def _mk_repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "mod.py").write_text("X = 1\n")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_mod.py").write_text(
        "from app.mod import X\n\ndef test_x():\n    assert X\n"
    )
    return tmp_path


# ── build_pr_summary ─────────────────────────────────────────────────────


def test_build_with_impacted_tests(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
    )
    assert s.impact.run_all is False
    assert "tests/test_mod.py" in s.impact.tests
    assert s.changed_files_count == 1
    assert s.has_blocking_issues() is False


def test_build_blocking_eval_fail(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        eval_snapshot=EvalSnapshot(
            overall_passed=False, failed_suites=1, total_suites=3
        ),
    )
    assert s.has_blocking_issues() is True


def test_llm_suggester_integrated(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)

    def _suggester(changed: List[str], tests: List[str]) -> List[PRSuggestion]:
        return [
            PRSuggestion(
                title="Edge case: boş liste",
                rationale="mod.py fonksiyonu liste alıyor; boş giriş için test eksik.",
                confidence=0.7,
            )
        ]

    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        llm_suggester=_suggester,
    )
    assert len(s.suggestions) == 1
    assert s.suggestions[0].title.startswith("Edge case")


def test_llm_suggester_errors_dont_break(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)

    def _boom(changed: List[str], tests: List[str]) -> List[PRSuggestion]:
        raise RuntimeError("LLM down")

    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        llm_suggester=_boom,
    )
    assert s.suggestions == []
    # Geri kalan tam çalışır
    assert s.changed_files_count == 1


def test_llm_suggester_capped_at_five(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)

    def _many(changed: List[str], tests: List[str]) -> List[PRSuggestion]:
        return [
            PRSuggestion(title=f"t{i}", rationale="r", confidence=0.5)
            for i in range(10)
        ]

    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        llm_suggester=_many,
    )
    assert len(s.suggestions) == 5


# ── render_markdown ─────────────────────────────────────────────────────


def test_render_has_title_and_counters(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
    )
    md = render_markdown(s)
    assert "Shift-left PR Bot" in md
    assert "Değişen dosya" in md
    assert "Etkilenen test" in md
    assert "tests/test_mod.py" in md


def test_render_icon_success_when_clean(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        eval_snapshot=EvalSnapshot(
            overall_passed=True, failed_suites=0, total_suites=3
        ),
    )
    md = render_markdown(s)
    assert md.startswith("## ✅")


def test_render_icon_fail_on_eval(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        eval_snapshot=EvalSnapshot(
            overall_passed=False, failed_suites=2, total_suites=3
        ),
    )
    md = render_markdown(s)
    assert md.startswith("## ❌")
    assert "2 fail" in md


def test_render_run_all_note(tmp_path: Path) -> None:
    # 40/100 → too_many_changes → run_all
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=[f"app/f{i}.py" for i in range(40)],
        total_src_count=100,
    )
    assert s.impact.run_all is True
    md = render_markdown(s)
    assert "test-full" in md.lower()
    assert "tüm suite" in md.lower()


def test_render_suggestions_block(tmp_path: Path) -> None:
    root = _mk_repo(tmp_path)

    def _sug(c: List[str], t: List[str]) -> List[PRSuggestion]:
        return [PRSuggestion(title="Null check ekle", rationale="guard eksik", confidence=0.88)]

    s = build_pr_summary(
        repo_root=root,
        changed_files=["app/mod.py"],
        test_roots=[root / "tests"],
        llm_suggester=_sug,
    )
    md = render_markdown(s)
    assert "Öneriler" in md
    assert "Null check ekle" in md
    assert "0.88" in md


def test_render_no_changes_shows_title(tmp_path: Path) -> None:
    # Boş diff — örn. force-push'tan sonra. run_all=False, reason='no_changes'
    root = _mk_repo(tmp_path)
    s = build_pr_summary(
        repo_root=root,
        changed_files=[],
        test_roots=[root / "tests"],
    )
    md = render_markdown(s)
    assert "Shift-left PR Bot" in md
    assert "Değişen dosya" in md
    assert s.impact.reason == "no_changes"
