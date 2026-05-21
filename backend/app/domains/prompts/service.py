"""Prompts service — CRUD + versiyon ekleme + resolve (canary/active).

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §3 / E1.3.

Tasarım kararları:
    * Raw psycopg2 + ``llm_trace._get_conn`` pattern'i (projede ikinci DB
      stil olarak kabul edilmiş; SQLAlchemy ORM'e yeniden yazma dışı).
    * ``resolve()`` caller'ın sıcak yolu: tek roundtrip ile
      (version + template + rollout). Prompt registry cache'lenebilir ama
      önce doğru çalışsın, sonra optimize — production load < 1 req/s/prompt
      ortalamasında cache gereksiz.
    * Canary resolve'de versiyon eksik/bozuk → ``active`` fallback
      (``decision_reason='fallback_active'``). Canary kırık PR'ı prod'u
      düşürmesin.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional, Tuple

from .canary import should_canary
from .schemas import (
    Env,
    PromptIn,
    PromptOut,
    PromptVersionIn,
    PromptVersionOut,
    ResolvedPrompt,
    RolloutIn,
    RolloutOut,
)

logger = logging.getLogger(__name__)


def _get_conn():
    from app.domains.ai.llm_trace import _get_conn as _base_conn  # type: ignore

    return _base_conn()


# ── Prompt (meta) ─────────────────────────────────────────────────────────


def list_prompts(include_archived: bool = False) -> List[PromptOut]:
    try:
        conn = _get_conn()
    except Exception as exc:
        logger.warning("prompts.list: DB yok (%s)", exc)
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.description, p.task_type, p.archived,
                       p.created_at, p.created_by, p.updated_at,
                       (SELECT MAX(version) FROM prompt_versions v WHERE v.prompt_id = p.id)
                FROM prompts p
                WHERE (%s OR p.archived = FALSE)
                ORDER BY p.id ASC
                """,
                (include_archived,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_prompt_out(r) for r in rows]


def get_prompt(prompt_id: str) -> Optional[PromptOut]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.description, p.task_type, p.archived,
                       p.created_at, p.created_by, p.updated_at,
                       (SELECT MAX(version) FROM prompt_versions v WHERE v.prompt_id = p.id)
                FROM prompts p WHERE p.id = %s
                """,
                (prompt_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return _row_to_prompt_out(row) if row else None


def upsert_prompt(
    prompt_id: str, payload: PromptIn, *, actor: Optional[str] = None
) -> PromptOut:
    if not prompt_id or not prompt_id.strip():
        raise ValueError("prompt_id boş olamaz")
    prompt_id = prompt_id.strip()

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO prompts
                    (id, description, task_type, created_at, created_by, updated_at)
                VALUES (%s, %s, %s, now(), %s, now())
                ON CONFLICT (id) DO UPDATE SET
                    description = EXCLUDED.description,
                    task_type   = EXCLUDED.task_type,
                    updated_at  = now()
                RETURNING id, description, task_type, archived,
                          created_at, created_by, updated_at
                """,
                (prompt_id, payload.description, payload.task_type, actor),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    # latest_version NULL olabilir — ayrı sorguya gerek yok, ilk upsert sonrası 0 satır
    if row is None:
        raise RuntimeError("prompts upsert satır dönmedi")
    return PromptOut(
        id=row[0],
        description=row[1] or "",
        task_type=row[2],
        archived=bool(row[3]),
        created_at=row[4],
        created_by=row[5],
        updated_at=row[6],
        latest_version=None,
    )


