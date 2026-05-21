"""RAG auto-ingestion helpers — TSPM execution, BDD features, llm_traces feedback.

Tasarım:
    * Tüm hook'lar fire-and-forget. Hata olursa sessiz atlar.
    * Chunking: uzun metinler ~800 token (~3200 char) + 400 char overlap.
    * Dedup: KnowledgeStore.ingest content_hash ile otomatik yapar.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Any

from app.domains.ai.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

_CHUNK_CHAR_TARGET = 3200  # ~800 token
_CHUNK_OVERLAP_CHARS = 400


def _chunk_text(text: str, max_chars: int = _CHUNK_CHAR_TARGET, overlap: int = _CHUNK_OVERLAP_CHARS) -> list[str]:
    """Uzun metinleri parcalara bol. Paragraf siniriyla hizala."""
    if not text:
        return []
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + max_chars, n)
        if end < n:
            paragraph_break = text.rfind("\n\n", start + max_chars // 2, end)
            if paragraph_break > 0:
                end = paragraph_break + 2
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(start + 1, end - overlap)
    return chunks


def _async(fn, *args, **kwargs) -> None:
    threading.Thread(target=fn, args=args, kwargs=kwargs, daemon=True).start()


# ── TSPM execution hook ─────────────────────────────────────────────────


def ingest_tspm_execution(execution_id: str) -> None:
    """Test kosusu bittiginde cagrilir. Özet + failed result'lar RAG'a yazilir."""
    try:
        from app.infra.database import SessionLocal
        from app.domains.tspm.models import (
            TspmExecution,
            TspmExecutionMetrics,
            TspmExecutionResult,
            TspmScenario,
        )
        from sqlalchemy import select
    except Exception as exc:
        logger.debug("ingest_tspm_execution: import hatasi: %s", exc)
        return

    store = KnowledgeStore()
    try:
        with SessionLocal() as db:
            ex = db.get(TspmExecution, execution_id)
            if ex is None:
                return

            metrics = db.scalar(
                select(TspmExecutionMetrics)
                .where(TspmExecutionMetrics.execution_id == execution_id)
            )

            summary_parts = [
                f"Koşu: {ex.name}",
                f"Durum: {ex.status}",
                f"Tarih: {ex.created_at.isoformat() if ex.created_at else '-'}",
            ]
            if metrics:
                summary_parts.append(
                    f"Başarı orani: %{metrics.pass_rate:.1f} ({metrics.passed} gecti / {metrics.failed} başarısız)"
                )
            store.ingest(
                text="\n".join(summary_parts),
                source="execution",
                metadata={
                    "execution_id": execution_id,
                    "project_id": ex.project_id,
                    "type": "summary",
                    "status": ex.status,
                },
            )

            failed = list(db.scalars(
                select(TspmExecutionResult)
                .where(
                    TspmExecutionResult.execution_id == execution_id,
                    TspmExecutionResult.status == "failed",
                )
                .limit(50)
            ))
            for r in failed:
                sc = db.get(TspmScenario, r.scenario_id) if r.scenario_id else None
                note = r.note or ""
                if not note.strip():
                    continue
                text = (
                    f"Senaryo: {sc.title if sc else r.scenario_id}\n"
                    f"Koşu: {ex.name}\n"
                    f"Durum: failed\n"
                    f"Hata: {note[:1200]}"
                )
                store.ingest(
                    text=text,
                    source="execution",
                    metadata={
                        "execution_id": execution_id,
                        "scenario_id": r.scenario_id,
                        "project_id": ex.project_id,
                        "type": "failure",
                    },
                )
    except Exception as exc:
        logger.debug("ingest_tspm_execution hatasi (sessiz): %s", exc)


def ingest_tspm_execution_async(execution_id: str) -> None:
    """Fire-and-forget — TSPM router hook'lari bunu cagirir."""
    _async(ingest_tspm_execution, execution_id)


# ── Error pattern promote ──────────────────────────────────────────────


