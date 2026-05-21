"""
Use case: Create a new project.

İş kuralı: aynı isimde proje varsa reddet (uniqueness DB constraint ile de
korunur ama happy path için burada da check).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.contexts._shared.outbox import OutboxRepository, OutboxEntry
from app.contexts.projects.domain import (
    Project,
    ProjectId,
    ProjectName,
    ProductFamily,
)

from .repositories import ProjectRepository


@dataclass(frozen=True, slots=True)
class CreateProjectCommand:
    name: str
    description: str = ""
    base_url: str = ""
    product_family: ProductFamily | str | None = None


class ProjectAlreadyExistsError(Exception):
    """Aynı isimde proje var."""


class CreateProjectHandler:
    def __init__(self, projects: ProjectRepository, outbox: OutboxRepository):
        self.projects = projects
        self.outbox = outbox

    async def handle(self, cmd: CreateProjectCommand) -> ProjectId:
        name = ProjectName(cmd.name)

        existing = await self.projects.get_by_name(name)
        if existing is not None:
            raise ProjectAlreadyExistsError(f"Bu isimde proje var: {name}")

        family = ProductFamily(cmd.product_family) if isinstance(cmd.product_family, str) else cmd.product_family

        project = Project.create(
            name=name,
            description=cmd.description,
            base_url=cmd.base_url,
            product_family=family,
        )

        await self.projects.save(project)
        for event in project.pull_events():
            await self.outbox.append(OutboxEntry.from_event(event))

        return project.id
