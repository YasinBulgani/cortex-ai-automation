"""Eval raporlarını parse edip dashboard için özet metrik üreten servis.

Kaynaklar (sırayla denenir, bulunan ilki kullanılır):
    1. ``engine/evals/reports/latest.md`` — en güncel koşum
    2. ``engine/evals/reports/history/`` — zaman serisi için son N koşum

Hiçbiri yoksa ``EvalSnapshot(available=False)`` döner — frontend "veri yok"
gösterir, sistem kırılmaz.

Parse stratejisi:
    latest.md deterministik bir formatta (YAML frontmatter'sız markdown
    tablo). Biz kırılgan regex yerine metrik adına göre arama yaparız.
    Format değişirse graceful bozulur, hiçbir zaman exception atmaz.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_DEFAULT_REPORTS_DIR = _PROJECT_ROOT / "engine" / "evals" / "reports"


@dataclass
class EvalSnapshot:
    """Tek bir eval koşumunun özet metrikleri. Eksik alanlar None kalır."""

    available: bool = False
    mode: Optional[str] = None                # "grounding-only" | "full-v2" | "baseline"
    mapping_accuracy_pct: Optional[float] = None   # 0..100
    value_preservation_pct: Optional[float] = None
    unknown_rate_pct: Optional[float] = None
    gherkin_valid_pct: Optional[float] = None
    p95_latency_ms: Optional[int] = None
    total_fixtures: Optional[int] = None
    total_steps: Optional[int] = None
    llm_errors: Optional[int] = None
    generated_at: Optional[str] = None         # ISO timestamp raw string


class EvalSnapshotModel(BaseModel):
    """Pydantic API view of EvalSnapshot."""

    model_config = ConfigDict(extra="ignore")

    available: bool = False
    mode: Optional[str] = None
    mapping_accuracy_pct: Optional[float] = None
    value_preservation_pct: Optional[float] = None
    unknown_rate_pct: Optional[float] = None
    gherkin_valid_pct: Optional[float] = None
    p95_latency_ms: Optional[int] = None
    total_fixtures: Optional[int] = None
    total_steps: Optional[int] = None
    llm_errors: Optional[int] = None
    generated_at: Optional[str] = None


class QualityMetrics(BaseModel):
    """Dashboard widget için toplu veri."""

    model_config = ConfigDict(extra="ignore")

    latest_eval: EvalSnapshotModel
    history: List[EvalSnapshotModel] = Field(
        default_factory=list,
        description="Son N koşumun özeti — zaman serisi grafiği için",
    )
    reports_dir: str = Field(..., description="Parse edilen dosyaların kökü")


def _first_match(text: str, pattern: str) -> Optional[str]:
    """Regex match — ilk grup'u veya None döner."""
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else None


def _to_float(s: Optional[str]) -> Optional[float]:
    if s is None:
        return None
    s = s.replace(",", ".").replace("%", "").strip()
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _to_int(s: Optional[str]) -> Optional[int]:
    if s is None:
        return None
    try:
        return int(re.sub(r"[^\d-]", "", s))
    except (ValueError, TypeError):
        return None


def parse_eval_report(text: str) -> EvalSnapshot:
    """Bir eval markdown raporundan metrikleri çıkar.

    Format (örnek latest.md):
        # BGTest Eval Report — 2026-04-19T06:53:31+00:00

        **Mod:** `grounding-only`
        ...

        | Metrik | Değer |
        |---|---|
        | Fixture sayısı | 5 |
        | Toplam adım | 22 |
        | **Mapping accuracy** | 86.4% |
        | Unknown rate | 13.6% |
        | Value preservation | 100.0% |
        | p95 latency | 44 ms |
        | LLM hatası | 0 |

    Eksik alanlar None bırakılır — graceful degradation.
    """
    snap = EvalSnapshot(available=True)

    # Timestamp (başlıktan)
    snap.generated_at = _first_match(text, r"Eval Report\s*[—-]?\s*([\dT:+\-.]+)")

    # Mod
    snap.mode = _first_match(text, r"\*\*Mod:\*\*\s*`?([^`\n]+?)`?\s*$")

    # Tablo hücreleri — `| <anahtar> | <değer> |` örüntüsü
    patterns = {
        "mapping_accuracy_pct": r"\|\s*\*{0,2}Mapping accuracy\*{0,2}\s*\|\s*([\d.,]+)\s*%",
        "unknown_rate_pct":    r"\|\s*Unknown rate\s*\|\s*([\d.,]+)\s*%",
        "value_preservation_pct": r"\|\s*Value preservation\s*\|\s*([\d.,]+)\s*%",
        "gherkin_valid_pct": r"\|\s*Gherkin valid(?:ity)?\s*\|\s*([\d.,]+)\s*%",
        "p95_latency_ms":    r"\|\s*p95 latency\s*\|\s*([\d.,]+)\s*ms",
        "total_fixtures":    r"\|\s*Fixture say[ıi]s[ıi]\s*\|\s*([\d]+)",
        "total_steps":       r"\|\s*Toplam ad[ıi]m\s*\|\s*([\d]+)",
        "llm_errors":        r"\|\s*LLM hatas[ıi]\s*\|\s*([\d]+)",
    }
    for field_name, pattern in patterns.items():
        raw = _first_match(text, pattern)
        if field_name in (
            "mapping_accuracy_pct",
            "unknown_rate_pct",
            "value_preservation_pct",
            "gherkin_valid_pct",
        ):
            setattr(snap, field_name, _to_float(raw))
        else:
            setattr(snap, field_name, _to_int(raw))

    return snap


def _read_latest_report(reports_dir: Path) -> EvalSnapshot:
    latest = reports_dir / "latest.md"
    if not latest.is_file():
        return EvalSnapshot(available=False)
    try:
        text = latest.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("Quality: latest.md okunamadı: %s", exc)
        return EvalSnapshot(available=False)
    return parse_eval_report(text)


def _read_history(reports_dir: Path, limit: int = 10) -> List[EvalSnapshot]:
    """history/ klasöründen en yeni N rapor."""
    history_dir = reports_dir / "history"
    if not history_dir.is_dir():
        return []
    files = sorted(
        (p for p in history_dir.glob("*.md") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )[:limit]
    out: List[EvalSnapshot] = []
    for f in files:
        try:
            out.append(parse_eval_report(f.read_text(encoding="utf-8")))
        except OSError:
            continue
    return out


def get_quality_metrics(
    reports_dir: Optional[Path] = None,
    history_limit: int = 10,
) -> QualityMetrics:
    """Dashboard için özet metrik üret.

    Args:
        reports_dir: Alternatif rapor klasörü (test için); default
            ``engine/evals/reports/``.
        history_limit: Kaç geçmiş rapor dahil edilsin.
    """
    env_dir = os.environ.get("ENGINE_EVAL_REPORTS_DIR")
    root = reports_dir or (Path(env_dir) if env_dir else _DEFAULT_REPORTS_DIR)

    latest = _read_latest_report(root)
    history = _read_history(root, limit=history_limit)

    return QualityMetrics(
        latest_eval=EvalSnapshotModel(**asdict(latest)),
        history=[EvalSnapshotModel(**asdict(s)) for s in history],
        reports_dir=str(root),
    )
