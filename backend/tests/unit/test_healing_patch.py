"""Patch applier unit testleri — güvenli replace semantiği.

Repo kökü olarak ``tmp_path`` kullanılır — gerçek proje dosyalarına
dokunulmaz.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.coverup.healing.patch_applier import apply_locator_swap


def _mkfile(root: Path, rel: str, content: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def test_happy_path_unique_replace(tmp_path: Path) -> None:
    _mkfile(
        tmp_path,
        "tests/login.spec.ts",
        "import { test } from '@playwright/test';\ntest('login', async ({ page }) => {\n  await page.locator('.submit-btn').click();\n});\n",
    )
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/login.spec.ts",
        old_locator=".submit-btn",
        new_locator="[data-testid='submit']",
    )
    assert res.success is True
    assert res.occurrences_before == 1
    assert res.line_number == 3
    content = (tmp_path / "tests/login.spec.ts").read_text()
    assert ".submit-btn" not in content
    assert "[data-testid='submit']" in content


def test_ambiguous_locator_refused(tmp_path: Path) -> None:
    _mkfile(
        tmp_path,
        "tests/x.spec.ts",
        "await page.locator('.btn').click();\nawait page.locator('.btn').isVisible();\n",
    )
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/x.spec.ts",
        old_locator=".btn",
        new_locator="[data-testid='x']",
    )
    assert res.success is False
    assert res.occurrences_before == 2
    assert "ambiguous" in res.reason


def test_locator_not_in_file(tmp_path: Path) -> None:
    _mkfile(tmp_path, "tests/x.spec.ts", "// empty\n")
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/x.spec.ts",
        old_locator=".missing",
        new_locator=".new",
    )
    assert res.success is False
    assert res.reason == "locator_not_in_file"


def test_file_not_found(tmp_path: Path) -> None:
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/nonexistent.spec.ts",
        old_locator="a",
        new_locator="b",
    )
    assert res.success is False
    assert res.reason == "file_not_found"


def test_path_traversal_rejected(tmp_path: Path) -> None:
    _mkfile(tmp_path, "safe.ts", "'.x'")
    # '..' ile kök dışına çıkmaya çalışma
    outside = tmp_path.parent / "outside.ts"
    try:
        outside.write_text("'.x'")
    except OSError:
        pytest.skip("tmp parent writable değil")

    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="../outside.ts",
        old_locator=".x",
        new_locator=".y",
    )
    assert res.success is False
    assert "path_unsafe" in res.reason


def test_absolute_path_rejected(tmp_path: Path) -> None:
    p = _mkfile(tmp_path, "tests/x.spec.ts", "'.x'")
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative=str(p.resolve()),  # mutlak
        old_locator=".x",
        new_locator=".y",
    )
    assert res.success is False
    assert "path_unsafe" in res.reason


def test_line_mismatch_beyond_tolerance(tmp_path: Path) -> None:
    # 10. satırda eşleşme; caller expected_line=3 → 7 satır fark → reddet
    lines = ["// line\n"] * 9 + ["await page.locator('.x').click();\n"]
    _mkfile(tmp_path, "tests/x.spec.ts", "".join(lines))
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/x.spec.ts",
        old_locator=".x",
        new_locator=".y",
        expected_line=3,
    )
    assert res.success is False
    assert "line_mismatch" in res.reason


def test_line_mismatch_within_tolerance(tmp_path: Path) -> None:
    # 5. satır; expected=3 → 2 fark → kabul
    lines = ["// line\n"] * 4 + ["await page.locator('.x').click();\n"]
    _mkfile(tmp_path, "tests/x.spec.ts", "".join(lines))
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/x.spec.ts",
        old_locator=".x",
        new_locator=".y",
        expected_line=3,
    )
    assert res.success is True
    assert res.line_number == 5


def test_snippet_contains_surrounding_lines(tmp_path: Path) -> None:
    lines = [
        "// 1\n",
        "// 2\n",
        "await page.locator('.x').click();\n",
        "// 4\n",
        "// 5\n",
    ]
    _mkfile(tmp_path, "tests/x.spec.ts", "".join(lines))
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/x.spec.ts",
        old_locator=".x",
        new_locator=".y",
    )
    assert res.success is True
    assert "// 1" in res.before_snippet
    assert "// 2" in res.before_snippet
    assert ".x" in res.before_snippet
    assert ".y" in res.after_snippet


def test_noop_replace_refused(tmp_path: Path) -> None:
    _mkfile(tmp_path, "tests/x.spec.ts", "'.same'\n")
    res = apply_locator_swap(
        repo_root=tmp_path,
        file_relative="tests/x.spec.ts",
        old_locator=".same",
        new_locator=".same",
    )
    assert res.success is False
    assert res.reason == "no_change_after_replace"
