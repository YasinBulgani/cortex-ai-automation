"""
Projects context — FastAPI router.

Mounts at: /api/v2/projects
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.contexts._shared.outbox import InMemoryOutboxRepository
from app.contexts.projects.application.archive_project import (
    ArchiveProjectCommand,
    ArchiveProjectHandler,
    RestoreProjectCommand,
    RestoreProjectHandler,
)
from app.contexts.projects.application.create_project import (
    CreateProjectCommand,
    CreateProjectHandler,
)
from app.contexts.projects.application.queries import (
    GetProjectHandler,
    GetProjectQuery,
    ListProjectsHandler,
    ListProjectsQuery,
    ProjectDTO,
)
from app.contexts.projects.application.rename_project import (
    RenameProjectCommand,
    RenameProjectHandler,
)
from app.contexts.projects.infrastructure.project_repository import (
    InMemoryProjectRepository,
)

router = APIRouter(prefix="/api/v2/projects", tags=["projects-v2"])

# Shared in-memory store for the process lifetime (swapped for DB in prod)
_repo = InMemoryProjectRepository()
_outbox = InMemoryOutboxRepository()


# ─── Request / Response schemas ─────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    base_url: str = ""
    product_family: str | None = None


class RenameProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ArchiveProjectRequest(BaseModel):
    reason: str = ""


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    base_url: str
    product_family: str | None
    status: str

    @classmethod
    def from_dto(cls, dto: ProjectDTO) -> "ProjectResponse":
        return cls(**dto.__dict__)


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    archived: bool = False,
    product_family: str | None = None,
) -> list[ProjectResponse]:
    handler = ListProjectsHandler(_repo)
    dtos = await handler.handle(ListProjectsQuery(archived=archived, product_family=product_family))
    return [ProjectResponse.from_dto(d) for d in dtos]


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(body: CreateProjectRequest) -> ProjectResponse:
    handler = CreateProjectHandler(_repo, _outbox)
    try:
        project_id = await handler.handle(
            CreateProjectCommand(
                name=body.name,
                description=body.description,
                base_url=body.base_url,
                product_family=body.product_family,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    get_handler = GetProjectHandler(_repo)
    dto = await get_handler.handle(GetProjectQuery(project_id=project_id))
    return ProjectResponse.from_dto(dto)  # type: ignore[arg-type]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID) -> ProjectResponse:
    handler = GetProjectHandler(_repo)
    dto = await handler.handle(GetProjectQuery(project_id=project_id))
    if dto is None:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return ProjectResponse.from_dto(dto)


@router.patch("/{project_id}/rename", response_model=ProjectResponse)
async def rename_project(project_id: UUID, body: RenameProjectRequest) -> ProjectResponse:
    handler = RenameProjectHandler(_repo, _outbox)
    try:
        await handler.handle(RenameProjectCommand(project_id=project_id, new_name=body.name))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    dto = await GetProjectHandler(_repo).handle(GetProjectQuery(project_id=project_id))
    return ProjectResponse.from_dto(dto)  # type: ignore[arg-type]


@router.post("/{project_id}/archive", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(project_id: UUID, body: ArchiveProjectRequest) -> None:
    handler = ArchiveProjectHandler(_repo, _outbox)
    try:
        await handler.handle(ArchiveProjectCommand(project_id=project_id, reason=body.reason))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/{project_id}/restore", status_code=status.HTTP_204_NO_CONTENT)
async def restore_project(project_id: UUID) -> None:
    handler = RestoreProjectHandler(_repo, _outbox)
    try:
        await handler.handle(RestoreProjectCommand(project_id=project_id))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
