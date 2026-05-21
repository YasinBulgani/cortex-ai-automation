"""
Projects bounded context — FastAPI HTTP layer.

Endpoints:
  POST   /contexts/projects          — CreateProject
  GET    /contexts/projects          — list active projects (dev convenience)
  GET    /contexts/projects/{id}     — get project by id
  PATCH  /contexts/projects/{id}/name — RenameProject
  DELETE /contexts/projects/{id}     — ArchiveProject

Infrastructure: InMemoryProjectRepository + InMemoryOutbox (dev/test).
Swap to SqlAlchemyProjectRepository + SqlAlchemyOutboxRepository for prod.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.contexts.projects.application import (
    ArchiveProjectCommand,
    ArchiveProjectHandler,
    CreateProjectCommand,
    CreateProjectHandler,
    RenameProjectCommand,
    RenameProjectHandler,
)
from app.contexts.projects.application.rename_project import (
    ProjectNameConflictError,
    ProjectNotFoundError,
)
from app.contexts.projects.application.create_project import ProjectAlreadyExistsError
from app.contexts.projects.domain import ProductFamily, ProjectId, ProjectStatus
from app.contexts.projects.infrastructure import InMemoryProjectRepository
from app.deps import get_current_user

router = APIRouter(prefix="/contexts/projects", tags=["contexts-projects"])

# ─── In-memory singletons (dev / integration tests without a DB) ─────────────

_projects_repo = InMemoryProjectRepository()


class _InMemoryOutbox:
    async def append(self, entry) -> None:
        pass  # fire-and-forget in dev; wire SqlAlchemyOutboxRepository for prod


_outbox = _InMemoryOutbox()

# ─── Pydantic schemas ────────────────────────────────────────────────────────


class ProjectCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    base_url: str = ""
    product_family: ProductFamily | None = None


class ProjectRenameIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)


class ProjectArchiveIn(BaseModel):
    reason: str = ""


class ProjectOut(BaseModel):
    id: UUID
    name: str
    description: str
    base_url: str
    product_family: str | None
    status: str


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _project_out(project) -> ProjectOut:
    return ProjectOut(
        id=project.id.value,
        name=str(project.name),
        description=project.description,
        base_url=project.base_url,
        product_family=project.product_family.value if project.product_family else None,
        status=project.status.value,
    )


async def _get_or_404(project_id: UUID):
    proj = await _projects_repo.get(ProjectId(project_id))
    if proj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
    return proj


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
async def create_project(body: ProjectCreateIn, _user=Depends(get_current_user)):
    handler = CreateProjectHandler(projects=_projects_repo, outbox=_outbox)
    cmd = CreateProjectCommand(
        name=body.name,
        description=body.description,
        base_url=body.base_url,
        product_family=body.product_family,
    )
    try:
        project_id = await handler.handle(cmd)
    except (ValueError, ProjectAlreadyExistsError) as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    proj = await _projects_repo.get(project_id)
    return _project_out(proj)


@router.get("", response_model=list[ProjectOut])
async def list_projects(_user=Depends(get_current_user)):
    projects = [
        p for p in _projects_repo._by_id.values()
        if p.status == ProjectStatus.ACTIVE
    ]
    return [_project_out(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, _user=Depends(get_current_user)):
    return _project_out(await _get_or_404(project_id))


@router.patch("/{project_id}/name", response_model=ProjectOut)
async def rename_project(
    project_id: UUID, body: ProjectRenameIn, _user=Depends(get_current_user)
):
    handler = RenameProjectHandler(projects=_projects_repo, outbox=_outbox)
    try:
        await handler.handle(
            RenameProjectCommand(
                project_id=ProjectId(project_id),
                new_name=body.name,
            )
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
    except ProjectNameConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    return _project_out(await _projects_repo.get(ProjectId(project_id)))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def archive_project(
    project_id: UUID, body: ProjectArchiveIn = ProjectArchiveIn(), _user=Depends(get_current_user)
):
    handler = ArchiveProjectHandler(projects=_projects_repo, outbox=_outbox)
    try:
        await handler.handle(
            ArchiveProjectCommand(project_id=ProjectId(project_id), reason=body.reason)
        )
    except ProjectNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proje bulunamadı")
