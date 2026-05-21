"""AI bütçe politikaları — tenant bazlı günlük cap + check.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §3 / E1.2.

Semantik:
    * ``BudgetPolicy`` = per-tenant, tek satır. ``daily_cap_usd=0`` → limit yok.
    * ``check_budget(tenant_id)``:
        - Politika yok veya cap=0 → BudgetStatus(allowed=True, reason='no_policy')
        - Bugünkü (UTC) kullanım < cap*notify_at_pct/100 → allowed, 'ok'
        - notify eşiği < kullanım < cap → allowed, 'approaching' (soft alarm)
        - kullanım >= cap AND hard_cap=True → allowed=False, 'hard_cap'
        - kullanım >= cap AND hard_cap=False → allowed=True, 'over_cap'
          (log + metric, ama geçer — finansal sürpriz önler ama hizmet kesmez)

Feature flag:
    ``ai.budget.enforce`` (feature_flags) kapalıysa check her zaman allowed
    döner (politikalar incelenmez). Bu sayede rollout kontrolü operator'de.

``usage_today_usd`` güncel harcama için ``usage_service.get_tenant_today_cost``
sorar — bu fonksiyon llm_traces'ten hesaplar (materialized view yok,
~günlük ~10K kayıt için doğrudan SUM performansı yeter).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class BudgetPolicyIn(BaseModel):
    """Upsert için request body."""

    daily_cap_usd: float = Field(ge=0)
    hard_cap: bool = False
    notify_at_pct: int = Field(default=80, ge=1, le=100)
    notes: Optional[str] = None

    @field_validator("daily_cap_usd")
    @classmethod
    def _round(cls, v: float) -> float:
        return round(float(v), 6)


class BudgetPolicyOut(BaseModel):
    tenant_id: str
    daily_cap_usd: float
    hard_cap: bool
    notify_at_pct: int
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str] = None


@dataclass(frozen=True)
class BudgetStatus:
    allowed: bool
    reason: str  # 'no_policy' | 'ok' | 'approaching' | 'over_cap' | 'hard_cap' | 'disabled'
    today_usd: float
    daily_cap_usd: float
    notify_at_pct: int
    hard_cap: bool

    def pct_used(self) -> float:
        if self.daily_cap_usd <= 0:
            return 0.0
        return round(100.0 * self.today_usd / self.daily_cap_usd, 2)


def _today_utc_bounds() -> tuple[datetime, datetime]:
    """[00:00 bugün UTC, 00:00 yarın UTC) aralığı."""
    now = datetime.now(timezone.utc)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    # 24h eklemek için timedelta (import et)
    from datetime import timedelta

    return start, start + timedelta(days=1)


def _get_conn():
    """Yeni psycopg2 bağlantısı — llm_trace.py pattern'i."""
    from .llm_trace import _get_conn as _base_conn  # type: ignore

    return _base_conn()


# ── CRUD ─────────────────────────────────────────────────────────────────


def list_policies() -> List[BudgetPolicyOut]:
    try:
        conn = _get_conn()
    except Exception as exc:
        logger.warning("budget.list_policies: DB bağlantısı yok (%s)", exc)
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tenant_id, daily_cap_usd, hard_cap, notify_at_pct,
                       notes, created_at, updated_at, updated_by
                FROM ai_budget_policies
                ORDER BY tenant_id
                """
            )
            rows = cur.fetchall()
        return [
            BudgetPolicyOut(
                tenant_id=r[0],
                daily_cap_usd=float(r[1]),
                hard_cap=bool(r[2]),
                notify_at_pct=int(r[3]),
                notes=r[4],
                created_at=r[5],
                updated_at=r[6],
                updated_by=r[7],
            )
            for r in rows
        ]
    finally:
        conn.close()


def get_policy(tenant_id: str) -> Optional[BudgetPolicyOut]:
    if not tenant_id:
        return None
    try:
        conn = _get_conn()
    except Exception as exc:
        logger.warning("budget.get_policy: DB bağlantısı yok (%s)", exc)
        return None
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT tenant_id, daily_cap_usd, hard_cap, notify_at_pct,
                       notes, created_at, updated_at, updated_by
                FROM ai_budget_policies
                WHERE tenant_id = %s
                """,
                (tenant_id,),
            )
            row = cur.fetchone()
        if not row:
            return None
        return BudgetPolicyOut(
            tenant_id=row[0],
            daily_cap_usd=float(row[1]),
            hard_cap=bool(row[2]),
            notify_at_pct=int(row[3]),
            notes=row[4],
            created_at=row[5],
            updated_at=row[6],
            updated_by=row[7],
        )
    finally:
        conn.close()


