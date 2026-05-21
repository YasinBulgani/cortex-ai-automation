"""DSL arama sonuçları için kullanıcı geri bildirim servisi.

`sd_dsl_feedback` tablosuna yazma ve skor bonusu (rerank) okuma.

Rerank stratejisi (şimdilik basit, ileride ML ile değiştirilebilir):
    - Son 30 günde aynı `query` için en az 3 🞠 varsa: skor + 0.15
    - 2 veya daha fazla 👎 varsa: skor - 0.15
    - İşaretsiz hit'ler değişmez
    - Alt sınır 0.0, üst sınır 1.0 olacak şekilde clamp edilir
"""
from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infra.models import DslFeedback

logger = logging.getLogger(__name__)

_BONUS_UP = 0.15
_BONUS_DOWN = -0.15
_UPVOTE_THRESHOLD = 3
_DOWNVOTE_THRESHOLD = 2
_LOOKBACK_DAYS = 30


def record_feedback(
    db: Session,
    *,
    user_id: Optional[str],
    query: str,
    action_id: str,
    vote: str,
    search_mode: Optional[str] = None,
    rank: Optional[int] = None,
    raw_score: Optional[float] = None,
) -> DslFeedback:
    """Kullanıcı geri bildirimini kaydet."""
    if vote not in {"up", "down", "ignored"}:
        raise ValueError("vote 'up' | 'down' | 'ignored' olmalı")
    entry = DslFeedback(
        user_id=user_id,
        query=(query or "")[:500],
        action_id=action_id[:128],
        vote=vote,
        search_mode=search_mode[:32] if search_mode else None,
        rank=rank,
        raw_score=(f"{raw_score:.4f}" if raw_score is not None else None),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def feedback_bonus_for(
    db: Session, *, query: str, action_ids: list[str]
) -> dict[str, float]:
    """Verilen (query, action_id) çiftleri için rerank bonusu döner.

    Değerler -0.15 .. +0.15 aralığında, "ignored" oylar dikkate alınmaz.
    """
    if not action_ids or not query:
        return {}

    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)

    rows = db.execute(
        select(
            DslFeedback.action_id,
            DslFeedback.vote,
            func.count(DslFeedback.id),
        )
        .where(DslFeedback.query == query[:500])
        .where(DslFeedback.action_id.in_(action_ids))
        .where(DslFeedback.created_at >= since)
        .where(DslFeedback.vote.in_(["up", "down"]))
        .group_by(DslFeedback.action_id, DslFeedback.vote)
    ).all()

    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"up": 0, "down": 0})
    for action_id, vote, count in rows:
        counts[action_id][vote] += int(count)

    bonuses: dict[str, float] = {}
    for action_id, c in counts.items():
        bonus = 0.0
        if c["up"] >= _UPVOTE_THRESHOLD:
            bonus += _BONUS_UP
        if c["down"] >= _DOWNVOTE_THRESHOLD:
            bonus += _BONUS_DOWN
        if bonus:
            bonuses[action_id] = bonus
    return bonuses


def feedback_stats_for_action(db: Session, action_id: str) -> dict:
    """Bir cümleciğin son 30 gündeki toplam 👍/👎 sayısı — UI'da gösterim için."""
    since = datetime.now(timezone.utc) - timedelta(days=_LOOKBACK_DAYS)
    rows = db.execute(
        select(DslFeedback.vote, func.count(DslFeedback.id))
        .where(DslFeedback.action_id == action_id)
        .where(DslFeedback.created_at >= since)
        .group_by(DslFeedback.vote)
    ).all()
    result = {"up": 0, "down": 0, "ignored": 0}
    for vote, count in rows:
        result[vote] = int(count)
    return result
