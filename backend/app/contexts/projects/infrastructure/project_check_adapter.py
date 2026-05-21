"""
ProjectExistsCheckAdapter — scenarios/application'da tanımlı `ProjectExistsCheck`
protokolünü projects context tarafından gerçekleştirir.

Cross-context call yerine event-driven veya read-model tercih edilebilir;
burada en sade implementasyon: projects repo'sunu doğrudan sorgular.

Composition root (DI container) bunu scenarios handler'ına geçirir.
"""

from __future__ import annotations

from uuid import UUID

from app.contexts.projects.application import ProjectRepository
from app.contexts.projects.domain import ProjectId, ProjectStatus


class ProjectExistsCheckAdapter:
    """`ProjectExistsCheck` protokol uygulaması."""

    def __init__(self, projects: ProjectRepository):
        self.projects = projects

    async def is_active(self, project_id: UUID) -> bool:
        project = await self.projects.get(ProjectId(project_id))
        if project is None:
            return False
        return project.status == ProjectStatus.ACTIVE