def upsert_policy(
    tenant_id: str,
    policy: BudgetPolicyIn,
    *,
    actor: Optional[str] = None,
) -> BudgetPolicyOut:
    if not tenant_id or not tenant_id.strip():
        raise ValueError("tenant_id boş olamaz")
    tenant_id = tenant_id.strip()

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO ai_budget_policies
                    (tenant_id, daily_cap_usd, hard_cap, notify_at_pct, notes,
                     created_at, updated_at, updated_by)
                VALUES (%s, %s, %s, %s, %s, now(), now(), %s)
                ON CONFLICT (tenant_id) DO UPDATE SET
                    daily_cap_usd = EXCLUDED.daily_cap_usd,
                    hard_cap       = EXCLUDED.hard_cap,
                    notify_at_pct  = EXCLUDED.notify_at_pct,
                    notes          = EXCLUDED.notes,
                    updated_at     = now(),
                    updated_by     = EXCLUDED.updated_by
                RETURNING tenant_id, daily_cap_usd, hard_cap, notify_at_pct,
                          notes, created_at, updated_at, updated_by
                """,
                (
                    tenant_id,
                    policy.daily_cap_usd,
                    policy.hard_cap,
                    policy.notify_at_pct,
                    policy.notes,
                    actor,
                ),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None
    return BudgetPolicyOut(
        tenant_id=row[0],
        daily_cap_usd=float(row[1]),
        hard_cap=bool(row[2]),
        notify_at_pct=int(row[3]),
        notes=row[4],
        created_at=row[5],
        updated_at=row[6],
        updated_by=row[7],
    )


def delete_policy(tenant_id: str) -> bool:
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM ai_budget_policies WHERE tenant_id = %s",
                (tenant_id,),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


# ── Check ───────────────────────────────────────────────────────────────


def _budget_enforcement_enabled(tenant_id: str) -> bool:
    """Feature flag ``ai.budget.enforce`` — kapalıysa check pasif."""
    try:
        from app.domains.feature_flags.service import feature_flags

        # Default False (fail-open): rollout operatör tarafından yönetilsin
        return feature_flags.is_enabled(
            "ai.budget.enforce", tenant_id=tenant_id, default=False
        )
    except Exception as exc:  # pragma: no cover - import guard
        logger.debug("budget: feature_flag check hata, disabled say: %s", exc)
        return False


def check_budget(
    tenant_id: str,
    *,
    additional_cost_usd: float = 0.0,
) -> BudgetStatus:
    """Tenant için bütçe karar fonksiyonu.

    ``additional_cost_usd`` henüz kaydedilmemiş bir çağrının beklenen maliyeti —
    proaktif blok için (estimate). Varsayılan 0: post-hoc check.
    """
    if not tenant_id:
        return BudgetStatus(
            allowed=True,
            reason="no_policy",
            today_usd=0.0,
            daily_cap_usd=0.0,
            notify_at_pct=0,
            hard_cap=False,
        )

    if not _budget_enforcement_enabled(tenant_id):
        return BudgetStatus(
            allowed=True,
            reason="disabled",
            today_usd=0.0,
            daily_cap_usd=0.0,
            notify_at_pct=0,
            hard_cap=False,
        )

    policy = get_policy(tenant_id)
    if not policy or policy.daily_cap_usd <= 0:
        return BudgetStatus(
            allowed=True,
            reason="no_policy",
            today_usd=0.0,
            daily_cap_usd=0.0,
            notify_at_pct=0,
            hard_cap=False,
        )

    # Lazy import — usage_service DB'ye gidiyor, import cycle olmasın diye burada
    from .usage_service import get_tenant_today_cost

    today_spent = get_tenant_today_cost(tenant_id)
    projected = today_spent + max(0.0, additional_cost_usd)
    notify_threshold = policy.daily_cap_usd * (policy.notify_at_pct / 100.0)

    if projected < notify_threshold:
        reason = "ok"
        allowed = True
    elif projected < policy.daily_cap_usd:
        reason = "approaching"
        allowed = True
    elif policy.hard_cap:
        reason = "hard_cap"
        allowed = False
    else:
        reason = "over_cap"
        allowed = True

    return BudgetStatus(
        allowed=allowed,
        reason=reason,
        today_usd=round(today_spent, 6),
        daily_cap_usd=policy.daily_cap_usd,
        notify_at_pct=policy.notify_at_pct,
        hard_cap=policy.hard_cap,
    )
