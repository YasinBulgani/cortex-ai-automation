"""Service layer for M-50 Threaded Comments + M-45 Notification Inbox.

HTTP-agnostic helpers backing ``/comments`` and ``/notifications`` endpoints.
Raises ``ValueError`` (→ 400 / 403) or ``KeyError`` (→ 404) — never
``HTTPException`` — so this module remains framework-independent.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Optional

from sqlalchemy import select, func, update
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

ALLOWED_NOTIFICATION_CHANNELS: set[str] = {"in_app", "email", "push", "slack", "teams"}

from app.domains.test_management.models import (
    DEFAULT_TENANT_ID,
    MgmtComment,
    MgmtNotification,
    TestManagementAuditEvent,
    utcnow,
)
from app.domains.test_management.schemas import (
    ALLOWED_COMMENT_ENTITY_TYPES,
    ALLOWED_NOTIFICATION_KINDS,
    MgmtCommentCreate,
    MgmtCommentReact,
    MgmtCommentUpdate,
    MgmtNotificationCreate,
)
from app.config import settings
from app.services.email_service import send_email, EmailMessageData
from app.services.notification_delivery import send_notification


# ── helpers ──────────────────────────────────────────────────────────────────

_MENTION_RE = re.compile(r"@([0-9a-fA-F-]{36})")
_UUID_RE = re.compile(r"^[0-9a-fA-F-]{36}$")


def _actor(user: Any | None) -> Optional[str]:
    if user is None:
        return None
    val = getattr(user, "id", None)
    return str(val) if val else None


def _tenant_for(user: Any | None) -> str:
    if user is None:
        return DEFAULT_TENANT_ID
    val = getattr(user, "tenant_id", None)
    return str(val) if val else DEFAULT_TENANT_ID


def parse_mentions(body_md: str, explicit: list[str] | None = None) -> list[str]:
    """Return a de-duplicated, ordered list of mentioned user UUIDs.

    Combines explicit ``mentions`` payload values with any inline
    ``@<uuid>`` patterns parsed from the markdown body.
    """
    found: list[str] = []
    seen: set[str] = set()
    for raw in (explicit or []):
        if not raw:
            continue
        candidate = str(raw)
        if not _UUID_RE.match(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        found.append(candidate)
    for match in _MENTION_RE.findall(body_md or ""):
        if match in seen:
            continue
        seen.add(match)
        found.append(match)
    return found


def _audit(
    db: Session,
    *,
    action: str,
    entity_type: str,
    entity_id: str | None,
    project_id: str | None,
    user: Any | None,
    payload: dict[str, Any] | None = None,
) -> None:
    db.add(
        TestManagementAuditEvent(
            project_id=project_id,
            actor_id=_actor(user),
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )


# ── Comments ─────────────────────────────────────────────────────────────────


def _serialize_comment(c: MgmtComment) -> dict[str, Any]:
    return {
        "id": c.id,
        "tenant_id": c.tenant_id,
        "project_id": c.project_id,
        "entity_type": c.entity_type,
        "entity_id": c.entity_id,
        "author_id": c.author_id,
        "parent_id": c.parent_id,
        "body_md": "" if c.deleted_at else c.body_md,
        "mentions": list(c.mentions or []),
        "reactions": dict(c.reactions or {}),
        "edited_at": c.edited_at,
        "deleted_at": c.deleted_at,
        "created_at": c.created_at,
    }


def create_comment(
    db: Session,
    payload: MgmtCommentCreate,
    user: Any,
) -> MgmtComment:
    if payload.entity_type not in ALLOWED_COMMENT_ENTITY_TYPES:
        raise ValueError("entity_type not allowed")

    parent: Optional[MgmtComment] = None
    if payload.parent_id:
        parent = db.get(MgmtComment, payload.parent_id)
        if parent is None or parent.deleted_at is not None:
            raise KeyError("Parent comment bulunamadı")
        if parent.entity_type != payload.entity_type or parent.entity_id != payload.entity_id:
            raise ValueError("Parent comment farklı bir entity'ye ait")

    mentions = parse_mentions(payload.body_md, payload.mentions)
    comment = MgmtComment(
        tenant_id=_tenant_for(user),
        project_id=payload.project_id,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        author_id=_actor(user),
        parent_id=payload.parent_id,
        body_md=payload.body_md,
        mentions=mentions,
        reactions={},
    )
    db.add(comment)
    db.flush()

    # Fan-out notifications.
    author_id = _actor(user)
    for mentioned in mentions:
        if mentioned == author_id:
            continue
        _create_notification(
            db,
            user_id=mentioned,
            kind="mention",
            title="Bir yorumda etiketlendiniz",
            body=_excerpt(payload.body_md),
            link_path=_link_for(payload.entity_type, payload.entity_id, payload.project_id),
            severity="info",
            project_id=payload.project_id,
            tenant_id=comment.tenant_id,
            source_trace={
                "comment_id": comment.id,
                "entity_type": comment.entity_type,
                "entity_id": comment.entity_id,
                "actor_id": author_id,
            },
        )

    if parent is not None and parent.author_id and parent.author_id != author_id and parent.author_id not in mentions:
        _create_notification(
            db,
            user_id=parent.author_id,
            kind="comment_reply",
            title="Yorumunuza yanıt geldi",
            body=_excerpt(payload.body_md),
            link_path=_link_for(payload.entity_type, payload.entity_id, payload.project_id),
            severity="info",
            project_id=payload.project_id,
            tenant_id=comment.tenant_id,
            source_trace={
                "comment_id": comment.id,
                "parent_comment_id": parent.id,
                "actor_id": author_id,
            },
        )

    _audit(
        db,
        action="comment.create",
        entity_type="mgmt_comment",
        entity_id=comment.id,
        project_id=payload.project_id,
        user=user,
        payload={
            "target_entity_type": payload.entity_type,
            "target_entity_id": payload.entity_id,
            "parent_id": payload.parent_id,
            "mentions": mentions,
        },
    )

    db.commit()
    db.refresh(comment)
    return comment


def list_comments(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    include_deleted: bool = False,
    tenant_id: Optional[str] = None,
) -> list[MgmtComment]:
    if entity_type not in ALLOWED_COMMENT_ENTITY_TYPES:
        raise ValueError("entity_type not allowed")
    if tenant_id is None:
        # Hardening — passing None used to return rows across all tenants;
        # the router now resolves a tenant via _require_tenant() so reaching
        # this branch indicates a programming error and we refuse to leak data.
        raise ValueError("tenant_id required")
    stmt = select(MgmtComment).where(
        MgmtComment.entity_type == entity_type,
        MgmtComment.entity_id == entity_id,
        MgmtComment.tenant_id == tenant_id,
    )
    if not include_deleted:
        stmt = stmt.where(MgmtComment.deleted_at.is_(None))
    stmt = stmt.order_by(MgmtComment.created_at.asc())
    return list(db.scalars(stmt).all())


def get_comment(db: Session, comment_id: str) -> MgmtComment:
    c = db.get(MgmtComment, comment_id)
    if c is None:
        raise KeyError("Comment bulunamadı")
    return c


def update_comment(
    db: Session,
    comment_id: str,
    payload: MgmtCommentUpdate,
    user: Any,
) -> MgmtComment:
    c = get_comment(db, comment_id)
    if c.deleted_at is not None:
        raise ValueError("Silinmiş yorum düzenlenemez")
    actor_id = _actor(user)
    if c.author_id != actor_id:
        raise ValueError("Sadece yazar düzenleyebilir")
    c.body_md = payload.body_md
    new_mentions = parse_mentions(payload.body_md, payload.mentions if payload.mentions is not None else list(c.mentions or []))
    c.mentions = new_mentions
    c.edited_at = utcnow()
    _audit(
        db,
        action="comment.update",
        entity_type="mgmt_comment",
        entity_id=c.id,
        project_id=c.project_id,
        user=user,
        payload={"mentions": new_mentions},
    )
    db.commit()
    db.refresh(c)
    return c


def delete_comment(
    db: Session,
    comment_id: str,
    user: Any,
    *,
    is_admin: bool = False,
) -> MgmtComment:
    c = get_comment(db, comment_id)
    if c.deleted_at is not None:
        return c
    actor_id = _actor(user)
    if c.author_id != actor_id and not is_admin:
        raise ValueError("Yorumu yalnızca yazar veya admin silebilir")
    c.deleted_at = utcnow()
    _audit(
        db,
        action="comment.delete",
        entity_type="mgmt_comment",
        entity_id=c.id,
        project_id=c.project_id,
        user=user,
        payload={"admin_override": is_admin and c.author_id != actor_id},
    )
    db.commit()
    db.refresh(c)
    return c


def react_to_comment(
    db: Session,
    comment_id: str,
    payload: MgmtCommentReact,
    user: Any,
) -> MgmtComment:
    c = get_comment(db, comment_id)
    if c.deleted_at is not None:
        raise ValueError("Silinmiş yorum üzerinde reaksiyon yapılamaz")
    actor_id = _actor(user)
    if actor_id is None:
        raise ValueError("Anonim kullanıcı reaksiyon ekleyemez")
    emoji = payload.emoji.strip()
    if not emoji:
        raise ValueError("Geçersiz emoji")

    reactions: dict[str, list[str]] = {k: list(v) for k, v in (c.reactions or {}).items()}
    bucket = reactions.setdefault(emoji, [])
    if payload.add:
        if actor_id not in bucket:
            bucket.append(actor_id)
    else:
        if actor_id in bucket:
            bucket.remove(actor_id)
        if not bucket:
            reactions.pop(emoji, None)
    c.reactions = reactions
    _audit(
        db,
        action="comment.react",
        entity_type="mgmt_comment",
        entity_id=c.id,
        project_id=c.project_id,
        user=user,
        payload={"emoji": emoji, "add": payload.add},
    )
    db.commit()
    db.refresh(c)
    return c


def _excerpt(body: str, limit: int = 240) -> str:
    txt = (body or "").strip()
    if len(txt) <= limit:
        return txt
    return txt[: limit - 1].rstrip() + "…"


def _link_for(entity_type: str, entity_id: str, project_id: Optional[str]) -> Optional[str]:
    if not project_id:
        return None
    base = f"/p/{project_id}/management"
    if entity_type == "case":
        return f"{base}/cases/{entity_id}"
    if entity_type == "defect":
        return f"{base}/defects?defect_id={entity_id}"
    if entity_type == "plan":
        return f"{base}/plans?plan_id={entity_id}"
    if entity_type == "run":
        return f"{base}/runs/{entity_id}"
    if entity_type == "requirement":
        return f"{base}/requirements?requirement_id={entity_id}"
    return base


# ── Notifications ────────────────────────────────────────────────────────────


def _create_notification(
    db: Session,
    *,
    user_id: str,
    kind: str,
    title: str,
    body: str,
    link_path: Optional[str],
    severity: str,
    project_id: Optional[str],
    tenant_id: str,
    source_trace: dict[str, Any] | None = None,
    channel: str = "in_app",
) -> MgmtNotification:
    if kind not in ALLOWED_NOTIFICATION_KINDS:
        # Soft-allow unknown kinds but coerce to "system" to keep the API forgiving.
        kind = "system"
    if channel not in ALLOWED_NOTIFICATION_CHANNELS:
        channel = "in_app"
    kwargs: dict[str, Any] = dict(
        tenant_id=tenant_id,
        user_id=user_id,
        project_id=project_id,
        kind=kind,
        title=title[:256],
        body=body or "",
        link_path=link_path,
        severity=severity if severity in {"info", "warning", "critical"} else "info",
        source_trace=source_trace or {},
    )
    # `channel` is column-mapped only on the new model; pass conditionally so
    # tests that monkey-patch a lightweight notification stand-in still work.
    if hasattr(MgmtNotification, "channel"):
        kwargs["channel"] = channel
    n = MgmtNotification(**kwargs)
    db.add(n)
    db.flush()
    _route_to_channel(n)
    return n


def _route_to_channel(notif: MgmtNotification) -> None:
    """Fan a notification out to its delivery channel."""
    channel = getattr(notif, "channel", "in_app") or "in_app"

    if channel == "in_app":
        _broadcast(notif.user_id, _serialize_notification(notif))
        return

    if channel == "email":
        try:
            # User email'ini al (notif objesinden veya DB'den)
            recipient = getattr(notif, "recipient_email", None)
            if recipient:
                send_email(EmailMessageData(
                    to=recipient,
                    subject=f"[Neurex] {notif.title or 'Yeni Bildirim'}",
                    body_text=notif.message or notif.title or "Yeni bir bildirim var.",
                    body_html=f"<p>{notif.message or notif.title or 'Yeni bir bildirim var.'}</p>",
                ))
            else:
                logger.warning("[mgmt.notif] email kanalı için recipient_email yok: %s", notif.id)
        except Exception as e:
            logger.error("[mgmt.notif] email gönderilemedi: %s", e)
        return

    if channel == "slack":
        sent = send_notification(
            channel="slack",
            title=notif.title or "Neurex Bildirimi",
            message=notif.message or notif.title or "Yeni bildirim",
            slack_webhook_url=settings.slack_webhook_url,
        )
        if not sent:
            # Fallback: in_app
            _broadcast(notif.user_id, _serialize_notification(notif))
        return

    if channel == "teams":
        sent = send_notification(
            channel="teams",
            title=notif.title or "Neurex Bildirimi",
            message=notif.message or notif.title or "Yeni bildirim",
            teams_webhook_url=settings.teams_webhook_url,
        )
        if not sent:
            _broadcast(notif.user_id, _serialize_notification(notif))
        return

    if channel == "push":
        # Web push — push_notifications_enabled ise gönder
        if settings.push_notifications_enabled:
            logger.info("[mgmt.notif] push bildirimi: %s", notif.id)
            # TODO(Push-v2): pywebpush entegrasyonu buraya gelecek
        _broadcast(notif.user_id, _serialize_notification(notif))
        return

    logger.warning("[mgmt.notif] bilinmeyen kanal: %r", channel)


def create_notification(
    db: Session,
    payload: MgmtNotificationCreate,
    actor: Any | None,
) -> MgmtNotification:
    n = _create_notification(
        db,
        user_id=payload.user_id,
        kind=payload.kind,
        title=payload.title,
        body=payload.body,
        link_path=payload.link_path,
        severity=payload.severity,
        project_id=payload.project_id,
        tenant_id=_tenant_for(actor),
        source_trace=payload.source_trace,
        channel=getattr(payload, "channel", "in_app") or "in_app",
    )
    db.commit()
    db.refresh(n)
    return n


def list_notifications(
    db: Session,
    *,
    user_id: str,
    tenant_id: Optional[str] = None,
    unread_only: bool = False,
    include_archived: bool = False,
    limit: int = 50,
    project_id: Optional[str] = None,
) -> list[MgmtNotification]:
    stmt = select(MgmtNotification).where(MgmtNotification.user_id == user_id)
    if tenant_id is not None:
        stmt = stmt.where(MgmtNotification.tenant_id == tenant_id)
    if unread_only:
        stmt = stmt.where(MgmtNotification.read_at.is_(None))
    if not include_archived:
        stmt = stmt.where(MgmtNotification.archived_at.is_(None))
    if project_id:
        stmt = stmt.where(MgmtNotification.project_id == project_id)
    stmt = stmt.order_by(MgmtNotification.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


def count_notifications(
    db: Session, *, user_id: str, tenant_id: Optional[str] = None
) -> tuple[int, int]:
    total_stmt = select(func.count(MgmtNotification.id)).where(
        MgmtNotification.user_id == user_id,
        MgmtNotification.archived_at.is_(None),
    )
    if tenant_id is not None:
        total_stmt = total_stmt.where(MgmtNotification.tenant_id == tenant_id)
    unread_stmt = total_stmt.where(MgmtNotification.read_at.is_(None))
    total = int(db.scalar(total_stmt) or 0)
    unread = int(db.scalar(unread_stmt) or 0)
    return unread, total


def mark_read(db: Session, *, notification_id: str, user_id: str) -> MgmtNotification:
    n = db.get(MgmtNotification, notification_id)
    if n is None or n.user_id != user_id:
        raise KeyError("Bildirim bulunamadı")
    if n.read_at is None:
        n.read_at = utcnow()
        db.commit()
        db.refresh(n)
    return n


def mark_archived(db: Session, *, notification_id: str, user_id: str) -> MgmtNotification:
    n = db.get(MgmtNotification, notification_id)
    if n is None or n.user_id != user_id:
        raise KeyError("Bildirim bulunamadı")
    if n.archived_at is None:
        n.archived_at = utcnow()
        if n.read_at is None:
            n.read_at = n.archived_at
        db.commit()
        db.refresh(n)
    return n


def mark_all_read(db: Session, *, user_id: str) -> int:
    now = utcnow()
    res = db.execute(
        update(MgmtNotification)
        .where(MgmtNotification.user_id == user_id, MgmtNotification.read_at.is_(None))
        .values(read_at=now)
    )
    db.commit()
    return int(res.rowcount or 0)


def _serialize_notification(n: MgmtNotification) -> dict[str, Any]:
    return {
        "id": n.id,
        "tenant_id": n.tenant_id,
        "user_id": n.user_id,
        "project_id": n.project_id,
        "kind": n.kind,
        "title": n.title,
        "body": n.body,
        "link_path": n.link_path,
        "severity": n.severity,
        "channel": getattr(n, "channel", "in_app"),
        "source_trace": dict(n.source_trace or {}),
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "archived_at": n.archived_at.isoformat() if n.archived_at else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


# ── SSE broadcast bus (in-process) ───────────────────────────────────────────


class _NotificationBus:
    """In-process pub/sub keyed by ``user_id``.

    Single-process by design — production deployments with multiple
    workers should swap this for a Redis pub/sub bridge. Notifications
    persisted in the database remain the source of truth; the bus only
    serves "live" pushes to currently-connected SSE clients.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}
        self._lock = asyncio.Lock()

    async def subscribe(self, user_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        async with self._lock:
            self._subscribers.setdefault(user_id, set()).add(queue)
        return queue

    async def unsubscribe(self, user_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        async with self._lock:
            queues = self._subscribers.get(user_id)
            if queues is None:
                return
            queues.discard(queue)
            if not queues:
                self._subscribers.pop(user_id, None)

    def publish(self, user_id: str, payload: dict[str, Any]) -> None:
        queues = self._subscribers.get(user_id)
        if not queues:
            return
        for q in list(queues):
            try:
                q.put_nowait(payload)
            except asyncio.QueueFull:
                # Drop oldest then enqueue. Best-effort delivery.
                try:
                    q.get_nowait()
                    q.put_nowait(payload)
                except Exception:
                    pass


def _get_notification_bus() -> Any:
    """Return the active notification bus.

    Switches to a Redis-backed adapter when ``REDIS_URL`` is configured
    so multi-worker deployments can fan out SSE events across processes;
    otherwise falls back to the single-process in-memory bus.
    """
    if os.getenv("REDIS_URL"):
        try:
            from app.domains.test_management._notification_redis_bus import (
                RedisNotificationBus,
            )
            return RedisNotificationBus.instance()
        except Exception as exc:  # pragma: no cover — defensive
            logger.warning(
                "Falling back to in-process notification bus (redis init failed): %s",
                exc,
            )
    return _NotificationBus()


_bus: Any = _get_notification_bus()


def _broadcast(user_id: str, payload: dict[str, Any]) -> None:
    _bus.publish(user_id, payload)


async def stream_events(user_id: str, *, keepalive_seconds: float = 25.0) -> AsyncIterator[bytes]:
    """Async generator yielding SSE-formatted bytes for one user."""
    queue = await _bus.subscribe(user_id)
    try:
        # Initial hello.
        yield b": connected\n\n"
        while True:
            try:
                payload = await asyncio.wait_for(queue.get(), timeout=keepalive_seconds)
            except asyncio.TimeoutError:
                yield b": keepalive\n\n"
                continue
            data = json.dumps(payload, default=str).encode("utf-8")
            yield b"event: notification\ndata: " + data + b"\n\n"
    finally:
        await _bus.unsubscribe(user_id, queue)


# Public helper for other services that want to fan out notifications.
def emit_notification(
    db: Session,
    *,
    user_id: str,
    kind: str,
    title: str,
    body: str = "",
    link_path: Optional[str] = None,
    severity: str = "info",
    project_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    source_trace: dict[str, Any] | None = None,
    channel: str = "in_app",
    commit: bool = True,
) -> MgmtNotification:
    """Create a notification and broadcast it. Caller controls commit."""
    n = _create_notification(
        db,
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        link_path=link_path,
        severity=severity,
        project_id=project_id,
        tenant_id=tenant_id or DEFAULT_TENANT_ID,
        source_trace=source_trace,
        channel=channel,
    )
    if commit:
        db.commit()
        db.refresh(n)
    return n


# ── M-50 / M-45 AI: thread summary + notification digest ─────────────────────


def _load_prompt(name: str) -> str:
    """Load a prompt template from the package `prompts/` directory."""
    base = os.path.join(os.path.dirname(__file__), "prompts")
    path = os.path.join(base, f"{name}.txt")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _call_llm(task_type: str, user_message: str, system_message: str) -> Optional[dict[str, Any]]:
    """Call the AI gateway and best-effort parse JSON.

    Returns ``None`` when the gateway is unavailable so callers can fall
    back to a deterministic heuristic — production tests must not depend
    on a live model.
    """
    try:
        from app.domains.ai.gateway_client import gateway_complete, gateway_is_available
    except Exception as exc:  # pragma: no cover — defensive import
        logger.debug("AI gateway client import failed: %s", exc)
        return None
    try:
        if not gateway_is_available():
            return None
        raw = gateway_complete(
            task_type=task_type,
            user_message=user_message,
            system_message=system_message,
            temperature=0.2,
            max_tokens=1024,
            json_mode=True,
            use_cache=True,
        )
        if not raw:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # Some models wrap JSON in prose; try to extract the first {...}.
            start = raw.find("{")
            end = raw.rfind("}")
            if start >= 0 and end > start:
                try:
                    return json.loads(raw[start : end + 1])
                except json.JSONDecodeError:
                    return None
            return None
    except Exception as exc:  # pragma: no cover — gateway transient failure
        logger.warning("LLM call failed task=%s: %s", task_type, exc)
        return None


def summarize_thread(
    db: Session,
    *,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
) -> dict[str, Any]:
    """Return an AI summary `{tldr, decisions, openQuestions}` for a thread.

    Falls back to a heuristic when the LLM gateway is unavailable.
    """
    if entity_type not in ALLOWED_COMMENT_ENTITY_TYPES:
        raise ValueError("entity_type not allowed")
    comments = list_comments(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        include_deleted=False,
        tenant_id=tenant_id,
    )

    transcript_lines: list[str] = []
    for c in comments:
        author = (c.author_id or "anon")[:8]
        ts = c.created_at.isoformat() if c.created_at else ""
        transcript_lines.append(f"[{ts}] {author}: {c.body_md}")
    transcript = "\n".join(transcript_lines)[:12000]

    system_prompt = _load_prompt("thread_summarize") or (
        "You summarize threaded QA discussions. Reply with strict JSON: "
        '{"tldr": string, "decisions": string[], "openQuestions": string[]}.'
    )
    parsed: Optional[dict[str, Any]] = None
    if transcript.strip():
        parsed = _call_llm(
            task_type="mgmt.comm.thread_summarize",
            user_message=transcript,
            system_message=system_prompt,
        )

    source = "llm"
    if parsed is None:
        source = "fallback"
        tldr = _excerpt(comments[-1].body_md, 200) if comments else ""
        parsed = {
            "tldr": tldr,
            "decisions": [],
            "openQuestions": [],
        }

    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "generated_at": utcnow().isoformat(),
        "tldr": str(parsed.get("tldr") or "")[:1000],
        "decisions": [str(d)[:280] for d in (parsed.get("decisions") or [])][:10],
        "openQuestions": [str(q)[:280] for q in (parsed.get("openQuestions") or [])][:10],
        "comment_count": len(comments),
        "source": source,
    }


def digest_notifications(
    db: Session,
    *,
    tenant_id: str,
    user_id: str,
    window: str = "24h",
) -> dict[str, Any]:
    """Group recent notifications into themed buckets (LLM-assisted)."""
    delta = timedelta(hours=24) if window == "24h" else timedelta(days=7)
    cutoff = utcnow() - delta
    stmt = (
        select(MgmtNotification)
        .where(
            MgmtNotification.user_id == user_id,
            MgmtNotification.tenant_id == tenant_id,
            MgmtNotification.created_at >= cutoff,
        )
        .order_by(MgmtNotification.created_at.desc())
        .limit(200)
    )
    items = list(db.scalars(stmt).all())

    def _fallback() -> list[dict[str, Any]]:
        counts: dict[str, list[MgmtNotification]] = {}
        for n in items:
            counts.setdefault(n.kind or "system", []).append(n)
        groups = []
        for kind, ns in counts.items():
            sample_title = ns[0].title if ns else kind
            groups.append(
                {
                    "theme": kind.replace("_", " ").title(),
                    "count": len(ns),
                    "oneLine": _excerpt(sample_title, 140),
                }
            )
        groups.sort(key=lambda g: g["count"], reverse=True)
        return groups[:8]

    digest_payload = None
    if items:
        compact = [
            {
                "kind": n.kind,
                "title": n.title,
                "body": _excerpt(n.body, 160),
                "severity": n.severity,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items[:80]
        ]
        system_prompt = _load_prompt("notif_digest") or (
            "Group the user's recent notifications into 3-6 themed buckets. "
            'Reply with strict JSON: {"groups": [{"theme": string, "count": number, "oneLine": string}]}.'
        )
        digest_payload = _call_llm(
            task_type="mgmt.me.notif_digest",
            user_message=json.dumps(compact, ensure_ascii=False),
            system_message=system_prompt,
        )

    source = "llm"
    if not digest_payload or not isinstance(digest_payload.get("groups"), list):
        source = "fallback"
        groups = _fallback()
    else:
        groups = []
        for g in digest_payload["groups"][:8]:
            try:
                groups.append(
                    {
                        "theme": str(g.get("theme") or "")[:120],
                        "count": int(g.get("count") or 0),
                        "oneLine": str(g.get("oneLine") or "")[:240],
                    }
                )
            except (TypeError, ValueError):
                continue
        if not groups:
            source = "fallback"
            groups = _fallback()

    return {
        "window": window,
        "generated_at": utcnow().isoformat(),
        "groups": groups,
        "source": source,
        "total_items": len(items),
    }
