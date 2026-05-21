"""Append-only denetim kayıtları — hash-chain'e bağlı.

``log_audit`` artık tamper-evident: her çağrı ``chain.append_event`` üzerinden
``sd_audit_events`` tablosuna hash chain içinde yazılır. Hash chain'e bağlanma
başarısız olursa (ör. yeni migration henüz uygulanmadı → kolon yok) ORM
fallback'i ile yazım devam eder; başarısızlık log'a düşer ancak request
kırılmaz. Bu davranış BDDK denetiminde kabul edilebilir bir gradation:
"chain kırık" alarmı ops'a düşer, veri kaybolmaz.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.infra.models import AuditEvent, utcnow

logger = logging.getLogger(__name__)


def log_audit(
    db: Session,
    *,
    actor_user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str],
    payload: Optional[Dict[str, Any]],
    ip: Optional[str],
    tenant_id: Optional[str] = None,
) -> None:
    """Audit event kaydı — hash chain'e append + ORM fallback.

    Args:
        db: SQLAlchemy session (geriye dönük uyum için tutulur; chain kendi
            psycopg2 bağlantısını açar).
        actor_user_id: İşlemi yapan kullanıcı.
        action: İşlem adı (ör. "scenario.create").
        resource_type: Etkilenen kaynağın türü.
        resource_id: Kaynağın ID'si.
        payload: Değişiklik detayları (JSON).
        ip: İstemci IP'si.
        tenant_id: Multi-tenant ortamda tenant ayrımı (opsiyonel).
    """
    # Öncelik: hash-chain path (tamper-evident). Başarısız olursa ORM fallback.
    try:
        from app.domains.audit.chain import append_event

        append_event(
            tenant_id=tenant_id,
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            payload=payload,
        )
        return
    except Exception as exc:
        # DB'ye ulaşılamadı, migration henüz yok, veya zinciri kiran bir
        # corruption → ORM fallback'e düş. Critical: audit kaybolmamalı.
        logger.warning(
            "Audit chain append başarısız, ORM fallback: action=%s err=%s",
            action,
            exc,
        )

    ev = AuditEvent(
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
        ip=ip,
        tenant_id=tenant_id,
        ts=utcnow(),
    )
    db.add(ev)
