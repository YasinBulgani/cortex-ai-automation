"""RBAC + Segregation of Duties — rol matrisi ve 4-göz politikaları.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §5 / E3.5 (P1).

Mimari:
    * Rol matrisi pure dict — runtime dep yok, test edilmesi kolay.
    * ``has_permission(user_perms, permission)`` — admin.* wildcard desteği,
      app.deps.require_permission ile uyumlu.
    * SoD politikaları: "aynı kullanıcı X aksiyonunu yapamaz if daha
      önce Y aksiyonunu yapmışsa" kuralları. Ör: "prompt yazan ≠ onaylayan".
    * AuditStore arayüzü protokol — gerçek audit_events tablosuna
      bağlanacak (E3.3 hash chain ile eşleşir); testte fake ile mock'lanır.

Kullanım:
    from app.domains.rbac.policy import enforce_sod, ROLES

    enforce_sod(
        audit_store=store,
        user_id=u.id,
        new_action="prompt.rollout.promote",
        resource_type="prompt",
        resource_id=prompt_id,
    )
    # SoDViolation raise ederse endpoint 403 döndürür
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Iterable, List, Optional, Protocol, Set, Tuple

logger = logging.getLogger(__name__)


# ── Rol matrisi ───────────────────────────────────────────────────────────


# Her rol → izin set'i. "admin.*" wildcard tüm admin.* izinleri kapsar.
# Composite: bir kullanıcı birden çok role sahip olabilir, izinler UNION alınır.
ROLES: Dict[str, Set[str]] = {
    "viewer": {
        "tspm.read",
        "ai.read",
        "coverup.read",
        "feature_flags.read",
    },
    "test_author": {
        "tspm.read",
        "tspm.write",
        "ai.read",
        "ai.generate",
        "coverup.read",
        "prompts.read",
        "feature_flags.read",
    },
    "reviewer": {
        "tspm.read",
        "tspm.approve",
        "prompts.read",
        "prompts.approve",
        "coverup.read",
        "coverup.heal.approve",
        "feature_flags.read",
    },
    "ops": {
        "tspm.read",
        "tspm.write",
        "tspm.deploy",
        "coverup.read",
        "coverup.heal.approve",
        "feature_flags.read",
        "feature_flags.write",
        "ai.read",
        "admin.evals",  # Eval suite koşumu operasyonel
    },
    "auditor": {
        "tspm.read",
        "ai.read",
        "coverup.read",
        "audit.read",
        "audit.verify",
        "feature_flags.read",
    },
    "admin": {
        "admin.*",
    },
}


def role_permissions(roles: Iterable[str]) -> Set[str]:
    """Birleşik izin kümesi."""
    out: Set[str] = set()
    for r in roles:
        out.update(ROLES.get(r, set()))
    return out


def has_permission(user_perms: Set[str], required: str) -> bool:
    """``admin.*`` wildcard desteği.

    ``admin.*`` herhangi bir izni karşılar (``deps.require_permission`` ile
    hizalı). Aksi halde exact match.
    """
    if "admin.*" in user_perms:
        return True
    return required in user_perms


# ── Segregation of Duties ────────────────────────────────────────────────


@dataclass(frozen=True)
class SoDRule:
    """Bir SoD kuralı.

    ``new_action`` yapılırken ``conflicting_actions`` listesinden herhangi
    biri aynı kullanıcı tarafından aynı kaynakta son ``window_days`` içinde
    yapılmışsa REDDEDİLİR.
    """

    name: str
    new_action: str
    conflicting_actions: Tuple[str, ...]
    window_days: int = 30
    scope: str = "resource"  # "resource" | "tenant" | "global"
    description: str = ""


# Temel SoD kuralları. Daha fazlası aynı şekilde eklenebilir.
SOD_RULES: Tuple[SoDRule, ...] = (
    SoDRule(
        name="prompt_author_vs_promoter",
        new_action="prompt.rollout.promote",
        conflicting_actions=("prompt.version.create",),
        window_days=30,
        scope="resource",
        description="Prompt yazan ≠ canary'den prod'a terfi eden",
    ),
    SoDRule(
        name="prompt_author_vs_approver",
        new_action="prompt.approve",
        conflicting_actions=("prompt.version.create",),
        window_days=30,
        scope="resource",
        description="Prompt yazan ≠ onaylayan",
    ),
    SoDRule(
        name="heal_author_vs_approver",
        new_action="coverup.heal.approve",
        conflicting_actions=("coverup.heal.create", "coverup.heal.propose"),
        window_days=7,
        scope="resource",
        description="Self-healing PR'ı üreten ≠ onaylayan",
    ),
    SoDRule(
        name="budget_set_vs_bypass",
        new_action="ai.budget.bypass",
        conflicting_actions=("ai.budget.set",),
        window_days=90,
        scope="tenant",
        description="Bütçe kuran ≠ bütçeyi bypass eden",
    ),
    SoDRule(
        name="feature_flag_author_vs_promote",
        new_action="feature_flag.promote",
        conflicting_actions=("feature_flag.create",),
        window_days=14,
        scope="resource",
        description="Feature flag oluşturan ≠ %100'e terfi eden",
    ),
)


def find_rules_for(action: str) -> List[SoDRule]:
    """Verilen ``new_action`` için geçerli kurallar."""
    return [r for r in SOD_RULES if r.new_action == action]


# ── Audit store arayüzü (DI) ──────────────────────────────────────────────


@dataclass(frozen=True)
class ActorAction:
    """AuditStore.actor_recent_actions sonucu — tek kayıt."""

    action: str
    resource_type: str
    resource_id: Optional[str]
    tenant_id: Optional[str]
    ts: datetime


class AuditStore(Protocol):
    """E3.3 audit_events tablosundan beslenecek arayüz.

    ``actor_recent_actions`` belirli bir aktörün belirli action'larını
    window içinde getirir. Scope'a göre resource_id veya tenant_id filter
    eklenir.
    """

    def actor_recent_actions(
        self,
        *,
        actor_user_id: str,
        actions: Tuple[str, ...],
        since: datetime,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
    ) -> List[ActorAction]:
        ...  # pragma: no cover - protocol


# ── Politika motor ────────────────────────────────────────────────────────


class SoDViolation(Exception):
    """Endpoint 403 ile yakalar."""

    def __init__(
        self,
        rule: SoDRule,
        conflicting: ActorAction,
    ) -> None:
        msg = (
            f"SoD ihlali: '{rule.name}' — bu aktör daha önce "
            f"'{conflicting.action}' yaptı (ts={conflicting.ts.isoformat()}). "
            f"Aynı kişi '{rule.new_action}' yapamaz."
        )
        super().__init__(msg)
        self.rule = rule
        self.conflicting = conflicting


def enforce_sod(
    *,
    audit_store: AuditStore,
    actor_user_id: str,
    new_action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    now: Optional[datetime] = None,
) -> None:
    """İhlalde ``SoDViolation`` raise. Temiz ise sessiz döner.

    Boş ``actor_user_id`` → raise (anonim aksiyon SoD kapsamında değil,
    ama kritik action'larda actor zorunlu).
    """
    if not actor_user_id:
        raise SoDViolation(
            rule=SoDRule(
                name="missing_actor",
                new_action=new_action,
                conflicting_actions=(),
            ),
            conflicting=ActorAction(
                action="", resource_type="", resource_id=None,
                tenant_id=None, ts=datetime.now(timezone.utc),
            ),
        )

    rules = find_rules_for(new_action)
    if not rules:
        return  # Bu action için SoD kuralı tanımlı değil

    now = now or datetime.now(timezone.utc)
    for rule in rules:
        since = now - timedelta(days=rule.window_days)
        # Scope'a göre filter ayarla
        rtype = resource_type if rule.scope == "resource" else None
        rid = resource_id if rule.scope == "resource" else None
        tid = tenant_id if rule.scope in ("resource", "tenant") else None

        recent = audit_store.actor_recent_actions(
            actor_user_id=actor_user_id,
            actions=rule.conflicting_actions,
            since=since,
            resource_type=rtype,
            resource_id=rid,
            tenant_id=tid,
        )
        if recent:
            # İlk çatışan kaydı raporla (en ilgilisi)
            raise SoDViolation(rule=rule, conflicting=recent[0])


# ── FastAPI helper ────────────────────────────────────────────────────────


def sod_http_detail(exc: SoDViolation) -> Dict[str, str]:
    """Router'dan 403 dönerken HTTP detail payload'u."""
    return {
        "error": "sod_violation",
        "rule": exc.rule.name,
        "message": str(exc),
        "conflicting_action": exc.conflicting.action,
        "conflicting_ts": exc.conflicting.ts.isoformat(),
    }
