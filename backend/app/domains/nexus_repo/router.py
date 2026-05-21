"""Nexus Repo API router."""

from __future__ import annotations

import threading
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.config import settings
from app.infra.database import get_db
from . import service
from .schemas import (
    NexusHealthOut,
    NexusProjectCreate,
    NexusProjectOut,
    NexusProjectUpdate,
    NexusCrawlJobOut,
    NexusScenarioCreate,
    NexusScenarioUpdate,
    NexusScenarioOut,
    NexusEndpointOut,
    NexusFileOut,
    NexusStatsOut,
    NexusExportCreate,
    NexusExportOut,
    NexusGenerateRequest,
)

router = APIRouter(prefix="/nexus-repo", tags=["nexus-repo"])


def _require_feature():
    if not settings.nexus_repo_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Nexus Repo modülü şu an devre dışı. Etkinleştirmek için NEXUS_REPO_ENABLED=true ayarlayın.",
        )


def _run_in_thread(target, *args) -> None:
    t = threading.Thread(target=target, args=args, daemon=True)
    t.start()


# ── Health ────────────────────────────────────────────────────────────────────

@router.get("/health", response_model=NexusHealthOut, tags=["health"])
def health():
    return NexusHealthOut(status="ok", feature_enabled=settings.nexus_repo_enabled)


# ── Projects ──────────────────────────────────────────────────────────────────

