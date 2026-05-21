"""
Repository protocols for projects context.

Concrete implementations (SQLAlchemy, in-memory) live in infrastructure.
Application layer programs against these Protocol types only.
"""

from __future__ import annotations

from typing import Protocol

from app.contexts.projects.domain import Project, ProjectId, ProjectName


class ProjectRepository(Protocol):
    """Repository for Project aggregate."""

    async def get(self, project_id: ProjectId) -> Project | None: ...
    async def get_by_name(self, name: ProjectName) -> Project | None: ...
    async def save(self, project: Project) -> None: ...
