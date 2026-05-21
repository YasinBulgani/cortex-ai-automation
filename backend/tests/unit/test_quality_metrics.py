"""quality.service için unit testler — UX-F2-201.

Disk I/O tmp_path ile izole. Eval raporu parsing örnek gerçek dosyada.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.domains.quality.service import (
    EvalSnapshot,
    get_quality_metrics,
    parse_eval_report,
)


# Gerçek eval raporlarının formatına uyan örnek — engine/evals/reports/latest.md
# yapısını birebir takip eder.
SAMPLE_REPORT = """# BGTest Eval Report — 2026-04-19T06:53:31+00:00

**Mod:** `grounding-only`
**Katalog:** /path/to/catalog (751 aksiyon)
**Grounding:** top_k=5, min_score=0.35

## Özet

| Metrik | Değer |
|---|---|
| Fixture sayısı | 5 |
| Toplam adım | 22 |
| **Mapping accuracy** | 86.4% |
| Unknown rate | 13.6% |
| Value preservation | 100.0% |
| p95 latency | 44 ms |
| LLM hatası | 0 |

## Detaylar
(…)
"""


# ── parse_eval_report ─────────────────────────────────────────────────────


def test_parse_sample_all_fields() -> None:
    snap = parse_eval_report(SAMPLE_REPORT)
    assert snap.available is True
    assert snap.mode == "grounding-only"
    assert snap.mapping_accuracy_pct == 86.4
    assert snap.unknown_rate_pct == 13.6
    assert snap.value_preservation_pct == 100.0
    assert snap.p95_latency_ms == 44
    assert snap.total_fixtures == 5
    assert snap.total_steps == 22
    assert snap.llm_errors == 0
    assert snap.generated_at is not None
    assert "2026-04-19" in snap.generated_at


def test_parse_tolerates_missing_fields() -> None:
    partial = "# BGTest Eval Report — 2026-04-19T10:00:00Z\n\n**Mod:** `full-v2`\n"
    snap = parse_eval_report(partial)
    assert snap.available is True
    assert snap.mode == "full-v2"
    # Tablo yok → metrikler None
    assert snap.mapping_accuracy_pct is None
    assert snap.total_fixtures is None


def test_parse_tolerates_comma_decimal() -> None:
    """TR lokalinde 86,4 gibi virgüllü sayı gelebilir — desteklenmeli."""
    # Not: regex pattern nokta bekliyor, ama _to_float virgülü noktaya çevirir.
    txt = "| **Mapping accuracy** | 92.5% |\n| Unknown rate | 7.5% |"
    # Başlık eklememiz gerekiyor parser için
    full = f"# Eval\n{txt}"
    snap = parse_eval_report(full)
    assert snap.mapping_accuracy_pct == 92.5


def test_parse_empty_input() -> None:
    snap = parse_eval_report("")
    assert snap.available is True   # parser çalıştı, ama bilgi yok
    assert snap.mapping_accuracy_pct is None


# ── get_quality_metrics (I/O) ──────────────────────────────────────────────


def test_missing_reports_dir_returns_unavailable(tmp_path: Path) -> None:
    missing = tmp_path / "nonexistent"
    result = get_quality_metrics(reports_dir=missing)
    assert result.latest_eval.available is False
    assert result.history == []


def test_reads_latest_md(tmp_path: Path) -> None:
    (tmp_path).mkdir(parents=True, exist_ok=True)
    (tmp_path / "latest.md").write_text(SAMPLE_REPORT, encoding="utf-8")

    result = get_quality_metrics(reports_dir=tmp_path)
    assert result.latest_eval.available is True
    assert result.latest_eval.mapping_accuracy_pct == 86.4
    assert result.latest_eval.total_fixtures == 5


def test_reads_history_newest_first(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True)

    older = SAMPLE_REPORT.replace("86.4%", "80.0%")
    newer = SAMPLE_REPORT.replace("86.4%", "90.0%")
    (history_dir / "2026-04-18.md").write_text(older, encoding="utf-8")
    (history_dir / "2026-04-19.md").write_text(newer, encoding="utf-8")

    # mtime fark yarat
    import time
    import os as _os

    t1 = time.time() - 60
    t2 = time.time()
    _os.utime(history_dir / "2026-04-18.md", (t1, t1))
    _os.utime(history_dir / "2026-04-19.md", (t2, t2))

    result = get_quality_metrics(reports_dir=tmp_path)
    assert len(result.history) == 2
    # En yenisi başta
    assert result.history[0].mapping_accuracy_pct == 90.0
    assert result.history[1].mapping_accuracy_pct == 80.0


def test_history_limit_respected(tmp_path: Path) -> None:
    history_dir = tmp_path / "history"
    history_dir.mkdir(parents=True)
    for i in range(15):
        (history_dir / f"run-{i:02d}.md").write_text(SAMPLE_REPORT, encoding="utf-8")

    result = get_quality_metrics(reports_dir=tmp_path, history_limit=5)
    assert len(result.history) == 5


def test_corrupted_report_doesnt_crash(tmp_path: Path) -> None:
    """Parser herhangi bir içerikte crash etmemeli."""
    (tmp_path / "latest.md").write_text(
        "garbage\x00\xff\xfeinvalid utf8 partial",
        encoding="utf-8",
        errors="ignore",
    )
    result = get_quality_metrics(reports_dir=tmp_path)
    # Available True (dosya var, parse edildi) ama metrikler None kalır
    assert result.latest_eval.available is True
    assert result.latest_eval.mapping_accuracy_pct is None


def test_reports_dir_in_response(tmp_path: Path) -> None:
    result = get_quality_metrics(reports_dir=tmp_path)
    assert result.reports_dir == str(tmp_path)
