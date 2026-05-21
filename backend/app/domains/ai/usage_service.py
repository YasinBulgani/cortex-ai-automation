"""AI kullanım servisi — trace kaydı, maliyet hesabı, Prometheus emit, range agg.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §3 / E1.2.

Genel akış:
    caller → record_usage(tenant_id, model, tokens, ...) → llm_traces satırı
             + llm_tokens_total Prometheus sayacı
             + llm_cost_usd_total Prometheus sayacı
             + (ops.) audit hook

Mevcut ``llm_trace.log_llm_call`` ile uyumlu: bu fonksiyon onun üstüne inşa
edilmiş bir ince sarıcı. Legacy çağrılar log_llm_call'u kullanmaya devam
edebilir; yeni kod record_usage'a gider ve tenant_id + cost otomatik
hesaplanır.
"""
from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from app.infra.telemetry import set_span_attr, trace_span

from .pricing import compute_cost_usd

logger = logging.getLogger(__name__)


# ── Prometheus metrikleri ──────────────────────────────────────────────
# TEK KAYNAK: app.domains.ai.metrics (Dalga 0 · L1 konsolidasyonu).
# Burada sadece record_usage -> metrics.record_request mapping'i.
from app.domains.ai import metrics as _metrics


def _emit_metrics(
    *,
    tenant_id: str,
    model: str,
    provider: Optional[str],
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    task_type: Optional[str] = None,
    tier: Optional[str] = None,
    status: str = "ok",
    latency_ms: Optional[int] = None,
) -> None:
    _metrics.record_request(
        tenant=tenant_id,
        task_type=task_type,
        model=model,
        provider=provider,
        tier=tier,
        status=status,
        latency_ms=latency_ms,
        input_tokens=input_tokens or 0,
        output_tokens=output_tokens or 0,
        cost_usd=cost_usd,
    )


# ── Record (yazma) ─────────────────────────────────────────────────────────


def record_usage(
    *,
    tenant_id: str,
    agent_name: str,
    model: str,
    latency_ms: int,
    input_tokens: int = 0,
    output_tokens: int = 0,
    cached_input_tokens: int = 0,
    provider: Optional[str] = None,
    task_type: Optional[str] = None,
    prompt_version: Optional[str] = None,
    system_prompt: str = "",
    user_prompt: str = "",
    response: str = "",
    success: bool = True,
    error_message: str = "",
    run_id: Optional[str] = None,
    phase: Optional[str] = None,
    cost_usd_override: Optional[float] = None,
) -> float:
    """LLM çağrısını kaydet, Prometheus emit et, hesaplanan USD'yi döndür.

    Bu fonksiyon llm_trace.log_llm_call'u çağırır ve aşağıdaki EK alanları
    DB'ye yazar: ``tenant_id``, ``cost_usd``, ``provider``, ``task_type``,
    ``prompt_version``.

    ``cost_usd_override`` verilmediyse pricing tablosundan otomatik hesaplar.
    Bilinmeyen model → 0.0 (pricing.compute_cost_usd davranışı).
    """
    with trace_span(
        "ai.usage.record",
        attrs={
            "tenant_id": tenant_id,
            "model": model,
            "provider": provider or "unknown",
            "task_type": task_type or "unknown",
            "input_tokens": int(input_tokens or 0),
            "output_tokens": int(output_tokens or 0),
        },
    ):
        total_tokens = (input_tokens or 0) + (output_tokens or 0)
        if cost_usd_override is not None:
            cost_usd = max(0.0, float(cost_usd_override))
        else:
            cost_usd = compute_cost_usd(
                model,
                input_tokens=input_tokens or 0,
                output_tokens=output_tokens or 0,
                cached_input_tokens=cached_input_tokens or 0,
            )
        set_span_attr("cost_usd", cost_usd)
        set_span_attr("total_tokens", total_tokens)

        # Prometheus metrics — DB hatası olsa bile in-memory sayaç tutar.
        # Tier/task_type/status metrics modülü tarafına geçti → label set
        # zenginleşti (registry'den tier inference).
        try:
            from app.domains.ai.model_registry import get_model_info
            tier_label = get_model_info(model).tier
        except Exception:
            tier_label = "mid"
        _emit_metrics(
            tenant_id=tenant_id,
            model=model,
            provider=provider,
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
            cost_usd=cost_usd,
            task_type=task_type,
            tier=tier_label,
            status="ok" if success else "error",
            latency_ms=latency_ms,
        )

        # DB trace — fire-and-forget (hata yutulur, pipeline kırılmaz)
        try:
            _persist_trace(
                tenant_id=tenant_id,
                agent_name=agent_name,
                model=model,
                provider=provider,
                task_type=task_type,
                prompt_version=prompt_version,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                response=response,
                latency_ms=latency_ms,
                success=success,
                error_message=error_message,
                run_id=run_id,
                phase=phase,
                prompt_tokens=input_tokens or None,
                completion_tokens=output_tokens or None,
                total_tokens=total_tokens or None,
                cost_usd=cost_usd,
            )
        except Exception as exc:
            logger.debug("usage_service.record_usage trace hata (sessiz): %s", exc)

    return cost_usd


