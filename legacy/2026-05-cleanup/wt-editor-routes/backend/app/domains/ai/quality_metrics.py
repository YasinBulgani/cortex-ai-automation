"""
Quality Metrics — LLM Performans Izleme & Analiz
==================================================

LLM cagrilarinin kalitesini, basarisini ve performansini olcer.
Zaman icinde trendleri izler ve optimize edilecek alanlari tespit eder.

Metrikler:
  - Basari orani (agent bazinda, model bazinda)
  - JSON parse basari orani
  - Ortalama latency (model bazinda)
  - Token verimliligi
  - Hata dagilimi
  - Kalite skoru trendi (QualityJudge skorlari)
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def get_llm_quality_metrics(
    days: int = 30,
    agent_name: Optional[str] = None,
    model: Optional[str] = None,
    project_id: Optional[str] = None,
    user_id: Optional[str] = None,
    task_type: Optional[str] = None,
    phase: Optional[str] = None,
) -> Dict[str, Any]:
    """
    LLM kalite metriklerini hesapla.

    Returns:
        {
            "period": {"start": "...", "end": "...", "days": 30},
            "overview": {
                "total_calls": 150,
                "success_rate": 94.5,
                "json_parse_rate": 89.2,
                "avg_latency_ms": 2340,
                "unique_agents": 8,
                "unique_models": 3,
            },
            "by_agent": [
                {
                    "agent": "ServiceTestAgent",
                    "calls": 45,
                    "success_rate": 96.0,
                    "json_parse_rate": 91.0,
                    "avg_latency_ms": 3200,
                    "error_count": 2,
                }
            ],
            "by_model": [
                {
                    "model": "qwen2.5:32b",
                    "calls": 80,
                    "success_rate": 95.0,
                    "json_parse_rate": 88.5,
                    "avg_latency_ms": 2800,
                    "p95_latency_ms": 5200,
                }
            ],
            "daily_trend": [
                {"date": "2026-04-14", "calls": 12, "success_rate": 100.0, "avg_latency_ms": 2100}
            ],
            "error_distribution": {
                "timeout": 3,
                "connection_error": 1,
                "json_parse_failure": 5,
                "rate_limit": 0,
                "unknown": 2,
            },
            "recommendations": [
                "ServiceTestAgent JSON parse orani %89 — prompt'a 'JSON formatinda yanit ver' eklenmeli",
                "qwen2.5:32b ortalama latency 3.2s — basit task'lar icin mistral:latest kullanilabilir",
            ]
        }
    """
    try:
        from app.infra.database import SessionLocal
        from sqlalchemy import text

        db = SessionLocal()
        try:
            return _compute_metrics(db, days, agent_name, model, project_id, user_id, task_type, phase)
        finally:
            db.close()
    except Exception as exc:
        logger.warning("Quality metrics hesaplama hatasi: %s", exc)
        return _empty_metrics(days)


def _compute_metrics(
    db: Any,
    days: int,
    agent_filter: Optional[str],
    model_filter: Optional[str],
    project_id: Optional[str],
    user_id: Optional[str],
    task_type: Optional[str],
    phase: Optional[str],
) -> Dict[str, Any]:
    """DB'den metrikleri hesapla."""
    from sqlalchemy import text
    from app.domains.ai.llm_trace import _normalize_phase, _normalize_task_type

    if not project_id:
        return _empty_metrics(days)

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    cutoff_str = cutoff.isoformat()

    # Base filter
    where_parts = ["created_at >= :cutoff", "project_id = :project_id"]
    params: Dict[str, Any] = {"cutoff": cutoff_str, "project_id": project_id}
    if user_id:
        where_parts.append("user_id = :user_id")
        params["user_id"] = user_id
    if agent_filter:
        where_parts.append("agent_name = :agent")
        params["agent"] = agent_filter
    if model_filter:
        where_parts.append("model = :model")
        params["model"] = model_filter
    if task_type:
        normalized_task_type = _normalize_task_type(task_type, phase, "")
        where_parts.append("task_type = :task_type")
        params["task_type"] = normalized_task_type
    if phase:
        normalized_phase = _normalize_phase(phase, _normalize_task_type(task_type, phase, ""), is_streaming=False)
        where_parts.append("phase = :phase")
        params["phase"] = normalized_phase

    where_clause = " AND ".join(where_parts)

    # 1. Overview
    overview_sql = text(f"""
        SELECT
            COUNT(*) as total_calls,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
            SUM(CASE WHEN json_parse_ok = true THEN 1 ELSE 0 END) as json_ok_count,
            SUM(CASE WHEN json_parse_ok IS NOT NULL THEN 1 ELSE 0 END) as json_total,
            AVG(latency_ms) as avg_latency,
            COUNT(DISTINCT agent_name) as unique_agents,
            COUNT(DISTINCT model) as unique_models
        FROM llm_traces
        WHERE {where_clause}
    """)

    row = db.execute(overview_sql, params).fetchone()
    total = row[0] or 0
    success_count = row[1] or 0
    json_ok = row[2] or 0
    json_total = row[3] or 0
    avg_latency = row[4] or 0

    overview = {
        "total_calls": total,
        "success_rate": round(success_count / total * 100, 1) if total > 0 else 0,
        "json_parse_rate": round(json_ok / json_total * 100, 1) if json_total > 0 else 0,
        "avg_latency_ms": round(avg_latency),
        "unique_agents": row[5] or 0,
        "unique_models": row[6] or 0,
    }

    # 2. By Agent
    agent_sql = text(f"""
        SELECT
            agent_name,
            COUNT(*) as calls,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as ok,
            SUM(CASE WHEN json_parse_ok = true THEN 1 ELSE 0 END) as json_ok,
            SUM(CASE WHEN json_parse_ok IS NOT NULL THEN 1 ELSE 0 END) as json_total,
            AVG(latency_ms) as avg_lat,
            SUM(CASE WHEN NOT success THEN 1 ELSE 0 END) as errors
        FROM llm_traces
        WHERE {where_clause}
        GROUP BY agent_name
        ORDER BY calls DESC
    """)

    by_agent = []
    for r in db.execute(agent_sql, params).fetchall():
        calls = r[1] or 0
        ok = r[2] or 0
        jok = r[3] or 0
        jt = r[4] or 0
        by_agent.append({
            "agent": r[0],
            "calls": calls,
            "success_rate": round(ok / calls * 100, 1) if calls > 0 else 0,
            "json_parse_rate": round(jok / jt * 100, 1) if jt > 0 else 0,
            "avg_latency_ms": round(r[5] or 0),
            "error_count": r[6] or 0,
        })

    # 3. By Model
    model_sql = text(f"""
        SELECT
            model,
            COUNT(*) as calls,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as ok,
            SUM(CASE WHEN json_parse_ok = true THEN 1 ELSE 0 END) as json_ok,
            SUM(CASE WHEN json_parse_ok IS NOT NULL THEN 1 ELSE 0 END) as json_total,
            AVG(latency_ms) as avg_lat,
            PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms) as p95_lat
        FROM llm_traces
        WHERE {where_clause}
        GROUP BY model
        ORDER BY calls DESC
    """)

    by_model = []
    try:
        for r in db.execute(model_sql, params).fetchall():
            calls = r[1] or 0
            ok = r[2] or 0
            jok = r[3] or 0
            jt = r[4] or 0
            by_model.append({
                "model": r[0],
                "calls": calls,
                "success_rate": round(ok / calls * 100, 1) if calls > 0 else 0,
                "json_parse_rate": round(jok / jt * 100, 1) if jt > 0 else 0,
                "avg_latency_ms": round(r[5] or 0),
                "p95_latency_ms": round(r[6] or 0),
            })
    except Exception:
        # PERCENTILE_CONT olmayabilir (SQLite vb.)
        pass

    # 3b. By Task Type
    task_type_sql = text(f"""
        SELECT
            COALESCE(task_type, 'unknown') as task_type,
            COUNT(*) as calls,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as ok,
            AVG(latency_ms) as avg_lat
        FROM llm_traces
        WHERE {where_clause}
        GROUP BY COALESCE(task_type, 'unknown')
        ORDER BY calls DESC
    """)

    by_task_type = []
    for r in db.execute(task_type_sql, params).fetchall():
        calls = r[1] or 0
        ok = r[2] or 0
        by_task_type.append({
            "task_type": r[0],
            "calls": calls,
            "success_rate": round(ok / calls * 100, 1) if calls > 0 else 0,
            "avg_latency_ms": round(r[3] or 0),
        })

    phase_sql = text(f"""
        SELECT
            COALESCE(phase, 'unknown') as phase,
            COUNT(*) as calls,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as ok,
            AVG(latency_ms) as avg_lat
        FROM llm_traces
        WHERE {where_clause}
        GROUP BY COALESCE(phase, 'unknown')
        ORDER BY calls DESC
    """)

    by_phase = []
    for r in db.execute(phase_sql, params).fetchall():
        calls = r[1] or 0
        ok = r[2] or 0
        by_phase.append({
            "phase": r[0],
            "calls": calls,
            "success_rate": round(ok / calls * 100, 1) if calls > 0 else 0,
            "avg_latency_ms": round(r[3] or 0),
        })

    # 4. Daily Trend
    daily_sql = text(f"""
        SELECT
            CAST(created_at AS DATE) as day,
            COUNT(*) as calls,
            SUM(CASE WHEN success THEN 1 ELSE 0 END) as ok,
            AVG(latency_ms) as avg_lat
        FROM llm_traces
        WHERE {where_clause}
        GROUP BY CAST(created_at AS DATE)
        ORDER BY day DESC
        LIMIT 30
    """)

    daily_trend = []
    try:
        for r in db.execute(daily_sql, params).fetchall():
            calls = r[1] or 0
            ok = r[2] or 0
            daily_trend.append({
                "date": str(r[0]),
                "calls": calls,
                "success_rate": round(ok / calls * 100, 1) if calls > 0 else 0,
                "avg_latency_ms": round(r[3] or 0),
            })
    except Exception:
        pass

    daily_trend.reverse()

    # 5. Error Distribution
    error_sql = text(f"""
        SELECT error_message, COUNT(*) as cnt
        FROM llm_traces
        WHERE {where_clause} AND NOT success AND error_message IS NOT NULL
        GROUP BY error_message
        ORDER BY cnt DESC
        LIMIT 20
    """)

    error_dist: Dict[str, int] = {
        "timeout": 0, "connection_error": 0,
        "json_parse_failure": 0, "rate_limit": 0, "unknown": 0,
    }
    try:
        for r in db.execute(error_sql, params).fetchall():
            msg = (r[0] or "").lower()
            count = r[1] or 0
            if "timeout" in msg:
                error_dist["timeout"] += count
            elif "connection" in msg or "connect" in msg:
                error_dist["connection_error"] += count
            elif "json" in msg or "parse" in msg:
                error_dist["json_parse_failure"] += count
            elif "rate" in msg or "429" in msg:
                error_dist["rate_limit"] += count
            else:
                error_dist["unknown"] += count
    except Exception:
        pass

    # 6. Recommendations
    recommendations = _generate_recommendations(overview, by_agent, by_model, error_dist)

    return {
        "period": {
            "start": cutoff.strftime("%Y-%m-%d"),
            "end": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "days": days,
        },
        "overview": overview,
        "by_agent": by_agent,
        "by_model": by_model,
        "by_task_type": by_task_type,
        "by_phase": by_phase,
        "daily_trend": daily_trend,
        "error_distribution": error_dist,
        "recommendations": recommendations,
    }


