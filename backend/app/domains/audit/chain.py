"""Audit hash chain — pure fonksiyonlar + append helper + verify.

Plan: docs/AI_OTOMASYON_GELISTIRME_PLANI.md §5 / E3.3.

Mimari:
    Her audit event SHA-256 imzalı. ``hash = sha256(prev_hash || canonical_payload)``.
    Genesis event prev_hash=None, hash=sha256(b'' || payload).
    Bir event'i değiştirmek → kendi hash'i değişir → sonraki tüm event'lerin
    prev_hash'i eşleşmez → verify tamper'i yakalar.

Canonical payload:
    * ts (ISO 8601 UTC microseconds)
    * tenant_id (normalize edilmiş string)
    * actor_user_id
    * action
    * resource_type
    * resource_id
    * payload (JSON, sort_keys=True, ensure_ascii=False)

Her alanı null-tolerant string'e çevir, tab separator, son newline.
Bu deterministiktir; aynı payload → aynı hash.

Pure / DB-bağımsız bölümler (hash/canonical/verify) test edilir.
DB append + verify_chain integration testi ileride (CI'da postgres).
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

logger = logging.getLogger(__name__)


GENESIS_PREV_HASH = ""  # İlk event için prev_hash boş string


@dataclass
class ChainEvent:
    """Hash hesabı için minimum payload.

    DB modelinin (AuditEvent) alanlarıyla 1:1 değil — sadece hash'e giren
    alanları içerir. ``seq`` sorgu sonrası eşleştirme için saklanır.
    """

    ts: datetime
    tenant_id: Optional[str]
    actor_user_id: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    payload: Optional[Dict[str, Any]] = None
    seq: Optional[int] = None
    prev_hash: Optional[str] = None
    hash: Optional[str] = None


def _iso_ts(ts: datetime) -> str:
    """Zaman damgasını deterministik ISO 8601 UTC string'e çevir."""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    # Microsecond içerir: "2026-04-19T21:30:45.123456+00:00"
    return ts.isoformat()


def _json_canonical(payload: Optional[Dict[str, Any]]) -> str:
    if payload is None:
        return ""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def canonical_payload(event: ChainEvent) -> str:
    """Event → deterministik string. Hash input'u budur."""
    parts = [
        _iso_ts(event.ts),
        event.tenant_id or "",
        event.actor_user_id or "",
        event.action,
        event.resource_type,
        event.resource_id or "",
        _json_canonical(event.payload),
    ]
    return "\t".join(parts) + "\n"


def compute_hash(prev_hash: Optional[str], event: ChainEvent) -> str:
    """SHA-256 hex string."""
    h = hashlib.sha256()
    h.update((prev_hash or GENESIS_PREV_HASH).encode("utf-8"))
    h.update(canonical_payload(event).encode("utf-8"))
    return h.hexdigest()


# ── Chain verify ─────────────────────────────────────────────────────────


@dataclass
class VerifyResult:
    ok: bool
    total: int
    verified: int
    first_bad_seq: Optional[int] = None
    errors: List[str] = field(default_factory=list)


def verify_chain(events: Sequence[ChainEvent]) -> VerifyResult:
    """Zinciri kronolojik (seq ASC) sırayla doğrula.

    Her event için beklenen hash = compute_hash(prev_event.hash, event).
    İlk uyumsuzlukta durur; errors listesinde detay verir.
    """
    if not events:
        return VerifyResult(ok=True, total=0, verified=0)

    # Sıralamayı garanti altına al
    ordered = sorted(events, key=lambda e: (e.seq if e.seq is not None else -1))

    errors: List[str] = []
    prev_hash: Optional[str] = None
    verified = 0
    first_bad: Optional[int] = None

    for ev in ordered:
        if ev.hash is None or ev.seq is None:
            # Legacy kayıt — chain dışı, skip (sequence durur, sonrası güvenilmez)
            errors.append(
                f"seq={ev.seq} legacy (hash/seq null) — zincir burada kesilir"
            )
            if first_bad is None:
                first_bad = ev.seq
            break

        expected = compute_hash(prev_hash, ev)
        if ev.hash != expected:
            errors.append(
                f"seq={ev.seq} hash uyumsuz: beklenen={expected[:12]} gerçek={ev.hash[:12]}"
            )
            if first_bad is None:
                first_bad = ev.seq
            break

        if (ev.prev_hash or None) != (prev_hash or None):
            errors.append(
                f"seq={ev.seq} prev_hash uyumsuz: beklenen={(prev_hash or '')[:12]} gerçek={(ev.prev_hash or '')[:12]}"
            )
            if first_bad is None:
                first_bad = ev.seq
            break

        prev_hash = ev.hash
        verified += 1

    return VerifyResult(
        ok=verified == len(ordered),
        total=len(ordered),
        verified=verified,
        first_bad_seq=first_bad,
        errors=errors,
    )


