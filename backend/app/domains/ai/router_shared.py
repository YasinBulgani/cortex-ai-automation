"""Shared helpers and type aliases for AI routers."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User

logger = logging.getLogger(__name__)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _estimate_tokens(*parts: object) -> int:
    joined = "".join(str(part) for part in parts if part)
    return max(len(joined) // 3, 0)


def check_llm_access(user_id: str) -> None:
    try:
        from app.domains.ai.llm_rate_limiter import check_llm_rate_limit

        check_llm_rate_limit(user_id)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("Rate limiter check failed for user %s: %s", user_id, exc)


def record_llm_usage_safe(user_id: str, *parts: object) -> None:
    try:
        from app.domains.ai.llm_rate_limiter import record_llm_usage

        record_llm_usage(user_id, tokens_used=_estimate_tokens(*parts))
    except Exception as exc:
        logger.warning("LLM usage record failed for user %s: %s", user_id, exc)


def require_project_access(db: Session, user: User, project_id: str) -> None:
    if not project_id:
        raise HTTPException(400, "project_id query parametresi gerekli")
    from app.deps import _user_permissions
    from app.domains.tspm.models import TspmProject, TspmProjectMember

    project = db.get(TspmProject, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")

    perms = _user_permissions(user)
    if "admin.*" in perms:
        return

    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu projeye erişim yetkiniz yok")


def raise_structured_internal_error(code: str, message: str, exc: Exception) -> None:
    details = str(exc).strip() or exc.__class__.__name__
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={
            "code": code,
            "message": message,
            "error_type": exc.__class__.__name__,
            "details": details[:300],
        },
    )

