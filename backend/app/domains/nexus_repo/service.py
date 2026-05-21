"""Nexus Repo servis katmanı — CRUD + iş mantığı stub'ları."""

from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from .models import (
    NexusProject, NexusCrawlJob, NexusScenario, NexusExport,
    NexusEndpoint, NexusFile,
)
from .schemas import (
    NexusProjectCreate, NexusProjectUpdate,
    NexusScenarioCreate, NexusScenarioUpdate,
    NexusExportCreate, NexusStatsOut,
)


# ── Project CRUD ──────────────────────────────────────────────────────────────

def list_projects(db: Session, *, skip: int = 0, limit: int = 50, archived: bool = False) -> list[NexusProject]:
    return (
        db.query(NexusProject)
        .filter(NexusProject.archived == archived)
        .order_by(NexusProject.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_project(db: Session, project_id: str) -> Optional[NexusProject]:
    return db.query(NexusProject).filter(NexusProject.id == project_id).first()


def create_project(db: Session, data: NexusProjectCreate, *, created_by: Optional[str] = None) -> NexusProject:
    project = NexusProject(**data.model_dump(), created_by=created_by)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def update_project(db: Session, project: NexusProject, data: NexusProjectUpdate) -> NexusProject:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(project, field, value)
    db.commit()
    db.refresh(project)
    return project


def archive_project(db: Session, project: NexusProject) -> NexusProject:
    project.archived = True
    db.commit()
    db.refresh(project)
    return project


# ── CrawlJob ──────────────────────────────────────────────────────────────────

def list_crawl_jobs(db: Session, project_id: str) -> list[NexusCrawlJob]:
    return (
        db.query(NexusCrawlJob)
        .filter(NexusCrawlJob.project_id == project_id)
        .order_by(NexusCrawlJob.created_at.desc())
        .all()
    )


def create_crawl_job(db: Session, project_id: str) -> NexusCrawlJob:
    job = NexusCrawlJob(project_id=project_id)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


# ── Scenario CRUD ─────────────────────────────────────────────────────────────

def list_scenarios(
    db: Session,
    project_id: str,
    *,
    type_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list[NexusScenario]:
    q = db.query(NexusScenario).filter(NexusScenario.project_id == project_id)
    if type_filter:
        q = q.filter(NexusScenario.type == type_filter)
    if status_filter:
        q = q.filter(NexusScenario.status == status_filter)
    return q.order_by(NexusScenario.created_at.desc()).offset(skip).limit(limit).all()


def get_scenario(db: Session, scenario_id: str) -> Optional[NexusScenario]:
    return db.query(NexusScenario).filter(NexusScenario.id == scenario_id).first()


def create_scenario(
    db: Session,
    project_id: str,
    data: NexusScenarioCreate,
    *,
    created_by: Optional[str] = None,
) -> NexusScenario:
    scenario = NexusScenario(**data.model_dump(), project_id=project_id, created_by=created_by)
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


def update_scenario(db: Session, scenario: NexusScenario, data: NexusScenarioUpdate) -> NexusScenario:
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(scenario, field, value)
    db.commit()
    db.refresh(scenario)
    return scenario


def delete_scenario(db: Session, scenario: NexusScenario) -> None:
    db.delete(scenario)
    db.commit()


# ── Crawl detayları ───────────────────────────────────────────────────────────

def list_endpoints(db: Session, crawl_job_id: str) -> list[NexusEndpoint]:
    return (
        db.query(NexusEndpoint)
        .filter(NexusEndpoint.crawl_job_id == crawl_job_id)
        .order_by(NexusEndpoint.method, NexusEndpoint.path)
        .all()
    )


def list_files(db: Session, crawl_job_id: str, *, with_summary: Optional[bool] = None) -> list[NexusFile]:
    q = db.query(NexusFile).filter(NexusFile.crawl_job_id == crawl_job_id)
    if with_summary is True:
        q = q.filter(NexusFile.summary.isnot(None))
    return q.order_by(NexusFile.path).all()


# ── İstatistikler ─────────────────────────────────────────────────────────────

def get_project_stats(db: Session, project_id: str) -> NexusStatsOut:
    from sqlalchemy import func

    scenarios = db.query(NexusScenario).filter(NexusScenario.project_id == project_id).all()

    by_type: dict[str, int] = {}
    by_status: dict[str, int] = {}
    by_priority: dict[str, int] = {}
    for s in scenarios:
        by_type[s.type] = by_type.get(s.type, 0) + 1
        by_status[s.status] = by_status.get(s.status, 0) + 1
        by_priority[s.priority] = by_priority.get(s.priority, 0) + 1

    crawl_jobs = (
        db.query(NexusCrawlJob)
        .filter(NexusCrawlJob.project_id == project_id)
        .order_by(NexusCrawlJob.created_at.desc())
        .all()
    )
    last_job = next((j for j in crawl_jobs if j.status == "done"), None)
    total_endpoints = sum(j.endpoints_found for j in crawl_jobs if j.status == "done")
    total_files = sum(j.files_scanned for j in crawl_jobs if j.status == "done")

    return NexusStatsOut(
        total_scenarios=len(scenarios),
        by_type=by_type,
        by_status=by_status,
        by_priority=by_priority,
        total_crawl_jobs=len(crawl_jobs),
        last_crawl_at=last_job.finished_at if last_job else None,
        total_endpoints=total_endpoints,
        total_files=total_files,
    )


# ── Export ────────────────────────────────────────────────────────────────────

def create_export(
    db: Session,
    project_id: str,
    data: NexusExportCreate,
    *,
    created_by: Optional[str] = None,
) -> NexusExport:
    export = NexusExport(**data.model_dump(), project_id=project_id, created_by=created_by)
    db.add(export)
    db.commit()
    db.refresh(export)
    return export
