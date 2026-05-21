"""
LLM Call Tracing — unified trace contract for all LLM flows.

Tamamen fire-and-forget: hata olursa sessizce atlar, pipeline'i ASLA kirmaz.
Prompt/response'un tamamini degil, yalnizca preview (on-ek) saklar — DB sismesini onler.

Kullanim:
    from app.domains.ai.llm_trace import log_llm_call
    log_llm_call(
        agent_name="ScenarioGenerator",
        model="qwen2.5:32b",
        system_prompt="Sen bir QA...",
        user_prompt="Login senaryosu üret",
        response="{ ... }",
        latency_ms=4200,
    )
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Preview limitleri — tam metin yerine sadece baslangic saklanir
_SYSTEM_PREVIEW_LEN = 500
_USER_PREVIEW_LEN = 500
_RESPONSE_PREVIEW_LEN = 1000

_MODEL_COST_PER_1K_TOKENS = {
    "gpt-4o": 0.0100,
    "gpt-4o-mini": 0.0010,
    "gpt-4-turbo": 0.0200,
    "claude-sonnet-4-20250514": 0.0180,
    "claude-3-5-sonnet-20241022": 0.0150,
}
_PROVIDER_DEFAULT_COST_PER_1K_TOKENS = {
    "openai": 0.0100,
    "anthropic": 0.0150,
    "ollama": 0.0,
}

_TASK_TYPE_ALIASES = {
    "chat": "chat",
    "chat_service": "chat",
    "chat_stream": "chat",
    "stream_chat": "chat",
    "test_analysis": "test_analysis",
    "analysis": "test_analysis",
    "debug_test": "test_analysis",
    "stream_test_analysis": "test_analysis",
    "scenario_generation": "scenario_generation",
    "stream_scenario_generation": "scenario_generation",
    "test_data_generation": "test_data_generation",
    "stream_test_data_generation": "test_data_generation",
    "nl_test_generation": "nl_test_generation",
    "test_generation": "nl_test_generation",
    "generate_test_cases": "nl_test_generation",
    "nl_test_generator": "nl_test_generation",
    "nl_test_suggest": "nl_test_suggest",
    "suggest": "nl_test_suggest",
    "assert_advice": "assert_advice",
    "assert_advisor": "assert_advice",
    "code_generation": "code_generation",
    "generate_gherkin": "code_generation",
    "generate_java_steps": "code_generation",
    "generate_playwright": "code_generation",
    "security_audit": "security_audit",
    "qa_planning": "qa_planning",
    "qa_orchestrator": "qa_planning",
    "plan": "qa_planning",
    "general_stream": "general_stream",
    "stream_general": "general_stream",
}

_PHASE_ALIASES = {
    "stream_chat": "chat",
    "chat_stream": "chat",
    "stream_scenario_generation": "scenarios",
    "stream_test_analysis": "analysis",
    "stream_test_data_generation": "test_data",
    "stream_general": "stream",
    "api_test": "api_test",
    "bdd": "bdd",
    "pytest": "pytest",
    "playwright": "playwright",
    "chat": "chat",
    "analysis": "analysis",
    "scenarios": "scenarios",
    "test_data": "test_data",
    "suggest": "suggest",
    "plan": "plan",
    "verify": "verify",
    "stream": "stream",
}


@dataclass
class LlmTraceRecord:
    agent_name: str
    model: str
    system_prompt: str
    user_prompt: str
    response: str
    latency_ms: int
    success: bool = True
    error_message: str = ""
    json_parse_ok: bool | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    run_id: str | None = None
    phase: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    project_id: str | None = None
    user_id: str | None = None
    provider: str | None = None
    task_type: str | None = None
    prompt_version: str | None = None
    fallback_used: bool = False
    cost_usd: float | None = None
    is_streaming: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


def _get_db_url() -> str:
    """Veritabani URL'sini config veya environment'tan al."""
    try:
        from app.config import settings
        return settings.database_url
    except Exception:
        import os
        return os.environ.get(
            "DATABASE_URL",
            "postgresql://twai_user:twai_pass@127.0.0.1:5432/twai_db",
        )


# ── Connection Pool ──────────────────────────────────────────────────────
import threading as _pool_threading

_trace_pool_lock = _pool_threading.Lock()
_trace_pool: list = []
_TRACE_POOL_MAX = 3


def _get_conn():
    """
    psycopg2 bağlantısı oluştur (KnowledgeStore pattern'i).
    Her cagri için yeni bağlantı — fire-and-forget için en guvenli yol.
    """
    import psycopg2

    with _trace_pool_lock:
        while _trace_pool:
            conn = _trace_pool.pop()
            try:
                if not conn.closed:
                    return conn
            except Exception:
                pass

    dsn = _get_db_url().replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(dsn)
    conn.autocommit = True
    return conn


def _return_conn(conn) -> None:
    """Baglantıyı pool'a geri koy."""
    if conn is None:
        return
    try:
        if conn.closed:
            return
    except Exception:
        return
    with _trace_pool_lock:
        if len(_trace_pool) < _TRACE_POOL_MAX:
            _trace_pool.append(conn)
        else:
            try:
                conn.close()
            except Exception:
                pass


def _safe_row_get(row: Any, idx: int, default: Any = None) -> Any:
    if row is None:
        return default
    try:
        return row[idx]
    except Exception:
        return default


def _infer_provider(model: str) -> str | None:
    lowered = (model or "").lower()
    if lowered.startswith("gpt-"):
        return "openai"
    if lowered.startswith("claude-"):
        return "anthropic"
    if lowered:
        return "ollama"
    return None


def _estimate_tokens(system_prompt: str, user_prompt: str, response: str) -> tuple[int, int, int]:
    prompt_tokens = max((len(system_prompt or "") + len(user_prompt or "")) // 3, 0)
    completion_tokens = max(len(response or "") // 3, 0)
    return prompt_tokens, completion_tokens, prompt_tokens + completion_tokens


def _estimate_cost_usd(provider: str | None, model: str, total_tokens: int | None) -> float | None:
    if total_tokens is None:
        return None
    effective_provider = provider or _infer_provider(model)
    cost_per_1k = _MODEL_COST_PER_1K_TOKENS.get(model)
    if cost_per_1k is None and effective_provider:
        cost_per_1k = _PROVIDER_DEFAULT_COST_PER_1K_TOKENS.get(effective_provider)
    if cost_per_1k is None:
        return None
    return round((total_tokens / 1000.0) * cost_per_1k, 6)


def _status_from(success: bool, error_message: str | None) -> str:
    if success:
        return "success"
    msg = (error_message or "").lower()
    if "timeout" in msg:
        return "timeout"
    return "error"


def _normalize_metadata(metadata: dict[str, Any] | None, *, is_streaming: bool) -> dict[str, Any]:
    normalized = dict(metadata or {})
    if is_streaming:
        normalized.setdefault("streaming", True)
    return normalized


def _normalize_task_type(
    task_type: str | None,
    phase: str | None,
    agent_name: str,
) -> str:
    candidates = [task_type, phase, agent_name]
    for candidate in candidates:
        key = (candidate or "").strip().lower()
        if not key:
            continue
        if key in _TASK_TYPE_ALIASES:
            return _TASK_TYPE_ALIASES[key]
    return "unknown"


def _normalize_phase(
    phase: str | None,
    normalized_task_type: str,
    *,
    is_streaming: bool,
) -> str | None:
    key = (phase or "").strip().lower()
    if key:
        return _PHASE_ALIASES.get(key, key)
    if is_streaming:
        return "stream"
    default_by_task = {
        "chat": "chat",
        "test_analysis": "analysis",
        "scenario_generation": "scenarios",
        "test_data_generation": "test_data",
        "nl_test_generation": "generation",
        "nl_test_suggest": "suggest",
        "assert_advice": "analysis",
        "code_generation": "generation",
        "security_audit": "analysis",
        "qa_planning": "plan",
        "general_stream": "stream",
    }
    return default_by_task.get(normalized_task_type)


def build_llm_trace_record(
    *,
    agent_name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    latency_ms: int,
    success: bool = True,
    error_message: str = "",
    json_parse_ok: bool | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    run_id: str | None = None,
    phase: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    project_id: str | None = None,
    user_id: str | None = None,
    provider: str | None = None,
    task_type: str | None = None,
    prompt_version: str | None = None,
    fallback_used: bool = False,
    cost_usd: float | None = None,
    is_streaming: bool = False,
    metadata: dict[str, Any] | None = None,
) -> LlmTraceRecord:
    if prompt_tokens is None or completion_tokens is None or total_tokens is None:
        est_prompt, est_completion, est_total = _estimate_tokens(system_prompt, user_prompt, response)
        prompt_tokens = est_prompt if prompt_tokens is None else prompt_tokens
        completion_tokens = est_completion if completion_tokens is None else completion_tokens
        total_tokens = est_total if total_tokens is None else total_tokens

    resolved_provider = provider or _infer_provider(model)
    normalized_task_type = _normalize_task_type(task_type, phase, agent_name)
    normalized_phase = _normalize_phase(phase, normalized_task_type, is_streaming=is_streaming)
    normalized_metadata = _normalize_metadata(metadata, is_streaming=is_streaming)
    raw_task_type = (task_type or "").strip()
    raw_phase = (phase or "").strip()
    if raw_task_type and raw_task_type != normalized_task_type:
        normalized_metadata.setdefault("raw_task_type", raw_task_type)
    if raw_phase and raw_phase != (normalized_phase or ""):
        normalized_metadata.setdefault("raw_phase", raw_phase)
    if cost_usd is None:
        cost_usd = _estimate_cost_usd(resolved_provider, model, total_tokens)

    return LlmTraceRecord(
        agent_name=agent_name,
        model=model or "unknown",
        system_prompt=system_prompt or "",
        user_prompt=user_prompt or "",
        response=response or "",
        latency_ms=int(latency_ms or 0),
        success=success,
        error_message=error_message or "",
        json_parse_ok=json_parse_ok,
        temperature=temperature,
        max_tokens=max_tokens,
        run_id=run_id,
        phase=normalized_phase,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
        project_id=project_id,
        user_id=user_id,
        provider=resolved_provider,
        task_type=normalized_task_type,
        prompt_version=prompt_version,
        fallback_used=fallback_used,
        cost_usd=cost_usd,
        is_streaming=is_streaming,
        metadata=normalized_metadata,
    )


def log_llm_call(
    agent_name: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    response: str,
    latency_ms: int,
    success: bool = True,
    error_message: str = "",
    json_parse_ok: bool | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    run_id: str | None = None,
    phase: str | None = None,
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
    correlation_id: str | None = None,
    project_id: str | None = None,
    user_id: str | None = None,
    provider: str | None = None,
    task_type: str | None = None,
    metadata: dict | None = None,
    fallback_used: bool = False,
) -> int | None:
    """
    LLM cagrisini DB'ye kaydet. Hata olursa sessizce atlar — pipeline'i ASLA kirmaz.

    Args:
        agent_name:     Cagiyi yapan ajan adi (BaseAgent.name veya "chat", "analysis" vb.)
        model:          Kullanilan LLM modeli (qwen2.5:32b, mistral:latest, vb.)
        system_prompt:  System prompt (sadece ilk 500 karakter saklanir)
        user_prompt:    User prompt (sadece ilk 500 karakter saklanir)
        response:       LLM yaniti (sadece ilk 1000 karakter saklanir)
        latency_ms:     Cagri süresi (milisaniye)
        success:        Cagri başarılı mi?
        error_message:  Hata varsa mesaj
        json_parse_ok:  JSON parse başarılı mi? (None = JSON beklenmiyordu)
        temperature:    Kullanilan temperature
        max_tokens:     Kullanilan max_tokens limiti
        run_id:         Pipeline run_id (opsiyonel)
        phase:          Pipeline fazı (opsiyonel)
        prompt_tokens:  Prompt token sayisi (opsiyonel)
        completion_tokens: Completion token sayisi (opsiyonel)
        total_tokens:   Toplam token sayisi (opsiyonel)
    """
    # Auto-resolve correlation_id from contextvar if not provided
    if correlation_id is None:
        try:
            from app.domains.ai.correlation import get_correlation_id
            correlation_id = get_correlation_id()
        except Exception:
            correlation_id = None

    metadata_json = json.dumps(metadata or {}, default=str)

    try:
        conn = _get_conn()
        try:
            trace_id: int | None = None
            with conn.cursor() as cur:
                # Full-schema insert (newest, preferred path)
                try:
                    cur.execute(
                        """
                        INSERT INTO llm_traces (
                            project_id, user_id, run_id, agent_name, provider, model,
                            task_type, phase,
                            system_prompt_preview, user_prompt_preview,
                            response_preview, full_response_length,
                            temperature, max_tokens, latency_ms,
                            success, error_message, json_parse_ok,
                            prompt_tokens, completion_tokens, total_tokens,
                            fallback_used, trace_metadata
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, CAST(%s AS JSONB)
                        ) RETURNING id
                        """,
                        (
                            project_id, user_id, run_id, agent_name, provider, model,
                            task_type, phase,
                            (system_prompt or "")[:_SYSTEM_PREVIEW_LEN],
                            (user_prompt or "")[:_USER_PREVIEW_LEN],
                            (response or "")[:_RESPONSE_PREVIEW_LEN],
                            len(response or ""),
                            temperature, max_tokens, latency_ms,
                            success,
                            error_message[:2000] if error_message else None,
                            json_parse_ok,
                            prompt_tokens, completion_tokens, total_tokens,
                            fallback_used, metadata_json,
                        ),
                    )
                    row = cur.fetchone()
                    trace_id = int(_safe_row_get(row, 0)) if row else None
                except Exception:
                    # Fallback: minimal schema (legacy DB)
                    try:
                        cur.execute(
                            """
                            INSERT INTO llm_traces (
                                run_id, agent_name, model, phase,
                                system_prompt_preview, user_prompt_preview,
                                response_preview, full_response_length,
                                temperature, max_tokens, latency_ms,
                                success, error_message, json_parse_ok,
                                prompt_tokens, completion_tokens, total_tokens
                            ) VALUES (
                                %s, %s, %s, %s,
                                %s, %s,
                                %s, %s,
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s, %s
                            ) RETURNING id
                            """,
                            (
                                run_id, agent_name, model, phase,
                                (system_prompt or "")[:_SYSTEM_PREVIEW_LEN],
                                (user_prompt or "")[:_USER_PREVIEW_LEN],
                                (response or "")[:_RESPONSE_PREVIEW_LEN],
                                len(response or ""),
                                temperature, max_tokens, latency_ms,
                                success,
                                error_message[:2000] if error_message else None,
                                json_parse_ok,
                                prompt_tokens, completion_tokens, total_tokens,
                            ),
                        )
                        row = cur.fetchone()
                        trace_id = int(_safe_row_get(row, 0)) if row else None
                    except Exception:
                        pass
            _return_conn(conn)
            return trace_id
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return None
    except Exception as exc:
        logger.debug("llm_trace kayit hatasi (sessiz): %s", exc)
        return None


def get_recent_traces(
    run_id: str | None = None,
    agent_name: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """
    Son LLM trace kayitlarini getir — API endpoint'i için.

    Args:
        run_id:      Belirli pipeline run_id'ye filtrele (opsiyonel)
        agent_name:  Belirli ajana filtrele (opsiyonel)
        limit:       Maks kayit sayisi (default 50, max 200)

    Returns:
        Trace kayitlarinin listesi (dict)
    """
    limit = min(limit, 200)
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE llm_traces
                    SET json_parse_ok = %s
                    WHERE id = %s
                    """,
                    (success, trace_id),
                )
            _return_conn(conn)
            return True
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return False
    except Exception as exc:
        logger.debug("llm_trace json_parse update hatasi: %s", exc)
        return False


def _deserialize_metadata(raw: Any) -> dict[str, Any]:
    if not raw:
        return {}
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def get_recent_traces(
    project_id: str | None = None,
    user_id: str | None = None,
    run_id: str | None = None,
    agent_name: str | None = None,
    task_type: str | None = None,
    phase: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Son LLM trace kayitlarini getir — API endpoint'i icin."""
    limit = min(limit, 200)
    if not project_id:
        return []

    try:
        conn = _get_conn()
        try:
            traces_result: list[dict[str, Any]] = []
            with conn.cursor() as cur:
                conditions: list[str] = ["project_id = %s"]
                params: list[Any] = [project_id]

                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                if run_id:
                    conditions.append("run_id = %s")
                    params.append(run_id)
                if agent_name:
                    conditions.append("agent_name = %s")
                    params.append(agent_name)
                if task_type:
                    conditions.append("task_type = %s")
                    params.append(_normalize_task_type(task_type, None, agent_name or ""))
                if phase:
                    conditions.append("phase = %s")
                    params.append(_normalize_phase(phase, _normalize_task_type(task_type, phase, agent_name or ""), is_streaming=False))

                where = "WHERE " + " AND ".join(conditions)

                try:
                    cur.execute(
                        f"""
                        SELECT
                            id, project_id, user_id, run_id, agent_name, provider, model,
                            task_type, phase, prompt_version,
                            system_prompt_preview, user_prompt_preview,
                            response_preview, full_response_length,
                            temperature, max_tokens, latency_ms,
                            success, error_message, json_parse_ok,
                            prompt_tokens, completion_tokens, total_tokens,
                            cost_usd, fallback_used, is_streaming, trace_metadata,
                            created_at
                        FROM llm_traces
                        {where}
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        params + [limit],
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        metadata = _deserialize_metadata(_safe_row_get(row, 26, {}))
                        success = bool(_safe_row_get(row, 17, False))
                        error_message = _safe_row_get(row, 18, None)
                        created_at = _safe_row_get(row, 27, None)
                        user_preview = _safe_row_get(row, 11, "")
                        system_preview = _safe_row_get(row, 10, "")
                        response_preview = _safe_row_get(row, 12, "")
                        traces_result.append(
                            {
                                "id": _safe_row_get(row, 0),
                                "project_id": _safe_row_get(row, 1),
                                "user_id": _safe_row_get(row, 2),
                                "run_id": _safe_row_get(row, 3),
                                "agent_name": _safe_row_get(row, 4),
                                "provider": _safe_row_get(row, 5),
                                "model": _safe_row_get(row, 6),
                                "task_type": _safe_row_get(row, 7),
                                "phase": _safe_row_get(row, 8),
                                "prompt_version": _safe_row_get(row, 9),
                                "system_prompt_preview": system_preview,
                                "user_prompt_preview": user_preview,
                                "response_preview": response_preview,
                                "input_preview": user_preview or system_preview,
                                "output_preview": response_preview,
                                "full_response_length": _safe_row_get(row, 13),
                                "temperature": _safe_row_get(row, 14),
                                "max_tokens": _safe_row_get(row, 15),
                                "latency_ms": _safe_row_get(row, 16),
                                "success": success,
                                "status": _status_from(success, error_message),
                                "error_message": error_message,
                                "json_parse_ok": _safe_row_get(row, 19),
                                "prompt_tokens": _safe_row_get(row, 20),
                                "completion_tokens": _safe_row_get(row, 21),
                                "total_tokens": _safe_row_get(row, 22),
                                "cost_usd": float(_safe_row_get(row, 23, 0) or 0),
                                "fallback_used": bool(_safe_row_get(row, 24, False)),
                                "is_streaming": bool(_safe_row_get(row, 25, False)),
                                "metadata": metadata,
                                "created_at": created_at.isoformat() if created_at else None,
                            }
                        )
                except Exception:
                    cur.execute(
                        f"""
                        SELECT id, run_id, agent_name, model, phase,
                               system_prompt_preview, user_prompt_preview,
                               response_preview, full_response_length,
                               temperature, max_tokens, latency_ms,
                               success, error_message, json_parse_ok,
                               created_at
                        FROM llm_traces
                        {where}
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        params + [limit],
                    )
                    rows = cur.fetchall()
                    for row in rows:
                        success = bool(_safe_row_get(row, 12, False))
                        error_message = _safe_row_get(row, 13, None)
                        created_at = _safe_row_get(row, 15, None)
                        user_preview = _safe_row_get(row, 6, "")
                        system_preview = _safe_row_get(row, 5, "")
                        response_preview = _safe_row_get(row, 7, "")
                        traces_result.append(
                            {
                                "id": _safe_row_get(row, 0),
                                "run_id": _safe_row_get(row, 1),
                                "agent_name": _safe_row_get(row, 2),
                                "model": _safe_row_get(row, 3),
                                "phase": _safe_row_get(row, 4),
                                "system_prompt_preview": system_preview,
                                "user_prompt_preview": user_preview,
                                "response_preview": response_preview,
                                "input_preview": user_preview or system_preview,
                                "output_preview": response_preview,
                                "full_response_length": _safe_row_get(row, 8),
                                "temperature": _safe_row_get(row, 9),
                                "max_tokens": _safe_row_get(row, 10),
                                "latency_ms": _safe_row_get(row, 11),
                                "success": success,
                                "status": _status_from(success, error_message),
                                "error_message": error_message,
                                "json_parse_ok": _safe_row_get(row, 14),
                                "created_at": created_at.isoformat() if created_at else None,
                                "metadata": {},
                            }
                        )
            _return_conn(conn)
            return traces_result
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return []
    except Exception as exc:
        logger.debug("llm_trace okuma hatasi: %s", exc)
        return []


def get_trace_stats() -> dict[str, Any]:
    """LLM trace özet istatistikleri — dashboard için."""
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                conditions = ["model = %s", "task_type = %s", "created_at > NOW() - (%s || ' days')::interval"]
                params: list[Any] = [model, normalized_task_type, str(days)]
                if normalized_phase:
                    conditions.append("phase = %s")
                    params.append(normalized_phase)
                if project_id:
                    conditions.append("project_id = %s")
                    params.append(project_id)
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                where_clause = " AND ".join(conditions)

                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_calls,
                        COUNT(*) FILTER (WHERE success = TRUE) as successful,
                        ROUND(AVG(latency_ms)) as avg_latency,
                        COUNT(*) FILTER (WHERE json_parse_ok = TRUE) as json_ok,
                        COUNT(*) FILTER (WHERE json_parse_ok IS NOT NULL) as json_total,
                        COUNT(*) FILTER (WHERE fallback_used = TRUE) as fallback_count,
                        COALESCE(AVG(cost_usd), 0) as avg_cost
                    FROM llm_traces
                    WHERE {where_clause}
                    """,
                    params,
                )
                row = cur.fetchone()
                total = int(_safe_row_get(row, 0, 0) or 0)
                if total == 0:
                    _return_conn(conn)
                    return {}

                try:
                    cur.execute(
                        f"""
                        SELECT PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY latency_ms)
                        FROM llm_traces
                        WHERE {where_clause}
                        """,
                        params,
                    )
                    p95_latency = int(_safe_row_get(cur.fetchone(), 0, 0) or 0)
                except Exception:
                    p95_latency = 0

                successful = int(_safe_row_get(row, 1, 0) or 0)
                avg_latency = int(_safe_row_get(row, 2, 0) or 0)
                json_ok = int(_safe_row_get(row, 3, 0) or 0)
                json_total = int(_safe_row_get(row, 4, 0) or 0)
                fallback_count = int(_safe_row_get(row, 5, 0) or 0)
                avg_cost = float(_safe_row_get(row, 6, 0) or 0)

                perf_result = {
                    "task_type": normalized_task_type,
                    "phase": normalized_phase,
                    "total_calls": total,
                    "success_rate": round(successful / total, 3) if total else 0.0,
                    "avg_latency_ms": avg_latency,
                    "p95_latency_ms": p95_latency,
                    "json_parse_ok_rate": round(json_ok / json_total, 3) if json_total else 1.0,
                    "fallback_rate": round(fallback_count / total, 3) if total else 0.0,
                    "avg_cost_usd": round(avg_cost, 6),
                    "sample_size_sufficient": total >= 10,
                }
            _return_conn(conn)
            return perf_result
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return {}
    except Exception as exc:
        logger.debug("Task performance stats alinamadi (%s/%s): %s", model, normalized_task_type, exc)
        return {}


def _empty_trace_stats() -> dict[str, Any]:
    return {
        "total_calls": 0,
        "total_traces": 0,
        "successful": 0,
        "failed": 0,
        "success_rate": 0.0,
        "avg_latency_ms": 0,
        "max_latency_ms": 0,
        "unique_agents": 0,
        "unique_models": 0,
        "json_failures": 0,
        "timeout_count": 0,
        "total_tokens": 0,
        "total_cost_usd": 0.0,
        "top_agents": [],
        "top_models": [],
    }


def update_json_parse_status(trace_id: int | None, success: bool) -> bool:
    """Update json_parse_ok for a specific trace row. Fire-and-forget safe."""
    if trace_id is None:
        return False
    try:
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE llm_traces SET json_parse_ok = %s WHERE id = %s",
                    (success, trace_id),
                )
            _return_conn(conn)
            return True
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return False
    except Exception as exc:
        logger.debug("update_json_parse_status hatasi (sessiz): %s", exc)
        return False


def get_trace_stats() -> dict[str, Any]:
    """LLM trace ozet istatistikleri — dashboard icin."""
    return get_trace_stats_scoped(project_id=None)


def get_trace_stats_scoped(
    project_id: str | None,
    user_id: str | None = None,
) -> dict[str, Any]:
    """LLM trace ozet istatistikleri — scope'lu dashboard icin."""
    if not project_id:
        return _empty_trace_stats()

    try:
        conn = _get_conn()
        try:
            with conn.cursor() as cur:
                conditions = ["project_id = %s"]
                params: list[Any] = [project_id]
                if user_id:
                    conditions.append("user_id = %s")
                    params.append(user_id)
                where_clause = " AND ".join(conditions)

                cur.execute(
                    f"""
                    SELECT
                        COUNT(*) as total_calls,
                        COUNT(*) FILTER (WHERE success = TRUE) as successful,
                        COUNT(*) FILTER (WHERE success = FALSE) as failed,
                        COUNT(*) FILTER (WHERE json_parse_ok = FALSE) as json_failures,
                        ROUND(AVG(latency_ms)) as avg_latency_ms,
                        MAX(latency_ms) as max_latency_ms,
                        COUNT(DISTINCT agent_name) as unique_agents,
                        COUNT(DISTINCT model) as unique_models,
                        COALESCE(SUM(total_tokens), 0) as total_tokens,
                        COALESCE(SUM(cost_usd), 0) as total_cost_usd,
                        COUNT(*) FILTER (
                            WHERE success = FALSE
                            AND COALESCE(error_message, '') ILIKE '%%timeout%%'
                        ) as timeout_count
                    FROM llm_traces
                    WHERE {where_clause}
                    """,
                    params,
                )
                row = cur.fetchone()
                if not row:
                    _return_conn(conn)
                    return _empty_trace_stats()

                total_calls = int(_safe_row_get(row, 0, 0) or 0)
                successful = int(_safe_row_get(row, 1, 0) or 0)
                failed = int(_safe_row_get(row, 2, 0) or 0)
                json_failures = int(_safe_row_get(row, 3, 0) or 0)
                avg_latency_ms = int(_safe_row_get(row, 4, 0) or 0)
                max_latency_ms = int(_safe_row_get(row, 5, 0) or 0)
                unique_agents = int(_safe_row_get(row, 6, 0) or 0)
                unique_models = int(_safe_row_get(row, 7, 0) or 0)
                total_tokens = int(_safe_row_get(row, 8, 0) or 0)
                total_cost_usd = float(_safe_row_get(row, 9, 0) or 0)
                timeout_count = int(_safe_row_get(row, 10, 0) or 0)

                cur.execute(
                    f"""
                    SELECT agent_name, COUNT(*)
                    FROM llm_traces
                    WHERE {where_clause}
                    GROUP BY agent_name
                    ORDER BY COUNT(*) DESC
                    """,
                    params,
                )
                traces_by_agent = {
                    name: count for name, count in cur.fetchall() if name
                }

                cur.execute(
                    f"""
                    SELECT model, COUNT(*)
                    FROM llm_traces
                    WHERE {where_clause}
                    GROUP BY model
                    ORDER BY COUNT(*) DESC
                    """,
                    params,
                )
                traces_by_model = {
                    name: count for name, count in cur.fetchall() if name
                }

                cur.execute(
                    f"""
                    SELECT
                        CASE
                            WHEN success = TRUE THEN 'success'
                            WHEN COALESCE(error_message, '') ILIKE '%%timeout%%' THEN 'timeout'
                            ELSE 'error'
                        END AS status,
                        COUNT(*)
                    FROM llm_traces
                    WHERE {where_clause}
                    GROUP BY status
                    """,
                    params,
                )
                traces_by_status = {
                    status: count for status, count in cur.fetchall() if status
                }

                stats_result = {
                    "total_calls": total_calls,
                    "successful": successful,
                    "failed": failed,
                    "json_parse_failures": json_failures,
                    "avg_latency_ms": avg_latency_ms,
                    "max_latency_ms": max_latency_ms,
                    "unique_agents": unique_agents,
                    "unique_models": unique_models,
                    "total_traces": total_calls,
                    "total_tokens": total_tokens,
                    "total_cost_usd": round(total_cost_usd, 6),
                    "success_count": successful,
                    "error_count": failed,
                    "timeout_count": timeout_count,
                    "traces_by_agent": traces_by_agent,
                    "traces_by_model": traces_by_model,
                    "traces_by_status": traces_by_status,
                }
            _return_conn(conn)
            return stats_result
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            return _empty_trace_stats()
    except Exception as exc:
        logger.debug("llm_trace stats hatasi: %s", exc)
        return _empty_trace_stats(error=str(exc))