def promote_recurring_errors(min_occurrences: int = 3) -> int:
    """occurrence_count >= N olan execution'lari error_pattern'e cevir."""
    try:
        store = KnowledgeStore()
        conn = store._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE project_knowledge
                SET source = 'error_pattern'
                WHERE source = 'execution'
                  AND occurrence_count >= %s
                  AND content ~* '(error|hata|fail|exception|timeout|connection)'
                RETURNING id
                """,
                (min_occurrences,),
            )
            rows = cur.fetchall() or []
            return len(rows)
    except Exception as exc:
        logger.debug("promote_recurring_errors hatasi: %s", exc)
        return 0


# ── BDD feature dosyalari ──────────────────────────────────────────────


_FEATURE_DIRS = (
    "frameworks/playwright-cucumber-ts/features",
    "e2e",
    "engine/features",
    "frameworks",
)


def ingest_bdd_features(base_path: str | Path, limit: int | None = None) -> int:
    """.feature dosyalarini tara ve RAG'a yaz. Returns: chunk sayisi."""
    base = Path(base_path)
    if not base.exists():
        logger.debug("ingest_bdd_features: base_path yok: %s", base)
        return 0

    store = KnowledgeStore()
    total_chunks = 0
    files_processed = 0
    for feature_dir in _FEATURE_DIRS:
        dir_path = base / feature_dir
        if not dir_path.exists():
            continue
        for feature_file in dir_path.rglob("*.feature"):
            try:
                content = feature_file.read_text(encoding="utf-8", errors="ignore")
                if not content.strip():
                    continue
                rel_path = str(feature_file.relative_to(base))
                for idx, chunk in enumerate(_chunk_text(content)):
                    prefix = f"[Feature] {rel_path}\n\n"
                    store.ingest(
                        text=prefix + chunk,
                        source="feature_file",
                        metadata={
                            "file_path": rel_path,
                            "chunk_index": idx,
                            "file_name": feature_file.name,
                        },
                    )
                    total_chunks += 1
                files_processed += 1
                if limit and files_processed >= limit:
                    return total_chunks
            except Exception as exc:
                logger.debug("ingest_bdd_features %s hatasi: %s", feature_file, exc)
    logger.info("ingest_bdd_features: %d dosya -> %d chunk", files_processed, total_chunks)
    return total_chunks


# ── llm_traces feedback ────────────────────────────────────────────────


def ingest_trace_insights(days: int = 1, max_records: int = 200) -> dict[str, int]:
    """Son N gun trace'leri insight/error_pattern'e aktar."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return {"insights": 0, "errors": 0}

    store = KnowledgeStore()
    insights = 0
    errors = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, agent_name, model, task_type, system_prompt_preview,
                       user_prompt_preview, response_preview, success, error_message,
                       json_parse_ok, created_at
                FROM llm_traces
                WHERE created_at > NOW() - INTERVAL %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (f"{int(days)} days", max_records),
            )
            rows = cur.fetchall() or []

        for r in rows:
            (
                _id, agent, model, task_type,
                sys_prev, user_prev, resp_prev,
                success, err_msg, json_ok, created_at,
            ) = r
            if success and (json_ok is True or json_ok is None):
                if resp_prev and len(resp_prev) > 100:
                    text = (
                        f"[Agent: {agent} | Model: {model} | Task: {task_type}]\n"
                        f"Soru: {(user_prev or '')[:300]}\n"
                        f"Cevap: {(resp_prev or '')[:800]}"
                    )
                    if store.ingest(
                        text=text,
                        source="insight",
                        metadata={
                            "trace_id": _id,
                            "agent_name": agent,
                            "model": model,
                            "task_type": task_type,
                        },
                    ):
                        insights += 1
            elif not success and err_msg:
                text = (
                    f"[Agent: {agent} | Model: {model} | Task: {task_type}]\n"
                    f"HATA: {err_msg[:800]}\n"
                    f"Kaynak Soru: {(user_prev or '')[:300]}"
                )
                if store.ingest(
                    text=text,
                    source="error_pattern",
                    metadata={
                        "trace_id": _id,
                        "agent_name": agent,
                        "model": model,
                        "task_type": task_type,
                    },
                ):
                    errors += 1
    except Exception as exc:
        logger.debug("ingest_trace_insights hatasi: %s", exc)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    logger.info("ingest_trace_insights: insights=%d errors=%d", insights, errors)
    return {"insights": insights, "errors": errors}


# ── Ingestion stats ─────────────────────────────────────────────────────


def get_ingestion_stats() -> dict[str, Any]:
    """Her source için kayit sayisi + son ingest zamani."""
    try:
        from app.domains.ai.llm_trace import _get_conn
        conn = _get_conn()
    except Exception:
        return {"sources": [], "total": 0}

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT source,
                       COUNT(*) AS count,
                       MAX(created_at) AS last_ingest,
                       COALESCE(SUM(occurrence_count) FILTER (WHERE occurrence_count IS NOT NULL), 0) AS dedup_events
                FROM project_knowledge
                GROUP BY source
                ORDER BY count DESC
                """
            )
            rows = cur.fetchall() or []
            return {
                "sources": [
                    {
                        "source": r[0],
                        "count": r[1],
                        "last_ingest": r[2].isoformat() if r[2] else None,
                        "dedup_events": int(r[3] or 0),
                    }
                    for r in rows
                ],
                "total": sum(r[1] for r in rows),
            }
    except Exception as exc:
        logger.debug("get_ingestion_stats hatasi: %s", exc)
        return {"sources": [], "total": 0, "error": str(exc)}
    finally:
        try:
            conn.close()
        except Exception:
            pass
