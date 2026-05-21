"""Kırık locator'ı test dosyasında güvenli replace eder.

Neden ayrı modül:
    * Tek kelimelik str.replace naive ve tehlikeli — aynı string farklı
      bağlamlarda geçebilir (comment, farklı test, vb.)
    * Bu modül sadece **benzersiz** eşleşmede replace eder. Birden fazla
      eşleşme → patch reddedilir (orchestrator skip eder, PR açılmaz).
    * ``line_number`` verilirse kontrol: o satırda replace yapılabiliyor mu?

Güvenlik:
    * Path, repo kökü altında olmalı (traversal önleme)
    * Hedef dosya gerçekten var olmalı + text olmalı
    * Replace sonrası içerik ``old`` string'i artık içermemeli (geri dönüş
      kontrolü)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class PatchResult:
    success: bool
    reason: str
    before_snippet: str = ""
    after_snippet: str = ""
    occurrences_before: int = 0
    line_number: Optional[int] = None


def _safe_path(repo_root: Path, relative: str) -> Path:
    """Relative path'i repo köküne göre resolve; kök dışına çıkıyorsa raise."""
    rel = Path(relative)
    if rel.is_absolute():
        raise ValueError(f"Mutlak yol kabul edilmiyor: {relative}")
    candidate = (repo_root / rel).resolve()
    root_resolved = repo_root.resolve()
    # Python 3.9+ uyumu: is_relative_to (3.9+)
    try:
        candidate.relative_to(root_resolved)
    except ValueError:
        raise ValueError(
            f"Hedef repo kökü dışında: {candidate} ∉ {root_resolved}"
        )
    return candidate


def _count_occurrences(text: str, needle: str) -> int:
    if not needle:
        return 0
    return text.count(needle)


def apply_locator_swap(
    *,
    repo_root: Path,
    file_relative: str,
    old_locator: str,
    new_locator: str,
    expected_line: Optional[int] = None,
) -> PatchResult:
    """Dosyada ``old_locator`` geçtiği tek yerde ``new_locator`` ile değiştir.

    Args:
        repo_root: Repo kökü mutlak path.
        file_relative: ``tests/login.spec.ts`` gibi repo-relative path.
        old_locator: Kırık selector (exact string).
        new_locator: Yeni selector.
        expected_line: Opsiyonel — replace yapılan satır bu değilse reddet.

    Return ``PatchResult``. ``success=True`` ise dosya disk'e yazılmıştır.
    """
    try:
        target = _safe_path(repo_root, file_relative)
    except ValueError as exc:
        return PatchResult(success=False, reason=f"path_unsafe: {exc}")

    if not target.exists() or not target.is_file():
        return PatchResult(success=False, reason="file_not_found")

    if old_locator == new_locator:
        # Erken noop reddi — "replace yaptım ama hâlâ içeriyor" gibi karmaşık
        # hata mesajı yerine net "no_change" dön
        return PatchResult(success=False, reason="no_change_after_replace")

    try:
        original = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return PatchResult(success=False, reason="binary_file_unsupported")
    except OSError as exc:
        return PatchResult(success=False, reason=f"io_error: {exc}")

    occurrences = _count_occurrences(original, old_locator)
    if occurrences == 0:
        return PatchResult(
            success=False,
            reason="locator_not_in_file",
            occurrences_before=0,
        )
    if occurrences > 1:
        return PatchResult(
            success=False,
            reason=f"ambiguous_locator_{occurrences}_matches",
            occurrences_before=occurrences,
        )

    # Satır doğrulama (opsiyonel)
    line_found: Optional[int] = None
    for i, line in enumerate(original.splitlines(), start=1):
        if old_locator in line:
            line_found = i
            break

    if expected_line is not None and line_found is not None:
        if expected_line != line_found:
            # Test çıktısından gelen satır numarası stale olabilir — tolerans
            # ±3 satır (import bloğu büyümesi vs.). Dışındaysa reddet.
            if abs(expected_line - line_found) > 3:
                return PatchResult(
                    success=False,
                    reason=f"line_mismatch_expected_{expected_line}_found_{line_found}",
                    occurrences_before=occurrences,
                    line_number=line_found,
                )

    patched = original.replace(old_locator, new_locator, 1)
    if old_locator in patched:
        return PatchResult(
            success=False,
            reason="post_patch_still_contains_old",
            occurrences_before=occurrences,
            line_number=line_found,
        )
    if patched == original:
        return PatchResult(
            success=False,
            reason="no_change_after_replace",
            occurrences_before=occurrences,
            line_number=line_found,
        )

    try:
        target.write_text(patched, encoding="utf-8")
    except OSError as exc:
        return PatchResult(success=False, reason=f"write_failed: {exc}")

    before_snippet, after_snippet = _snippets(original, patched, line_found)
    return PatchResult(
        success=True,
        reason="ok",
        before_snippet=before_snippet,
        after_snippet=after_snippet,
        occurrences_before=occurrences,
        line_number=line_found,
    )


def _snippets(before: str, after: str, line: Optional[int]) -> Tuple[str, str]:
    """PR açıklamasına koymak için ±3 satırlık diff snippet'i."""
    if line is None:
        return "", ""
    before_lines = before.splitlines()
    after_lines = after.splitlines()
    lo = max(0, line - 3)
    hi_b = min(len(before_lines), line + 3)
    hi_a = min(len(after_lines), line + 3)
    return (
        "\n".join(before_lines[lo:hi_b]),
        "\n".join(after_lines[lo:hi_a]),
    )