def _persist_trace(
    *,
    tenant_id: str,
    agent_name: str,
    model: str,
    provider: Optional[str],
    task_type: Optional[str],
    prompt_version: Optional[str],
    system_prompt: str,
    user_prompt: str,
    response: str,
    latency_ms: int,
    success: bool,
    error_message: str,
    run_id: Optional[str],
    phase: Optional[str],
    prompt_tokens: Optional[int],
    completion_tokens: Optional[int],
    total_tokens: Optional[int],
    cost_usd: float,
) -> None:
    """llm_traces'e satır yazar (tenant_id + cost_usd + provider + task_type dahil).

    llm_trace.log_llm_call'un SQL'ini genişletiyoruz. Kolon yoksa insert
    fail eder → üst seviyede yutulur (schema güncel değilse de pipeline kırılmasın).
    """
    from .llm_trace import _get_conn  # type: ignore

    SYSTEM_PREV = 500
    USER_PREV = 500
    RESP_PREV = 1000

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO llm_traces (
                    run_id, agent_name, model, phase,
                    system_prompt_preview, user_prompt_preview,
                    response_preview, full_response_length,
                    latency_ms, success, error_message,
                    prompt_tokens, completion_tokens, total_tokens,
                    tenant_id, provider, task_type, prompt_version, cost_usd
                ) VALUES (
                    %s, %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s, %s
                )
                """,
                (
                    run_id, agent_name, model, phase,
                    (system_prompt or "")[:SYSTEM_PREV],
                    (user_prompt or "")[:USER_PREV],
                    (response or "")[:RESP_PREV],
                    len(response or ""),
                    latency_ms, success,
                    error_message[:2000] if error_message else None,
                    prompt_tokens, completion_tokens, total_tokens,
                    tenant_id, provider, task_type, prompt_version, cost_usd,
                ),
            )
    finally:
        conn.close()


# ── Aggregation (okuma) ────────────────────────────────────────────────────


def _today_utc_bounds() -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def get_tenant_today_cost(tenant_id: str) -> float:
    """Bugünün (UTC) toplam USD harcaması — budget.check_budget kullanır."""
    if not tenant_id:
        return 0.0
    from .llm_trace import _get_conn  # type: ignore

    start, end = _today_utc_bounds()
    try:
        conn = _get_conn()
    except Exception as exc:
        logger.debug("usage_service.today_cost: DB yok (%s)", exc)
        return 0.0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(cost_usd), 0.0)
                FROM llm_traces
                WHERE tenant_id = %s AND created_at >= %s AND created_at < %s
                """,
                (tenant_id, start, end),
            )
            row = cur.fetchone()
            return float(row[0] or 0.0) if row else 0.0
    finally:
        conn.close()


