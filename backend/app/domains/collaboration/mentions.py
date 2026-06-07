"""@mention parser — extract @user_handle tokens from comment body."""

from __future__ import annotations

import re
from collections.abc import Iterable

from sqlalchemy.orm import Session

from app.infra.models import User

# @handle: letters, digits, dot, underscore, dash; min 2 chars
# avoids @ inside emails (preceded by alphanumeric)
_MENTION_RE = re.compile(r"(?:(?<=^)|(?<=[\s,;!?]))@([A-Za-z0-9._-]{2,64})")


def extract_handles(body: str) -> list[str]:
    if not body:
        return []
    return list({m.group(1).lower() for m in _MENTION_RE.finditer(body)})


def resolve_handles_to_users(
    db: Session,
    handles: Iterable[str],
    tenant_id: str | None = None,
) -> list[User]:
    """Match handles against the local-part of email. Fast & deterministic."""
    handles = [h.lower() for h in handles]
    if not handles:
        return []
    from sqlalchemy import func, or_, select
    conds = [func.lower(User.email).like(f"{h}@%") for h in handles]
    q = select(User).where(or_(*conds))
    if tenant_id:
        q = q.where(User.tenant_id == tenant_id)
    return list(db.execute(q).scalars().all())


def parse_and_resolve(
    db: Session,
    body: str,
    tenant_id: str | None = None,
) -> list[User]:
    return resolve_handles_to_users(db, extract_handles(body), tenant_id=tenant_id)