def _generate_recommendations(
    overview: Dict[str, Any],
    by_agent: List[Dict[str, Any]],
    by_model: List[Dict[str, Any]],
    errors: Dict[str, int],
) -> List[str]:
    """Metriklerden otomatik iyilestirme onerileri uret."""
    recs = []

    # JSON parse orani dusuk
    if overview.get("json_parse_rate", 100) < 90:
        recs.append(
            f"JSON parse basari orani %{overview['json_parse_rate']} — "
            "Prompt'lara 'Yaniti SADECE JSON formatinda ver, aciklama ekleme' talimatini ekleyin."
        )

    # Yuksek latency
    if overview.get("avg_latency_ms", 0) > 5000:
        recs.append(
            f"Ortalama LLM latency {overview['avg_latency_ms']}ms — "
            "Basit task'lar icin daha hizli model (mistral:latest) kullanmayi deneyin."
        )

    # Agent bazinda sorunlar
    for a in by_agent:
        if a["success_rate"] < 85 and a["calls"] >= 5:
            recs.append(
                f"{a['agent']} basari orani %{a['success_rate']} ({a['calls']} cagri) — "
                "Prompt iyilestirmesi veya model degisikligi onerilir."
            )
        if a.get("json_parse_rate", 100) < 80 and a["calls"] >= 3:
            recs.append(
                f"{a['agent']} JSON parse orani %{a['json_parse_rate']} — "
                "Few-shot ornekler veya daha guclu JSON modu kullanin."
            )

    # Model bazinda sorunlar
    for m in by_model:
        if m.get("p95_latency_ms", 0) > 10000:
            recs.append(
                f"{m['model']} P95 latency {m['p95_latency_ms']}ms — "
                "Bu model agir yukler altinda yavasliyorr, alternatif degerlendirilmeli."
            )

    # Hata dagilimi
    if errors.get("timeout", 0) > 3:
        recs.append(
            f"{errors['timeout']} timeout hatasi — "
            "max_tokens veya model timeout ayarlarini gozden gecirin."
        )
    if errors.get("connection_error", 0) > 2:
        recs.append(
            f"{errors['connection_error']} baglanti hatasi — "
            "Ollama servisi durumunu kontrol edin, circuit breaker dogru calistigini dogrulayin."
        )

    if not recs:
        recs.append("Tum metrikler normal seviyede — surekli izlemeye devam edin.")

    return recs