def get_tenant_usage(
    tenant_id: str,
    *,
    days: int = 7,
    group_by: str = "day",  # "day" | "model" | "provider"
) -> Dict[str, Any]:
    """Son N günün agregasyonu.

    ``group_by='day'``  → {"series": [{"date": "YYYY-MM-DD", "tokens":..., "cost_usd":..., "calls":...}]}
    ``group_by='model'``→ {"by_model": [{"model": "...", "tokens":..., "cost_usd":..., "calls":...}]}
    ``group_by='provider'`` → benzer ama provider'a göre
    """
    if days < 1:
        days = 1
    if days > 90:
        days = 90
    if group_by not in {"day", "model", "provider"}:
        raise ValueError(f"geçersiz group_by: {group_by}")

    from .llm_trace import _get_conn  # type: ignore

    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=days - 1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    end = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)

    where = "WHERE created_at >= %s AND created_at < %s"
    params: List[Any] = [start, end]
    if tenant_id:
        where += " AND tenant_id = %s"
        params.append(tenant_id)

    result: Dict[str, Any] = {
        "tenant_id": tenant_id or None,
        "days": days,
        "range_start": start.isoformat(),
        "range_end": end.isoformat(),
    }

    try:
        conn = _get_conn()
    except Exception as exc:
        logger.debug("usage_service.get_tenant_usage DB yok (%s)", exc)
        result.update({"series": [], "by_model": [], "by_provider": []})
        return result

    try:
        with conn.cursor() as cur:
            # Toplam
            cur.execute(
                f"""
                SELECT COALESCE(SUM(prompt_tokens),0),
                       COALESCE(SUM(completion_tokens),0),
                       COALESCE(SUM(total_tokens),0),
                       COALESCE(SUM(cost_usd),0.0),
                       COUNT(*)
                FROM llm_traces {where}
                """,
                params,
            )
            row = cur.fetchone() or (0, 0, 0, 0.0, 0)
            result["totals"] = {
                "prompt_tokens": int(row[0] or 0),
                "completion_tokens": int(row[1] or 0),
                "total_tokens": int(row[2] or 0),
                "cost_usd": round(float(row[3] or 0.0), 6),
                "calls": int(row[4] or 0),
            }

            if group_by == "day":
                cur.execute(
                    f"""
                    SELECT date_trunc('day', created_at) AS day,
                           COALESCE(SUM(total_tokens),0),
                           COALESCE(SUM(cost_usd),0.0),
                           COUNT(*)
                    FROM llm_traces {where}
                    GROUP BY day
                    ORDER BY day ASC
                    """,
                    params,
                )
                result["series"] = [
                    {
                        "date": r[0].date().isoformat() if r[0] else None,
                        "tokens": int(r[1] or 0),
                        "cost_usd": round(float(r[2] or 0.0), 6),
                        "calls": int(r[3] or 0),
                    }
                    for r in cur.fetchall()
                ]
            elif group_by == "model":
                cur.execute(
                    f"""
                    SELECT model,
                           COALESCE(SUM(total_tokens),0),
                           COALESCE(SUM(cost_usd),0.0),
                           COUNT(*)
                    FROM llm_traces {where}
                    GROUP BY model
                    ORDER BY SUM(cost_usd) DESC NULLS LAST
                    """,
                    params,
                )
                result["by_model"] = [
                    {
                        "model": r[0] or "unknown",
                        "tokens": int(r[1] or 0),
                        "cost_usd": round(float(r[2] or 0.0), 6),
                        "calls": int(r[3] or 0),
                    }
                    for r in cur.fetchall()
                ]
            else:  # provider
                cur.execute(
                    f"""
                    SELECT provider,
                           COALESCE(SUM(total_tokens),0),
                           COALESCE(SUM(cost_usd),0.0),
                           COUNT(*)
                    FROM llm_traces {where}
                    GROUP BY provider
                    ORDER BY SUM(cost_usd) DESC NULLS LAST
                    """,
                    params,
                )
                result["by_provider"] = [
                    {
                        "provider": r[0] or "unknown",
                        "tokens": int(r[1] or 0),
                        "cost_usd": round(float(r[2] or 0.0), 6),
                        "calls": int(r[3] or 0),
                    }
                    for r in cur.fetchall()
                ]
    finally:
        conn.close()

    return result
