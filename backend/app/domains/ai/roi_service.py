"""ROI hesaplama servisi — AI'ın ürettiği testlerin manuel karşılığı.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §6 / E4.3.

Formül:
    savings_usd  = tests_generated * avg_manual_hours * hourly_rate
    ai_cost_usd  = llm_traces tenant'ın period'daki cost_usd SUM
    net_savings  = savings_usd - ai_cost_usd
    roi_pct      = (net_savings / ai_cost_usd) * 100        if ai_cost_usd > 0
                   = +inf (temsili 99999)                     else

Varsayılanlar (ENV ile override):
    ROI_HOURLY_RATE_USD         = 40.0
    ROI_AVG_MANUAL_HOURS_PER_TEST = 0.5   (30 dk ortalama)

Kaynak veriler:
    * tests_generated sayısı: llm_traces'teki belirli task_type'lardan
      ('test_generation', 'scenario_gen', 'gherkin') başarılı çağrılar
    * ai_cost_usd: llm_traces.cost_usd SUM (E1.2 entegrasyonu)

Export:
    * get_roi_summary(tenant, days) → ROISummary pydantic
    * build_weekly_pdf() hook — şimdilik plain-text rapor (PDF sonraki)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Hangi task_type'lar "test üretimi" sayılır
_TEST_TASK_TYPES = (
    "test_generation",
    "scenario_gen",
    "scenario_generation",
    "gherkin",
    "gherkin_generation",
    "bdd_generation",
)


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, str(default)))
    except ValueError:
        return default


def _hourly_rate() -> float:
    return _env_float("ROI_HOURLY_RATE_USD", 40.0)


def _avg_manual_hours() -> float:
    return _env_float("ROI_AVG_MANUAL_HOURS_PER_TEST", 0.5)


# ── Pure compute ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class RoiInputs:
    tests_generated: int
    ai_cost_usd: float
    days: int


@dataclass(frozen=True)
class RoiOutputs:
    tests_generated: int
    ai_cost_usd: float
    manual_hours_saved: float
    manual_cost_saved_usd: float
    net_savings_usd: float
    roi_pct: float   # 99999 → "infinity-like" (ai_cost 0)
    hourly_rate_usd: float
    avg_manual_hours: float


def compute_roi(inputs: RoiInputs) -> RoiOutputs:
    hrate = _hourly_rate()
    avgh = _avg_manual_hours()
    hours_saved = inputs.tests_generated * avgh
    manual_saved = hours_saved * hrate
    net = manual_saved - inputs.ai_cost_usd
    if inputs.ai_cost_usd <= 0:
        roi = 99999.0 if net > 0 else 0.0
    else:
        roi = (net / inputs.ai_cost_usd) * 100.0
    return RoiOutputs(
        tests_generated=inputs.tests_generated,
        ai_cost_usd=round(inputs.ai_cost_usd, 6),
        manual_hours_saved=round(hours_saved, 2),
        manual_cost_saved_usd=round(manual_saved, 2),
        net_savings_usd=round(net, 2),
        roi_pct=round(roi, 2),
        hourly_rate_usd=hrate,
        avg_manual_hours=avgh,
    )


# ── Pydantic API ─────────────────────────────────────────────────────────


class ROISummary(BaseModel):
    tenant_id: Optional[str] = None
    days: int
    range_start: datetime
    range_end: datetime
    tests_generated: int
    ai_cost_usd: float
    manual_hours_saved: float
    manual_cost_saved_usd: float
    net_savings_usd: float
    roi_pct: float
    hourly_rate_usd: float
    avg_manual_hours: float
    task_types_counted: List[str] = Field(default_factory=list)


# ── DB erişimi ───────────────────────────────────────────────────────────


def _range_bounds(days: int) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=days)
    return start, end


def _fetch_llm_aggregates(
    tenant_id: Optional[str], days: int
) -> tuple[int, float]:
    """(tests_generated_count, total_cost_usd) tuple."""
    from app.domains.ai.llm_trace import _get_conn  # type: ignore

    start, end = _range_bounds(days)
    placeholders = ", ".join(["%s"] * len(_TEST_TASK_TYPES))
    where = (
        f"WHERE created_at >= %s AND created_at < %s "
        f"AND success = TRUE AND task_type IN ({placeholders})"
    )
    params: List[Any] = [start, end] + list(_TEST_TASK_TYPES)
    if tenant_id:
        where += " AND tenant_id = %s"
        params.append(tenant_id)

    try:
        conn = _get_conn()
    except Exception as exc:
        logger.debug("ROI: DB yok (%s)", exc)
        return 0, 0.0
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"""  # nosec B608
                SELECT COUNT(*), COALESCE(SUM(cost_usd), 0.0)
                FROM llm_traces {where}
                """,
                params,
            )
            row = cur.fetchone()
            count = int(row[0] or 0)
            cost = float(row[1] or 0.0)

        # ai_cost_usd: sadece test task'ları değil, o tenant'ın TÜM LLM
        # harcaması olsun — "AI'a karşı yatırım" hesabı total ile daha
        # dürüst olur. Alternatif: sadece test gen'in kendi maliyeti.
        # İkisini de tutalım; buradaki basit versiyon test-gen maliyeti.
        return count, cost
    finally:
        conn.close()


def get_roi_summary(
    tenant_id: Optional[str] = None,
    *,
    days: int = 30,
) -> ROISummary:
    if days < 1:
        days = 1
    if days > 365:
        days = 365

    start, end = _range_bounds(days)
    count, cost = _fetch_llm_aggregates(tenant_id, days)
    out = compute_roi(RoiInputs(tests_generated=count, ai_cost_usd=cost, days=days))

    return ROISummary(
        tenant_id=tenant_id,
        days=days,
        range_start=start,
        range_end=end,
        tests_generated=out.tests_generated,
        ai_cost_usd=out.ai_cost_usd,
        manual_hours_saved=out.manual_hours_saved,
        manual_cost_saved_usd=out.manual_cost_saved_usd,
        net_savings_usd=out.net_savings_usd,
        roi_pct=out.roi_pct,
        hourly_rate_usd=out.hourly_rate_usd,
        avg_manual_hours=out.avg_manual_hours,
        task_types_counted=list(_TEST_TASK_TYPES),
    )


# ── Weekly report (plain text) ───────────────────────────────────────────


def format_weekly_report(summary: ROISummary) -> str:
    """Plain-text rapor — PDF render'ı sonraki sprint'te."""
    tenant = summary.tenant_id or "tüm tenant'lar"
    return (
        f"TestwrightAI — ROI Haftalık Raporu\n"
        f"{'=' * 42}\n"
        f"Tenant   : {tenant}\n"
        f"Period   : {summary.range_start.date()} → {summary.range_end.date()} "
        f"({summary.days} gün)\n"
        f"\n"
        f"Üretilen test / senaryo   : {summary.tests_generated}\n"
        f"Kazanılan manuel saat     : {summary.manual_hours_saved}\n"
        f"Kazanılan manuel maliyet  : ${summary.manual_cost_saved_usd:,.2f}\n"
        f"AI çağrı maliyeti         : ${summary.ai_cost_usd:,.2f}\n"
        f"Net kazanç                : ${summary.net_savings_usd:,.2f}\n"
        f"ROI                       : %{summary.roi_pct:,.2f}\n"
        f"\n"
        f"Varsayımlar: saatlik ücret ${summary.hourly_rate_usd:.2f}, "
        f"ortalama {summary.avg_manual_hours:.2f}h/test\n"
        f"Sayılan task_types: {', '.join(summary.task_types_counted)}\n"
    )