def archive_prompt(prompt_id: str, archived: bool = True) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE prompts SET archived = %s, updated_at = now() WHERE id = %s",
                (archived, prompt_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


# ── Versiyon ──────────────────────────────────────────────────────────────


def add_version(
    prompt_id: str, payload: PromptVersionIn, *, actor: Optional[str] = None
) -> PromptVersionOut:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Monotonik version — mevcut max + 1 (race için UNIQUE + retry mümkün)
            cur.execute(
                "SELECT COALESCE(MAX(version), 0) FROM prompt_versions WHERE prompt_id = %s",
                (prompt_id,),
            )
            next_version = int((cur.fetchone() or [0])[0] or 0) + 1

            cur.execute(
                """
                INSERT INTO prompt_versions
                    (prompt_id, version, system_prompt, user_template,
                     model_hint, temperature, max_tokens, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, prompt_id, version, system_prompt, user_template,
                          model_hint, temperature, max_tokens, notes,
                          created_at, created_by
                """,
                (
                    prompt_id,
                    next_version,
                    payload.system_prompt,
                    payload.user_template,
                    payload.model_hint,
                    payload.temperature,
                    payload.max_tokens,
                    payload.notes,
                    actor,
                ),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    return _row_to_version_out(row)


def get_version(prompt_id: str, version: int) -> Optional[PromptVersionOut]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, prompt_id, version, system_prompt, user_template,
                       model_hint, temperature, max_tokens, notes,
                       created_at, created_by
                FROM prompt_versions
                WHERE prompt_id = %s AND version = %s
                """,
                (prompt_id, version),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return _row_to_version_out(row) if row else None


def list_versions(prompt_id: str, limit: int = 100) -> List[PromptVersionOut]:
    limit = max(1, min(limit, 500))
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, prompt_id, version, system_prompt, user_template,
                       model_hint, temperature, max_tokens, notes,
                       created_at, created_by
                FROM prompt_versions
                WHERE prompt_id = %s
                ORDER BY version DESC
                LIMIT %s
                """,
                (prompt_id, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_version_out(r) for r in rows]


# ── Rollout ──────────────────────────────────────────────────────────────


def get_rollout(prompt_id: str, env: Env = "prod") -> Optional[RolloutOut]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT prompt_id, env, active_version, canary_version, canary_pct,
                       updated_at, updated_by
                FROM prompt_rollouts
                WHERE prompt_id = %s AND env = %s
                """,
                (prompt_id, env),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    return _row_to_rollout_out(row) if row else None


def list_rollouts(prompt_id: str) -> List[RolloutOut]:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT prompt_id, env, active_version, canary_version, canary_pct,
                       updated_at, updated_by
                FROM prompt_rollouts
                WHERE prompt_id = %s
                ORDER BY env
                """,
                (prompt_id,),
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    return [_row_to_rollout_out(r) for r in rows]


def upsert_rollout(
    prompt_id: str,
    env: Env,
    payload: RolloutIn,
    *,
    actor: Optional[str] = None,
) -> RolloutOut:
    # Validasyon: active_version gerçekten var mı?
    if get_version(prompt_id, payload.active_version) is None:
        raise ValueError(
            f"active_version={payload.active_version} mevcut değil"
        )
    if payload.canary_version is not None:
        if get_version(prompt_id, payload.canary_version) is None:
            raise ValueError(
                f"canary_version={payload.canary_version} mevcut değil"
            )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO prompt_rollouts
                    (prompt_id, env, active_version, canary_version, canary_pct,
                     updated_at, updated_by)
                VALUES (%s, %s, %s, %s, %s, now(), %s)
                ON CONFLICT (prompt_id, env) DO UPDATE SET
                    active_version  = EXCLUDED.active_version,
                    canary_version  = EXCLUDED.canary_version,
                    canary_pct      = EXCLUDED.canary_pct,
                    updated_at      = now(),
                    updated_by      = EXCLUDED.updated_by
                RETURNING prompt_id, env, active_version, canary_version, canary_pct,
                          updated_at, updated_by
                """,
                (
                    prompt_id,
                    env,
                    payload.active_version,
                    payload.canary_version,
                    payload.canary_pct,
                    actor,
                ),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    return _row_to_rollout_out(row)


# ── Resolve (caller sıcak yolu) ───────────────────────────────────────────


def resolve(
    prompt_id: str,
    *,
    tenant_id: Optional[str] = None,
    env: Env = "prod",
) -> Optional[ResolvedPrompt]:
    """Bir çağrı için çözülmüş prompt (versiyon + gövde + karar).

    Dönüş ``None`` sadece prompt yoksa VEYA hiç versiyonu yoksa.
    """
    rollout = get_rollout(prompt_id, env)
    if rollout is None:
        # Rollout henüz kurulmadıysa en son versiyon aktif kabul edilir
        versions = list_versions(prompt_id, limit=1)
        if not versions:
            return None
        v = versions[0]
        return ResolvedPrompt(
            prompt_id=prompt_id,
            env=env,
            version=v.version,
            system_prompt=v.system_prompt,
            user_template=v.user_template,
            model_hint=v.model_hint,
            temperature=v.temperature,
            max_tokens=v.max_tokens,
            decision_reason="active",  # default — "no_rollout"den ayırt etme şimdilik yok
            active_version=v.version,
            canary_version=None,
            canary_pct=0,
        )

    # Rollout var — canary kararı
    use_canary = False
    if rollout.canary_version is not None and rollout.canary_pct > 0:
        use_canary = should_canary(tenant_id, prompt_id, rollout.canary_pct)

    chosen_version = rollout.canary_version if use_canary else rollout.active_version
    reason = "canary_percent" if use_canary else "active"
    assert chosen_version is not None  # canary True → canary_version not None garantisi

    v = get_version(prompt_id, chosen_version)
    if v is None:
        # Canary versiyonu silinmiş veya kayıt bozuk → active'e fallback
        if use_canary:
            v = get_version(prompt_id, rollout.active_version)
            reason = "fallback_active"
        if v is None:
            logger.warning(
                "prompts.resolve: %s env=%s active_version=%s mevcut değil",
                prompt_id,
                env,
                rollout.active_version,
            )
            return None

    return ResolvedPrompt(
        prompt_id=prompt_id,
        env=env,
        version=v.version,
        system_prompt=v.system_prompt,
        user_template=v.user_template,
        model_hint=v.model_hint,
        temperature=v.temperature,
        max_tokens=v.max_tokens,
        decision_reason=reason,
        active_version=rollout.active_version,
        canary_version=rollout.canary_version,
        canary_pct=rollout.canary_pct,
    )


# ── Row mapping yardımcıları ──────────────────────────────────────────────


def _row_to_prompt_out(row) -> PromptOut:
    return PromptOut(
        id=row[0],
        description=row[1] or "",
        task_type=row[2],
        archived=bool(row[3]),
        created_at=row[4],
        created_by=row[5],
        updated_at=row[6],
        latest_version=int(row[7]) if row[7] is not None else None,
    )


def _row_to_version_out(row) -> PromptVersionOut:
    return PromptVersionOut(
        id=int(row[0]),
        prompt_id=row[1],
        version=int(row[2]),
        system_prompt=row[3] or "",
        user_template=row[4] or "",
        model_hint=row[5],
        temperature=float(row[6]) if row[6] is not None else None,
        max_tokens=int(row[7]) if row[7] is not None else None,
        notes=row[8],
        created_at=row[9],
        created_by=row[10],
    )


def _row_to_rollout_out(row) -> RolloutOut:
    return RolloutOut(
        prompt_id=row[0],
        env=row[1],
        active_version=int(row[2]),
        canary_version=int(row[3]) if row[3] is not None else None,
        canary_pct=int(row[4] or 0),
        updated_at=row[5],
        updated_by=row[6],
    )