def _empty_metrics(days: int) -> Dict[str, Any]:
    """Bos metrik sonucu (DB yoksa veya hata durumunda)."""
    now = datetime.now(timezone.utc)
    return {
        "period": {
            "start": (now - timedelta(days=days)).strftime("%Y-%m-%d"),
            "end": now.strftime("%Y-%m-%d"),
            "days": days,
        },
        "overview": {
            "total_calls": 0, "success_rate": 0, "json_parse_rate": 0,
            "avg_latency_ms": 0, "unique_agents": 0, "unique_models": 0,
        },
        "by_agent": [],
        "by_model": [],
        "daily_trend": [],
        "error_distribution": {},
        "recommendations": ["Henuz LLM cagri verisi bulunmuyor."],
    }


# ── Fine-Tune Data Collector ─────────────────────────────────────────


def collect_finetune_pair(
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    quality_score: Optional[float] = None,
    is_good_example: bool = True,
    project_id: Optional[str] = None,
) -> None:
    """
    Yuksek kaliteli input/output cifti topla (gelecekte fine-tuning icin).

    Sadece basarili, yuksek kaliteli ciktilari kaydeder.
    Quality score >= 7.0 olan veya manuel olarak iyi isaretlenen ornekler.
    """
    if quality_score is not None and quality_score < 7.0:
        return
    if not is_good_example:
        return

    try:
        from app.domains.ai.knowledge_store import KnowledgeStore

        store = KnowledgeStore(project_id=project_id)
        text = (
            f"[FINETUNE] Agent: {agent_name}\n"
            f"System: {system_prompt[:500]}\n"
            f"User: {user_prompt[:1000]}\n"
            f"Response: {response[:2000]}"
        )
        store.ingest(
            text=text,
            source="insight",
            metadata={
                "type": "finetune_pair",
                "agent_name": agent_name,
                "quality_score": str(quality_score or "manual"),
                "collected_at": datetime.now(timezone.utc).isoformat(),
            },
            project_id=project_id,
        )
        logger.debug("Fine-tune pair kaydedildi: %s (score=%.1f)", agent_name, quality_score or 0)
    except Exception as exc:
        logger.debug("Fine-tune pair kayit hatasi: %s", exc)
