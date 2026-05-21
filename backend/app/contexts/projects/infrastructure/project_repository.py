"""
Project repository implementations.

InMemoryProjectRepository — for unit tests, no DB required.
SqlProjectRepository      — async SQLAlchemy (requires DB session).
"""

from __future__ import annotations

from uuid import UUID

from app.contexts.projects.domain.project import (
    Project,
    ProjectId,
    ProjectName,
    ProductFamily,
    ProjectStatus,
)


# ─── In-memory (for tests) ────────────────────────────────────────────────

class InMemoryProjectRepository:
    """Thread-unsafe in-memory store. Sufficient for unit tests."""

    def __init__(self) -> None:
        self._store: dict[UUID, Project] = {}

    async def get(self, project_id: ProjectId | UUID) -> Project | None:
        value = project_id.value if isinstance(project_id, ProjectId) else project_id
        return self._store.get(value)

    async def get_by_name(self, name: ProjectName) -> Project | None:
        return next((p for p in self._store.values() if p.name == name), None)

    async def list_all(self, archived: bool = False) -> list[Project]:
        projects = list(self._store.values())
        if not archived:
            projects = [p for p in projects if p.status == ProjectStatus.ACTIVE]
        return projects

    async def save(self, project: Project) -> None:
        self._store[project.id.value] = project


# ─── SQLAlchemy async implementation ────────────────────────────────────────

try:
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import select, text
    from app.models.project import ProjectModel  # type: ignore[import]

    class SqlProjectRepository:
        def __init__(self, session: AsyncSession) -> None:
            self._session = session

        async def get(self, project_id: ProjectId | UUID) -> Project | None:
            value = project_id.value if isinstance(project_id, ProjectId) else project_id
            row = await self._session.get(ProjectModel, str(value))
            if row is None:
                return None
            return self._to_domain(row)

        async def get_by_name(self, name: ProjectName) -> Project | None:
            result = await self._session.execute(select(ProjectModel).where(ProjectModel.name == str(name)))
            row = result.scalar_one_or_none()
            if row is None:
                return None
            return self._to_domain(row)

        async def list_all(self, archived: bool = False) -> list[Project]:
            stmt = select(ProjectModel)
            if not archived:
                stmt = stmt.where(ProjectModel.archived == False)  # noqa: E712
            result = await self._session.execute(stmt)
            return [self._to_domain(r) for r in result.scalars().all()]

        async def save(self, project: Project) -> None:
            row = await self._session.get(ProjectModel, str(project.id.value))
            if row is None:
                row = ProjectModel(id=str(project.id.value))
                self._session.add(row)
            row.name = str(project.name)
            row.description = project.description
            row.base_url = project.base_url
            row.product_family = project.product_family.value if project.product_family else None
            row.archived = project.status == ProjectStatus.ARCHIVED
            await self._session.flush()

        @staticmethod
        def _to_domain(row: "ProjectModel") -> Project:
            family = ProductFamily(row.product_family) if row.product_family else None
            return Project(
                id=ProjectId(UUID(row.id)),
                name=ProjectName(row.name),
                description=row.description or "",
                base_url=row.base_url or "",
                product_family=family,
                status=ProjectStatus.ARCHIVED if row.archived else ProjectStatus.ACTIVE,
            )

except ImportError:
    # ProjectModel not yet generated — SQL repo unavailable in this environment
    pass
