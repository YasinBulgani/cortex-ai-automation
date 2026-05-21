"""
SQLAlchemy implementation of ProjectRepository.

Postgres-backed. ORM <-> domain çeviri burada izole. Domain layer SQLAlchemy
hakkında hiçbir şey bilmez.

Migration: alembic revision (yeni tablo `prj_projects`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Column, DateTime, String, Text, select
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base
from sqlalchemy.sql import func

from app.contexts.projects.application import ProjectRepository
from app.contexts.projects.domain import (
    ProductFamily,
    Project,
    ProjectId,
    ProjectName,
    ProjectStatus,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


Base = declarative_base()


class ProjectRow(Base):
    """
    Projects tablosu.

    Index'ler:
      - id (pk)
      - name (unique within tenant — tenant_id kolonu sonra eklenir)
      - status (filtering için)
    """

    __tablename__ = "prj_projects"

    id              = Column(PG_UUID(as_uuid=True), primary_key=True)
    name            = Column(String(255), nullable=False, unique=True, index=True)
    description     = Column(Text, nullable=False, default="")
    base_url        = Column(String(2048), nullable=False, default="")
    product_family  = Column(String(50), nullable=True)
    status          = Column(String(20), nullable=False, default=ProjectStatus.ACTIVE.value, index=True)
    version         = Column("agg_version", String(20), nullable=False, default="0")
    created_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    @classmethod
    def from_aggregate(cls, project: Project) -> "ProjectRow":
        return cls(
            id=project.id.value,
            name=str(project.name),
            description=project.description,
            base_url=project.base_url,
            product_family=project.product_family.value if project.product_family else None,
            status=project.status.value,
            version=str(project.version),
        )

    def update_from_aggregate(self, project: Project) -> None:
        self.name = str(project.name)
        self.description = project.description
        self.base_url = project.base_url
        self.product_family = project.product_family.value if project.product_family else None
        self.status = project.status.value
        self.version = str(project.version)

    def to_aggregate(self) -> Project:
        return Project(
            id=ProjectId(self.id),
            name=ProjectName(self.name),
            description=self.description,
            base_url=self.base_url,
            product_family=ProductFamily(self.product_family) if self.product_family else None,
            status=ProjectStatus(self.status),
        )


class SqlAlchemyProjectRepository(ProjectRepository):
    """ProjectRepository PostgreSQL implementation (async)."""

    def __init__(self, session: "AsyncSession"):
        self.session = session

    async def get(self, project_id: ProjectId) -> Project | None:
        row = await self.session.get(ProjectRow, project_id.value)
        return row.to_aggregate() if row else None

    async def get_by_name(self, name: ProjectName) -> Project | None:
        stmt = select(ProjectRow).where(ProjectRow.name == str(name))
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return row.to_aggregate() if row else None

    async def save(self, project: Project) -> None:
        """Upsert — yoksa insert, varsa update.

        Commit caller'ın sorumluluğunda (outbox entry'leriyle aynı tx'te
        olabilsin diye).
        """
        existing = await self.session.get(ProjectRow, project.id.value)
        if existing is None:
            self.session.add(ProjectRow.from_aggregate(project))
        else:
            existing.update_from_aggregate(project)

    # Yardımcı (debugging / admin)
    async def list_active(self, limit: int = 50) -> list[Project]:
        stmt = (
            select(ProjectRow)
            .where(ProjectRow.status == ProjectStatus.ACTIVE.value)
            .order_by(ProjectRow.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [row.to_aggregate() for row in result.scalars().all()]
