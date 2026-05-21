"""
Use case: Archive or restore a project.

Domain'de idempotent (zaten arşivliyse/aktifse no-op). Reason audit için
outbox'a gider.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxEntry, OutboxRepository
from app.contexts.projects.domain import ProjectId

from .rename_project import ProjectNotFoundError
from .repositories import ProjectRepository


@dataclass(frozen=True, slots=True)
class ArchiveProjectCommand:
    project_id: ProjectId
    reason: str = ""


@dataclass(frozen=True, slots=True)
class RestoreProjectCommand:
    project_id: ProjectId


class ArchiveProjectHandler:
    def __init__(self, projects: ProjectRepository, outbox: OutboxRepository):
        self.projects = projects
        self.outbox = outbox

    async def handle(self, cmd: ArchiveProjectCommand) -> None:
        project = await self.projects.get(cmd.project_id)
        if project is None:
            raise ProjectNotFoundError(f"Proje bulunamadı: {cmd.project_id}")

        already_archived = project.status.value == "archived"
        project.archive(cmd.reason)
        if already_archived:
            return

        await self.projects.save(project)
        for event in project.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))


class RestoreProjectHandler:
    def __init__(self, projects: ProjectRepository, outbox: OutboxRepository):
        self.projects = projects
        self.outbox = outbox

    async def handle(self, cmd: RestoreProjectCommand) -> None:
        project = await self.projects.get(cmd.project_id)
        if project is None:
            raise ProjectNotFoundError(f"Proje bulunamadı: {cmd.project_id}")

        already_active = project.status.value == "active"
        project.restore()
        if already_active:
            return

        await self.projects.save(project)
        for event in project.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))
