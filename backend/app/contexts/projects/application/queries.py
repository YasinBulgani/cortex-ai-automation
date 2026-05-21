"""CQRS read side — project queries."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.contexts.projects.domain.project import ProductFamily, Project, ProjectId
from .create_project import ProjectRepository


@dataclass(frozen=True, slots=True)
class GetProjectQuery:
    project_id: UUID


@dataclass(frozen=True, slots=True)
class ListProjectsQuery:
    archived: bool = False
    product_family: str | None = None


# ─── Read models (lightweight DTOs) ────────────────────────────────────────

@dataclass(slots=True)
class ProjectDTO:
    id: str
    name: str
    description: str
    base_url: str
    product_family: str | None
    status: str

    @classmethod
    def from_aggregate(cls, p: Project) -> "ProjectDTO":
        return cls(
            id=str(p.id.value),
            name=str(p.name),
            description=p.description,
            base_url=p.base_url,
            product_family=p.product_family.value if p.product_family else None,
            status=p.status.value,
        )


# ─── Handlers ───────────────────────────────────────────────────────────────

class GetProjectHandler:
    def __init__(self, projects: ProjectRepository) -> None:
        self.projects = projects

    async def handle(self, query: GetProjectQuery) -> ProjectDTO | None:
        project = await self.projects.get(ProjectId(query.project_id))
        if project is None:
            return None
        return ProjectDTO.from_aggregate(project)


class ListProjectsHandler:
    def __init__(self, projects: ProjectRepository) -> None:
        self.projects = projects

    async def handle(self, query: ListProjectsQuery) -> list[ProjectDTO]:
        all_projects = await self.projects.list_all(archived=query.archived)

        if query.product_family:
            try:
                family = ProductFamily(query.product_family)
                all_projects = [p for p in all_projects if p.product_family == family]
            except ValueError:
                pass

        return [ProjectDTO.from_aggregate(p) for p in all_projects]
