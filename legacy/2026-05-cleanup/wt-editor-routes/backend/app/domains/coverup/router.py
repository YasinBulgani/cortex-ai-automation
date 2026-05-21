"""CoverUp — Coverage-guided test generation API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User
from app.domains.tspm.models import TspmProject, TspmProjectMember

from .repository import CoverageReportRepository
from .schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    CoverageReport,
    CoverageReportListItem,
    CoverageUploadRequest,
    GenerateTestRequest,
    GenerateTestResponse,
    TrendResponse,
)
from .service import (
    analyze_report,
    build_trend_response,
    create_report,
    generate_tests,
    get_report_or_404,
)

router = APIRouter(prefix="/coverup", tags=["coverup"])

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _repository(db: Session) -> CoverageReportRepository:
    return CoverageReportRepository(db)


def _is_admin_user(user: User) -> bool:
    for role in user.roles:
        for role_permission in role.permissions:
            if role_permission.permission == "admin.*":
                return True
    return False


def _accessible_project_ids(db: Session, user: User) -> set[str] | None:
    if _is_admin_user(user):
        return None
    project_rows = db.scalars(
        select(TspmProject.id)
        .join(TspmProjectMember, TspmProjectMember.project_id == TspmProject.id)
        .where(TspmProjectMember.user_id == user.id)
    ).all()
    return set(project_rows)


def _require_project_access(project_id: str, db: Session, user: User) -> TspmProject:
    project = db.get(TspmProject, project_id)
    if not project:
        raise HTTPException(404, "Proje bulunamadi")
    allowed_ids = _accessible_project_ids(db, user)
    if allowed_ids is not None and project.id not in allowed_ids:
        raise HTTPException(403, "Bu projeye erisim yetkiniz yok")
    return project


@router.post("/upload", response_model=CoverageReport)
def upload_coverage(
    body: CoverageUploadRequest,
    db: DB,
    user: CurrentUser,
) -> CoverageReport:
    """Coverage raporu yukle ve kalici olarak sakla."""
    project = _require_project_access(body.project_id, db, user)
    sanitized_body = body.model_copy(
        update={"project_id": project.id, "project_name": project.name}
    )
    return create_report(_repository(db), sanitized_body)


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_coverage(
    body: AnalyzeRequest,
    db: DB,
    user: CurrentUser,
) -> AnalyzeResponse:
    """Coverage gap'lerini analiz et ve hedefleri belirle."""
    report = get_report_or_404(
        _repository(db),
        body.report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )
    return analyze_report(report, body)


@router.post("/generate", response_model=GenerateTestResponse)
def generate_coverage_tests(
    body: GenerateTestRequest,
    db: DB,
    user: CurrentUser,
) -> GenerateTestResponse:
    """Kapsanmayan kod icin test uret ve metadata'sini sakla."""
    repository = _repository(db)
    report = get_report_or_404(
        repository,
        body.report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )
    return generate_tests(repository, report, body)


@router.get("/reports", response_model=list[CoverageReportListItem])
def list_reports(
    db: DB,
    user: CurrentUser,
    project_id: str | None = Query(default=None),
) -> list[CoverageReportListItem]:
    """Tum coverage raporlarini listele."""
    repository = _repository(db)
    if project_id:
        project = _require_project_access(project_id, db, user)
        return repository.list_reports(project_ids={project.id})
    return repository.list_reports(project_ids=_accessible_project_ids(db, user))


@router.get("/reports/{report_id}", response_model=CoverageReport)
def get_report(
    report_id: str,
    db: DB,
    user: CurrentUser,
) -> CoverageReport:
    """Belirli bir coverage raporunu getir."""
    return get_report_or_404(
        _repository(db),
        report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )


@router.get("/trends", response_model=TrendResponse)
def get_trends(
    db: DB,
    user: CurrentUser,
    project_id: str | None = Query(default=None),
) -> TrendResponse:
    """Coverage trendlerini getir."""
    repository = _repository(db)
    if project_id:
        project = _require_project_access(project_id, db, user)
        return build_trend_response(repository.list_trend_points(project_ids={project.id}))
    return build_trend_response(
        repository.list_trend_points(project_ids=_accessible_project_ids(db, user))
    )


@router.post("/targets", response_model=AnalyzeResponse)
def banking_targets(
    body: AnalyzeRequest,
    db: DB,
    user: CurrentUser,
) -> AnalyzeResponse:
    """Bankacilik-kritik kapsam hedeflerini belirle."""
    report = get_report_or_404(
        _repository(db),
        body.report_id,
        allowed_project_ids=_accessible_project_ids(db, user),
    )
    return analyze_report(report, body, banking_only=True)
