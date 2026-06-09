"""TSPM — thin service facade for projects and scenarios.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps SQLAlchemy TspmProject / TspmScenario models.
Async-first using AsyncSession.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.tspm.models import TspmProject, TspmProjectMember, TspmScenario, utcnow

logger = logging.getLogger(__name__)


async def list_projects(
    db: AsyncSession,
    limit: int = 50,
    owner_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List TSPM projects, newest first.

    Args:
        db: AsyncSession.
        limit: Maximum rows (capped at 500).
        owner_id: Optional filter by owner/creator user ID.

    Returns:
        List of project dicts.
    """
    limit = min(int(limit), 500)
    q = select(TspmProject).order_by(TspmProject.created_at.desc()).limit(limit)
    if owner_id:
        q = q.join(TspmProjectMember, TspmProjectMember.project_id == TspmProject.id).where(
            TspmProjectMember.user_id == owner_id
        )
    result = await db.scalars(q)
    projects = list(result.all())
    return [{c.key: getattr(p, c.key) for c in p.__table__.columns} for p in projects]


async def create_project(
    db: AsyncSession,
    data: Dict[str, Any],
    owner_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new TSPM project.

    Args:
        db: AsyncSession.
        data: Project fields. 'name' is required.
        owner_id: User ID of the creator.

    Returns:
        Created project dict.

    Raises:
        ValueError: Missing required 'name'.
    """
    name = (data.get("name") or "").strip()
    if not name:
        raise ValueError("'name' alanı zorunludur.")

    project = TspmProject(
        name=name,
        description=data.get("description") or "",
        owner_id=owner_id,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    logger.info("TspmProject oluşturuldu: %s (owner=%s)", project.id, owner_id)
    return {c.key: getattr(project, c.key) for c in project.__table__.columns}


async def list_scenarios(
    db: AsyncSession,
    project_id: str,
    limit: int = 100,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List scenarios for a project.

    Args:
        db: AsyncSession.
        project_id: Parent project ID.
        limit: Maximum rows (capped at 1000).
        status: Optional status filter.

    Returns:
        List of scenario dicts.

    Raises:
        KeyError: Project not found.
    """
    project = await db.get(TspmProject, project_id)
    if project is None:
        raise KeyError(f"TspmProject '{project_id}' bulunamadı.")

    limit = min(int(limit), 1000)
    q = (
        select(TspmScenario)
        .where(TspmScenario.project_id == project_id)
        .order_by(TspmScenario.created_at.desc())
        .limit(limit)
    )
    if status:
        q = q.where(TspmScenario.status == status)

    result = await db.scalars(q)
    scenarios = list(result.all())
    return [{c.key: getattr(s, c.key) for c in s.__table__.columns} for s in scenarios]
