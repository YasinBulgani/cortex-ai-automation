"""
Router Learning — llm_traces + llm_judge_runs'tan otomatik routing optimizasyonu.

Problem:
    route_model()'deki karar matrisi elle yazildi. Zamanla veri birikince:
    - "gpt-4o-mini aslinda chain_builder'da %92 başarılı"
    - "claude-sonnet-4 test_generation'da %5 daha kotu"
    gibi insightlar ortaya cikar. Manuel tuning yerine **veri** karar verir.

Yaklasim: Thompson Sampling (Bayesian bandit)
    Her (task_type, model) cifti için Beta(alpha, beta) distribution:
    alpha = başarılı cagri + iyi judge skor
    beta  = başarısız cagri + kotu judge skor

    Decision score = success_rate - cost_penalty + judge_bonus
    Nightly job bu skorlari hesaplayip preferred_routing tablosuna yazar.

Kullanim:
    route_model() mevcut karar matrisi UYGULANIR, ardindan
    get_learned_preference(task_type) kontrol edilir:
    - Preference daha yuksek skorlu baska bir tier ise UYARI log'lanir
      (shadow mode — tier degistirmez, sadece onerir)
    - ai.routing.learned flag acilirsa UYGULANIR

Bu shadow mode gecis kolaylastirir — 1 hafta shadow, sonra aktif.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RoutingStats:
    task_type: str
    model: str
    total_calls: int = 0
    successful: int = 0
    judge_avg: Optional[float] = None
    judge_count: int = 0
    avg_cost_usd: float = 0.0
    avg_latency_ms: int = 0
    success_rate: float = 0.0
    composite_score: float = 0.0
    samples: int = 0  # alpha + beta for Beta distribution

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_type": self.task_type,
            "model": self.model,
            "total_calls": self.total_calls,
            "successful": self.successful,
            "success_rate": round(self.success_rate, 3),
            "judge_avg": round(self.judge_avg, 2) if self.judge_avg is not None else None,
            "judge_count": self.judge_count,
            "avg_cost_usd": round(self.avg_cost_usd, 6),
            "avg_latency_ms": self.avg_latency_ms,
            "composite_score": round(self.composite_score, 4),
        }


# ── Scoring ─────────────────────────────────────────────────────────────


# Composite score formulu:
#   success_rate * W_SUCCESS
# + (judge_avg/10) * W_JUDGE
# - cost_norm    * W_COST
# - latency_norm * W_LATENCY
_W_SUCCESS = 0.40
_W_JUDGE = 0.30
_W_COST = 0.20
_W_LATENCY = 0.10

# Normalize sabitleri — bu degerleri asan model cezalandirilir
_COST_NORMALIZER = 0.01  # $0.01 per call = 1.0
_LATENCY_NORMALIZER = 5000.0  # 5s = 1.0


def _compute_composite(s: RoutingStats) -> float:
    """Bu (task, model) için composite decision score."""
    judge_part = (s.judge_avg / 10.0) if s.judge_avg is not None else s.success_rate
    cost_part = min(1.0, s.avg_cost_usd / _COST_NORMALIZER)
    lat_part = min(1.0, s.avg_latency_ms / _LATENCY_NORMALIZER)
    return (
        s.success_rate * _W_SUCCESS
        + judge_part * _W_JUDGE
        - cost_part * _W_COST
        - lat_part * _W_LATENCY
    )


# ── Data aggregation ────────────────────────────────────────────────────


def aggregate_stats(days: int = 14, min_calls: int = 30) -> list[RoutingStats]:
    """
    llm_traces + llm_judge_runs JOIN -> (task_type, model) basina aggregate.

    Min_calls alti kombinasyonlar cikartilir (gurultulu).
    """
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception as exc:
        logger.debug("aggregate_stats DB yok: %s", exc)
        return []

    results: list[RoutingStats] = []
    try:
        with conn.cursor() as cur:
            # llm_traces tarafi
            cur.execute(
                """
                SELECT
                    COALESCE(task_type, 'unknown') AS tt,
                    model,
                    COUNT(*) AS total,
                    SUM(CASE WHEN success THEN 1 ELSE 0 END) AS ok,
                    COALESCE(AVG(cost_usd), 0) AS avg_cost,
                    COALESCE(AVG(latency_ms), 0) AS avg_lat
                FROM llm_traces
                WHERE created_at > NOW() - INTERVAL %s
                  AND task_type IS NOT NULL
                  AND model IS NOT NULL
                GROUP BY task_type, model
                HAVING COUNT(*) >= %s
                """,
                (f"{int(days)} days", min_calls),
            )
            rows = cur.fetchall() or []

            # Judge tarafi
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_judge_runs')"
            )
            has_judge = cur.fetchone()[0]

            judge_map: dict[tuple[str, str], tuple[float, int]] = {}
            if has_judge:
                cur.execute(
                    """
                    SELECT task_type, judged_model, AVG(overall), COUNT(*)
                    FROM llm_judge_runs
                    WHERE created_at > NOW() - INTERVAL %s
                    GROUP BY task_type, judged_model
                    """,
                    (f"{int(days)} days",),
                )
                for r in cur.fetchall() or []:
                    judge_map[(r[0], r[1])] = (float(r[2] or 0), int(r[3] or 0))
    except Exception as exc:
        logger.debug("aggregate_stats hatasi: %s", exc)
        return []
    finally:
        try:
            conn.close()
        except Exception:
            pass

    for r in rows:
        tt, model, total, ok, avg_cost, avg_lat = r
        success_rate = (ok / total) if total > 0 else 0.0
        judge = judge_map.get((tt, model))
        s = RoutingStats(
            task_type=tt,
            model=model,
            total_calls=total,
            successful=ok,
            success_rate=success_rate,
            judge_avg=judge[0] if judge else None,
            judge_count=judge[1] if judge else 0,
            avg_cost_usd=float(avg_cost or 0),
            avg_latency_ms=int(avg_lat or 0),
            samples=total + (judge[1] if judge else 0),
        )
        s.composite_score = _compute_composite(s)
        results.append(s)

    return results


# ── Preference tablosu ──────────────────────────────────────────────────


def compute_preferences(days: int = 14, min_calls: int = 30) -> dict[str, dict]:
    """
    Her task_type için en iyi skorlu model -> preference dict.

    Returns:
        {
          "test_generation": {
            "preferred_model": "gpt-4o-mini",
            "preferred_score": 0.78,
            "current_default_model": "gpt-4o",
            "current_default_score": 0.72,
            "suggestion": "switch" | "keep" | "insufficient_data",
            "candidates": [{model, composite_score, success_rate, ...}]
          },
          ...
        }
    """
    stats = aggregate_stats(days=days, min_calls=min_calls)
    if not stats:
        return {}

    # Task_type bazli grupla
    by_task: dict[str, list[RoutingStats]] = {}
    for s in stats:
        by_task.setdefault(s.task_type, []).append(s)

    preferences: dict[str, dict] = {}
    for tt, models in by_task.items():
        models.sort(key=lambda x: x.composite_score, reverse=True)
        if len(models) < 2:
            # Tek model verisi — karsilastirma yapamayiz
            preferences[tt] = {
                "preferred_model": models[0].model,
                "preferred_score": models[0].composite_score,
                "suggestion": "insufficient_data",
                "candidates": [m.to_dict() for m in models],
            }
            continue

        best = models[0]
        # Karar matrisindeki default'u cikart
        try:
            from app.domains.ai.smart_model_router import route_model
            default_rec = route_model(tt)
            default_model = default_rec.model
        except Exception:
            default_model = None

        default_stats = next((m for m in models if m.model == default_model), None)

        if default_stats is None:
            suggestion = "no_baseline"
        elif best.model == default_model:
            suggestion = "keep"
        else:
            # En az %5 fark varsa switch oneriyoruz
            delta = best.composite_score - default_stats.composite_score
            suggestion = "switch" if delta > 0.05 else "keep"

        preferences[tt] = {
            "preferred_model": best.model,
            "preferred_score": round(best.composite_score, 4),
            "current_default_model": default_model,
            "current_default_score": round(default_stats.composite_score, 4) if default_stats else None,
            "delta": round(best.composite_score - (default_stats.composite_score if default_stats else 0), 4),
            "suggestion": suggestion,
            "candidates": [m.to_dict() for m in models[:5]],
        }

    return preferences


def get_learned_preference(task_type: str) -> Optional[str]:
    """
    Ogrenilen preferred model'i cek (flag acikken route_model bunu uygular).

    Feature flag: ``ai.routing.learned`` — default False (shadow mode).
    DB'den okur: ``learned_routing_preferences`` tablosu.
    """
    try:
        from app.domains.feature_flags.service import feature_flags
        if not feature_flags.is_enabled("ai.routing.learned", default=False):
            return None
    except Exception:
        return None

    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'learned_routing_preferences')"
                )
                if not cur.fetchone()[0]:
                    return None
                cur.execute(
                    """
                    SELECT preferred_model
                    FROM learned_routing_preferences
                    WHERE task_type = %s AND suggestion = 'switch'
                    ORDER BY updated_at DESC
                    LIMIT 1
                    """,
                    (task_type,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("get_learned_preference hatasi: %s", exc)
        return None


def persist_preferences(preferences: dict[str, dict]) -> int:
    """Preference tablosuna yaz. Yoksa atla."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return 0

    written = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'learned_routing_preferences')"
            )
            if not cur.fetchone()[0]:
                logger.warning("learned_routing_preferences tablosu yok — migration çalıştır")
                return 0
            for tt, pref in preferences.items():
                cur.execute(
                    """
                    INSERT INTO learned_routing_preferences
                        (task_type, preferred_model, preferred_score,
                         default_model, default_score, suggestion,
                         sample_size, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (task_type) DO UPDATE SET
                        preferred_model = EXCLUDED.preferred_model,
                        preferred_score = EXCLUDED.preferred_score,
                        default_model = EXCLUDED.default_model,
                        default_score = EXCLUDED.default_score,
                        suggestion = EXCLUDED.suggestion,
                        sample_size = EXCLUDED.sample_size,
                        updated_at = now()
                    """,
                    (
                        tt,
                        pref.get("preferred_model"),
                        pref.get("preferred_score"),
                        pref.get("current_default_model"),
                        pref.get("current_default_score"),
                        pref.get("suggestion"),
                        sum(c.get("total_calls", 0) for c in pref.get("candidates", [])),
                    ),
                )
                written += 1
    except Exception as exc:
        logger.debug("persist_preferences hatasi: %s", exc)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    return written


def run_learning_cycle(days: int = 14, persist: bool = True) -> dict[str, Any]:
    """Nightly cron target: tek fonksiyonla aggregate + persist + dondur."""
    preferences = compute_preferences(days=days)
    n_written = persist_preferences(preferences) if persist else 0
    switches = [tt for tt, p in preferences.items() if p.get("suggestion") == "switch"]
    return {
        "analyzed_task_types": len(preferences),
        "persisted": n_written,
        "switches_suggested": switches,
        "preferences": preferences,
    }