# ── DB append (raw SQL — AuditEvent modeline dokunmadan) ────────────────


def append_event(
    *,
    tenant_id: Optional[str],
    actor_user_id: Optional[str],
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    ts: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Yeni audit event ekle, hash chain'e bağla.

    Return: {id, seq, hash, prev_hash, ts}

    Thread/process safety:
        Postgres per-tenant row-level lock ile seq monotonik. Aynı anda
        iki append'de yarış durumu ``UNIQUE (tenant_id, seq)`` partial
        index tarafından yakalanır; yarış kaybeden retry edebilir.
    """
    from app.domains.ai.llm_trace import _get_conn  # type: ignore

    ev_ts = ts or datetime.now(timezone.utc)
    ev = ChainEvent(
        ts=ev_ts,
        tenant_id=tenant_id,
        actor_user_id=actor_user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        payload=payload,
    )

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            # Bu tenant için son chain tail'i al (row-level lock)
            # NOT: Tablo adı ``sd_audit_events`` (migration audit_chain_bind_0001
            # ile hash-chain kolonları eklendi). Eski ``audit_events`` tablosu
            # hiç CREATE edilmemişti.
            cur.execute(
                """
                SELECT hash, seq
                FROM sd_audit_events
                WHERE (%s::VARCHAR IS NULL AND tenant_id IS NULL OR tenant_id = %s)
                  AND seq IS NOT NULL
                ORDER BY seq DESC LIMIT 1
                FOR UPDATE
                """,
                (tenant_id, tenant_id),
            )
            tail = cur.fetchone()
            prev_hash = tail[0] if tail else GENESIS_PREV_HASH
            next_seq = (int(tail[1]) + 1) if tail else 1

            ev.prev_hash = prev_hash
            ev.seq = next_seq
            ev.hash = compute_hash(prev_hash, ev)

            # payload DB'ye JSONB olarak gider. ``sd_audit_events.id`` NOT NULL
            # ama DB-side default yok (ORM-side default=_uuid). Raw SQL path
            # olduğu için Python tarafında UUID üretiyoruz.
            event_id = str(uuid.uuid4())
            cur.execute(
                """
                INSERT INTO sd_audit_events
                    (id, actor_user_id, action, resource_type, resource_id,
                     payload, ts, tenant_id, seq, prev_hash, hash)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                RETURNING id, ts
                """,
                (
                    event_id,
                    actor_user_id,
                    action,
                    resource_type,
                    resource_id,
                    json.dumps(payload) if payload else None,
                    ev_ts,
                    tenant_id,
                    next_seq,
                    prev_hash if prev_hash != GENESIS_PREV_HASH else None,
                    ev.hash,
                ),
            )
            row = cur.fetchone()
        conn.commit()
    finally:
        conn.close()

    return {
        "id": row[0] if row else None,
        "ts": row[1].isoformat() if row else ev_ts.isoformat(),
        "seq": next_seq,
        "hash": ev.hash,
        "prev_hash": ev.prev_hash or None,
    }


def load_chain(tenant_id: Optional[str], limit: int = 1000) -> List[ChainEvent]:
    from app.domains.ai.llm_trace import _get_conn  # type: ignore

    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT ts, tenant_id, actor_user_id, action, resource_type,
                       resource_id, payload, seq, prev_hash, hash
                FROM sd_audit_events
                WHERE (%s::VARCHAR IS NULL AND tenant_id IS NULL OR tenant_id = %s)
                ORDER BY seq ASC NULLS LAST
                LIMIT %s
                """,
                (tenant_id, tenant_id, limit),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    out: List[ChainEvent] = []
    for r in rows:
        out.append(
            ChainEvent(
                ts=r[0],
                tenant_id=r[1],
                actor_user_id=r[2],
                action=r[3],
                resource_type=r[4],
                resource_id=r[5],
                payload=r[6] if isinstance(r[6], dict) else (json.loads(r[6]) if r[6] else None),
                seq=int(r[7]) if r[7] is not None else None,
                prev_hash=r[8],
                hash=r[9],
            )
        )
    return out
