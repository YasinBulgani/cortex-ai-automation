"""
Use case: Rename an existing project.

İş kuralı:
- Proje bulunamazsa 404
- Yeni isim başka projede kullanılıyorsa reddet (cross-aggregate uniqueness)
- Arşivli proje yeniden adlandırılamaz (domain'de zaten kontrol)
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxRepository, OutboxEntry
from app.contexts.projects.domain import ProjectId, ProjectName

from .repositories import ProjectRepository


@dataclass(frozen=True, slots=True)
class RenameProjectCommand:
    project_id: ProjectId
    new_name: str


class ProjectNotFoundError(ValueError):
    """Proje bulunamadı."""


class ProjectNameConflictError(Exception):
    """Hedef isim başka bir projede kullanılıyor."""


class RenameProjectHandler:
    def __init__(self, projects: ProjectRepository, outbox: OutboxRepository):
        self.projects = projects
        self.outbox = outbox

    async def handle(self, cmd: RenameProjectCommand) -> None:
        new_name = ProjectName(cmd.new_name)

        project = await self.projects.get(cmd.project_id)
        if project is None:
            raise ProjectNotFoundError(f"Proje bulunamadı: {cmd.project_id}")

        if new_name == project.name:
            return  # No-op

        conflict = await self.projects.get_by_name(new_name)
        if conflict is not None and conflict.id != project.id:
            raise ProjectNameConflictError(f"Bu isim başka bir projede: {new_name}")

        project.rename(new_name)

        await self.projects.save(project)
        for event in project.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))