@router.get("/projects", response_model=list[NexusProjectOut])
def list_projects(
    archived: bool = False,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    return service.list_projects(db, skip=skip, limit=limit, archived=archived)


@router.post("/projects", response_model=NexusProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    data: NexusProjectCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    return service.create_project(db, data)


@router.get("/projects/{project_id}", response_model=NexusProjectOut)
def get_project(
    project_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return project


@router.patch("/projects/{project_id}", response_model=NexusProjectOut)
def update_project(
    project_id: str,
    data: NexusProjectUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return service.update_project(db, project, data)


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_project(
    project_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    service.archive_project(db, project)


# ── Crawl ─────────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/crawls", response_model=list[NexusCrawlJobOut])
def list_crawls(
    project_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return service.list_crawl_jobs(db, project_id)


@router.post("/projects/{project_id}/crawls", response_model=NexusCrawlJobOut, status_code=status.HTTP_201_CREATED)
def start_crawl(
    project_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    """Repo tarama işini başlatır (arka planda daemon thread)."""
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    job = service.create_crawl_job(db, project_id)
    from .crawler import run_crawl_job
    _run_in_thread(run_crawl_job, job.id)
    return job


@router.get("/projects/{project_id}/crawls/{job_id}", response_model=NexusCrawlJobOut)
def get_crawl_job(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    from .models import NexusCrawlJob
    job = db.query(NexusCrawlJob).filter(
        NexusCrawlJob.id == job_id,
        NexusCrawlJob.project_id == project_id,
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="CrawlJob bulunamadı")
    return job


# ── Scenarios ─────────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/scenarios", response_model=list[NexusScenarioOut])
def list_scenarios(
    project_id: str,
    type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    return service.list_scenarios(db, project_id, type_filter=type, status_filter=status_filter, skip=skip, limit=limit)


@router.post("/projects/{project_id}/scenarios", response_model=NexusScenarioOut, status_code=status.HTTP_201_CREATED)
def create_scenario(
    project_id: str,
    data: NexusScenarioCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return service.create_scenario(db, project_id, data)


@router.patch("/projects/{project_id}/scenarios/{scenario_id}", response_model=NexusScenarioOut)
def update_scenario(
    project_id: str,
    scenario_id: str,
    data: NexusScenarioUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    scenario = service.get_scenario(db, scenario_id)
    if not scenario or scenario.project_id != project_id:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    return service.update_scenario(db, scenario, data)


@router.delete("/projects/{project_id}/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    project_id: str,
    scenario_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    scenario = service.get_scenario(db, scenario_id)
    if not scenario or scenario.project_id != project_id:
        raise HTTPException(status_code=404, detail="Senaryo bulunamadı")
    service.delete_scenario(db, scenario)


# ── Crawl Detayları (endpoints + files) ───────────────────────────────────────

@router.get("/projects/{project_id}/crawls/{job_id}/endpoints", response_model=list[NexusEndpointOut])
def list_endpoints(
    project_id: str,
    job_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    from .models import NexusCrawlJob
    job = db.query(NexusCrawlJob).filter(
        NexusCrawlJob.id == job_id, NexusCrawlJob.project_id == project_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="CrawlJob bulunamadı")
    return service.list_endpoints(db, job_id)


@router.get("/projects/{project_id}/crawls/{job_id}/files", response_model=list[NexusFileOut])
def list_files(
    project_id: str,
    job_id: str,
    with_summary: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    from .models import NexusCrawlJob
    job = db.query(NexusCrawlJob).filter(
        NexusCrawlJob.id == job_id, NexusCrawlJob.project_id == project_id
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="CrawlJob bulunamadı")
    return service.list_files(db, job_id, with_summary=with_summary)


# ── İstatistikler ─────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/stats", response_model=NexusStatsOut)
def get_stats(
    project_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    return service.get_project_stats(db, project_id)


# ── Generate (LLM) ────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/generate", status_code=status.HTTP_202_ACCEPTED)
def generate_scenarios(
    project_id: str,
    data: NexusGenerateRequest,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    """LLM ile senaryo üretimini başlatır (arka planda daemon thread)."""
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")

    from .llm_generator import run_generate_job
    _run_in_thread(
        run_generate_job,
        project_id,
        data.crawl_job_id,
        data.scenario_types,
        data.max_scenarios,
        data.language,
    )
    return {
        "message": "Senaryo üretimi arka planda başlatıldı",
        "crawl_job_id": data.crawl_job_id,
        "model": project.llm_model,
        "provider": project.llm_provider,
    }


# ── Exports ───────────────────────────────────────────────────────────────────

@router.post("/projects/{project_id}/exports", response_model=NexusExportOut, status_code=status.HTTP_201_CREATED)
def create_export(
    project_id: str,
    data: NexusExportCreate,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    """Dışa aktarım işini başlatır (arka planda daemon thread)."""
    project = service.get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Proje bulunamadı")
    export = service.create_export(db, project_id, data)
    from .exporter import run_export_job
    _run_in_thread(run_export_job, export.id)
    return export


@router.get("/projects/{project_id}/exports", response_model=list[NexusExportOut])
def list_exports(
    project_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    from .models import NexusExport
    return (
        db.query(NexusExport)
        .filter(NexusExport.project_id == project_id)
        .order_by(NexusExport.created_at.desc())
        .all()
    )


@router.get("/projects/{project_id}/exports/{export_id}/download")
def download_export(
    project_id: str,
    export_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(_require_feature),
):
    """Hazır export dosyasını indir."""
    from fastapi.responses import FileResponse
    from .models import NexusExport

    export = db.query(NexusExport).filter(
        NexusExport.id == export_id,
        NexusExport.project_id == project_id,
    ).first()
    if not export:
        raise HTTPException(status_code=404, detail="Export bulunamadı")
    if export.status != "done" or not export.file_path:
        raise HTTPException(status_code=409, detail=f"Export henüz hazır değil (durum: {export.status})")

    from pathlib import Path
    fpath = Path(export.file_path)
    if not fpath.is_file():
        raise HTTPException(status_code=404, detail="Export dosyası bulunamadı")

    media_types = {
        "gherkin": "text/plain",
        "postman": "application/json",
        "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "jira": "text/csv",
    }
    return FileResponse(
        path=fpath,
        filename=fpath.name,
        media_type=media_types.get(export.format, "application/octet-stream"),
    )
