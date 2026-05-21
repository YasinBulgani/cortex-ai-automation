"""Shift-left PR bot — değişen PR'da TIA + coverage + eval özetini yorum olarak bırakır.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §6 / E4.1.

Giriş:
    * Değişen dosya listesi (diff)
    * Coverage raporu path'leri (opsiyonel)
    * Son eval summary (opsiyonel; build_pr_summary dışarıdan alır)

Çıkış:
    * Markdown yorumu (GitHub PR comment için hazır)
    * JSON payload (CI step çıktısı)

Tasarım:
    * Pure Python + cicd/tia + a11y + ROI + evals → zaten var olan servislere
      bağlanır. Yeni kod sadece "orchestrator + markdown render".
    * LLM önerisi opsiyonel — LlmCallable enjekte edilebilir; yoksa bot
      sadece istatistikleri özetler. Bu sayede LLM down olsa bile PR bot
      çalışır.
    * GitHub post işi bu modülün dışında (existing GitHubClient veya
      actions/github-script ile).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, List, Optional, Sequence

from app.domains.cicd.tia import ImpactResult, map_changes_to_tests

logger = logging.getLogger(__name__)


# ── Girdi/çıktı tipleri ──────────────────────────────────────────────────


@dataclass
class EvalSnapshot:
    """Eval harness özetinden ilgili kısım. E1.1 CLI çıktısının subseti."""

    overall_passed: bool
    failed_suites: int
    total_suites: int
    worst_mean_score: Optional[float] = None  # en kötü mean_* metriği
    notes: str = ""


@dataclass
class PRSuggestion:
    """LLM tarafından önerilen yeni test / iyileştirme."""

    title: str
    rationale: str
    confidence: float = 0.5


@dataclass
class PRSummary:
    impact: ImpactResult
    eval_snapshot: Optional[EvalSnapshot]
    suggestions: List[PRSuggestion] = field(default_factory=list)
    changed_files_count: int = 0

    def has_blocking_issues(self) -> bool:
        if self.eval_snapshot and not self.eval_snapshot.overall_passed:
            return True
        return False


# ── LLM enjeksiyon noktası ──────────────────────────────────────────────


LlmSuggesterFn = Callable[[List[str], List[str]], List[PRSuggestion]]
"""(changed_files, impacted_tests) -> 0+ test önerisi."""


# ── Builder ─────────────────────────────────────────────────────────────


def build_pr_summary(
    *,
    repo_root: Path,
    changed_files: Sequence[str],
    coverage_paths: Optional[Sequence[Path]] = None,
    test_roots: Optional[Sequence[Path]] = None,
    total_src_count: Optional[int] = None,
    eval_snapshot: Optional[EvalSnapshot] = None,
    llm_suggester: Optional[LlmSuggesterFn] = None,
) -> PRSummary:
    impact = map_changes_to_tests(
        repo_root=repo_root,
        changed_files=list(changed_files),
        coverage_paths=coverage_paths,
        test_roots=test_roots,
        total_src_count=total_src_count,
    )

    suggestions: List[PRSuggestion] = []
    if llm_suggester is not None:
        try:
            suggestions = list(
                llm_suggester(list(changed_files), list(impact.tests))
            )[:5]
        except Exception as exc:
            logger.warning("PR bot LLM suggester hata: %s", exc)

    return PRSummary(
        impact=impact,
        eval_snapshot=eval_snapshot,
        suggestions=suggestions,
        changed_files_count=len(list(changed_files)),
    )


# ── Markdown render ─────────────────────────────────────────────────────


def render_markdown(summary: PRSummary) -> str:
    imp = summary.impact
    icon = "❌" if summary.has_blocking_issues() else (
        "⚠️" if (summary.suggestions or imp.run_all) else "✅"
    )

    lines: List[str] = [
        f"## {icon} TestwrightAI — Shift-left PR Bot",
        "",
        f"**Değişen dosya**: {summary.changed_files_count}",
    ]

    # TIA
    if imp.run_all:
        lines.append(
            f"**Test kapsamı**: tüm suite'i koşmak öneriliyor — `{imp.reason}`"
        )
    elif imp.tests:
        lines.append(f"**Etkilenen test**: {len(imp.tests)}")
        sources = imp.impact_sources or {}
        if sources:
            parts = [f"`{k}={v}`" for k, v in sources.items() if v]
            if parts:
                lines.append(f"<sub>Sinyaller: {', '.join(parts)}</sub>")
    else:
        lines.append("**Etkilenen test**: yok (değişiklik yalnız docs/lint olabilir)")

    # Eval
    if summary.eval_snapshot:
        ev = summary.eval_snapshot
        status = "✅ geçti" if ev.overall_passed else f"❌ {ev.failed_suites} fail"
        lines.append(
            f"**Eval**: {status} ({ev.failed_suites}/{ev.total_suites} suite)"
        )
        if ev.worst_mean_score is not None:
            lines.append(f"<sub>En kötü ortalama: {ev.worst_mean_score:.3f}</sub>")
        if ev.notes:
            lines.append(f"<sub>{ev.notes}</sub>")

    # Impacted tests önizleme
    if imp.tests and not imp.run_all:
        shown = imp.tests[:10]
        rest = max(0, len(imp.tests) - len(shown))
        lines.append("\n<details><summary>Etkilenen testler</summary>\n")
        lines.append("")
        for t in shown:
            lines.append(f"- `{t}`")
        if rest:
            lines.append(f"- _(+{rest} daha)_")
        lines.append("\n</details>")

    # LLM önerileri
    if summary.suggestions:
        lines.append("\n### 🤖 Öneriler")
        for s in summary.suggestions:
            conf_bar = f"{s.confidence:.2f}"
            lines.append(f"- **{s.title}** _(confidence={conf_bar})_")
            if s.rationale:
                lines.append(f"  - {s.rationale}")

    # Koşum önerisi
    if imp.run_all:
        lines.append(
            "\n> Bu PR geniş kapsamlı görünüyor — `make test-full` önerilir."
        )
    elif imp.tests:
        lines.append(
            f"\n> CI'da yalnız {len(imp.tests)} test koşularak zaman kazanabilirsiniz: `python -m scripts.tia --json`"
        )

    return "\n".join(lines)
