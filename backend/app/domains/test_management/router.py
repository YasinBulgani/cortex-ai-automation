"""Neurex Management API.

Manual QA operation endpoints under /api/v1/test-management/*.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.deps import require_permission
from app.domains.test_management import service
from fastapi import File, UploadFile

from app.domains.test_management.schemas import (
    AuditEventOut,
    DefectLinkCreate,
    DefectLinkOut,
    DefectLinkUpdate,
    EvidenceOut,
    ExecutionSummaryOut,
    ImportJobDetailOut,
    ImportJobRowOut,
    ManagementProjectCreate,
    ManagementProjectOut,
    ManagementSettingsOut,
    RegressionCandidateOut,
    RegressionSelectionFilter,
    RegressionSetCreate,
    RegressionSetOut,
    ReleaseReportOut,
    ReleaseSignoffCreate,
    ReleaseSignoffOut,
    RepositoryOut,
    RequirementCreate,
    RequirementLinkCreate,
    RequirementLinkOut,
    RequirementOut,
    RunCaseOut,
    RunDetailOut,
    SimilarCaseQuery,
    SimilarCaseResult,
    StepResultUpdate,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
    TestCaseVersionOut,
    TestCycleCreate,
    TestCycleOut,
    TestFolderCreate,
    TestFolderOut,
    TestImportJobCreate,
    TestImportJobOut,
    TestPlanCreate,
    TestPlanOut,
    TestRunCreate,
    TestRunOut,
    TestSuiteCreate,
    TestSuiteOut,
    TraceabilityRow,
)
from app.infra.database import get_db
from app.infra.models import User

router = APIRouter(prefix="/test-management", tags=["test-management"])

DB = Annotated[Session, Depends(get_db)]
ReadUser = Annotated[User, Depends(require_permission("test_management.read"))]
WriteUser = Annotated[User, Depends(require_permission("test_management.write"))]
ExecuteUser = Annotated[User, Depends(require_permission("test_management.execute"))]
AdminUser = Annotated[User, Depends(require_permission("test_management.admin"))]


@router.get("/health", summary="Neurex Management domain health")
def health() -> dict[str, str]:
    return {"status": "ok", "domain": "test_management"}


@router.get("/projects", response_model=list[ManagementProjectOut])
def list_projects(db: DB, _user: ReadUser) -> list[ManagementProjectOut]:
    return service.list_projects(db)


@router.post(
    "/projects",
    response_model=ManagementProjectOut,
    status_code=status.HTTP_201_CREATED,
)
def create_project(payload: ManagementProjectCreate, db: DB, user: AdminUser) -> ManagementProjectOut:
    return service.create_project(db, payload, user)


@router.get("/projects/{project_id}", response_model=ManagementProjectOut)
def get_project(project_id: str, db: DB, _user: ReadUser) -> ManagementProjectOut:
    return service.get_project(db, project_id)


@router.post(
    "/projects/by-tspm/{tspm_project_id}/ensure",
    response_model=ManagementProjectOut,
    status_code=status.HTTP_200_OK,
)
def ensure_project_for_tspm(tspm_project_id: str, db: DB, user: WriteUser) -> ManagementProjectOut:
    return service.ensure_project_for_tspm(db, tspm_project_id, user)


@router.get("/projects/{project_id}/settings", response_model=ManagementSettingsOut)
def get_settings(project_id: str, db: DB, _user: ReadUser) -> ManagementSettingsOut:
    return service.management_settings(db, project_id)  # type: ignore[return-value]


@router.get("/projects/{project_id}/audit-events", response_model=list[AuditEventOut])
def list_audit_events(
    project_id: str,
    db: DB,
    _user: ReadUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AuditEventOut]:
    return service.list_audit_events(db, project_id, limit=limit)


@router.get("/projects/{project_id}/repository", response_model=RepositoryOut)
def repository(project_id: str, db: DB, _user: ReadUser) -> RepositoryOut:
    return service.repository(db, project_id)


@router.get("/projects/{project_id}/export")
def export_repository(project_id: str, db: DB, _user: ReadUser) -> dict[str, object]:
    return service.export_repository(db, project_id)


@router.post("/projects/{project_id}/suites", response_model=TestSuiteOut, status_code=status.HTTP_201_CREATED)
def create_suite(project_id: str, payload: TestSuiteCreate, db: DB, user: WriteUser) -> TestSuiteOut:
    return service.create_suite(db, project_id, payload, user)


@router.post("/projects/{project_id}/folders", response_model=TestFolderOut, status_code=status.HTTP_201_CREATED)
def create_folder(project_id: str, payload: TestFolderCreate, db: DB, user: WriteUser) -> TestFolderOut:
    return service.create_folder(db, project_id, payload, user)


@router.get("/projects/{project_id}/cases", response_model=list[TestCaseOut])
def list_cases(
    project_id: str,
    db: DB,
    _user: ReadUser,
    q: Optional[str] = Query(default=None),
    include_archived: bool = False,
) -> list[TestCaseOut]:
    return service.list_cases(db, project_id, q=q, include_archived=include_archived)


@router.post("/projects/{project_id}/cases", response_model=TestCaseOut, status_code=status.HTTP_201_CREATED)
def create_case(project_id: str, payload: TestCaseCreate, db: DB, user: WriteUser) -> TestCaseOut:
    return service.create_case(db, project_id, payload, user)


@router.get("/projects/{project_id}/cases/{case_id}", response_model=TestCaseOut)
def get_case(project_id: str, case_id: str, db: DB, _user: ReadUser) -> TestCaseOut:
    return service.get_case(db, project_id, case_id)


@router.get("/projects/{project_id}/cases/{case_id}/versions", response_model=list[TestCaseVersionOut])
def list_case_versions(project_id: str, case_id: str, db: DB, _user: ReadUser) -> list[TestCaseVersionOut]:
    return service.list_case_versions(db, project_id, case_id)


@router.patch("/projects/{project_id}/cases/{case_id}", response_model=TestCaseOut)
def update_case(project_id: str, case_id: str, payload: TestCaseUpdate, db: DB, user: WriteUser) -> TestCaseOut:
    return service.update_case(db, project_id, case_id, payload, user)


@router.post("/projects/{project_id}/cases/{case_id}/archive", response_model=TestCaseOut)
def archive_case(project_id: str, case_id: str, db: DB, user: WriteUser) -> TestCaseOut:
    return service.archive_case(db, project_id, case_id, user)


@router.post("/projects/{project_id}/plans", response_model=TestPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(project_id: str, payload: TestPlanCreate, db: DB, user: WriteUser) -> TestPlanOut:
    return service.create_plan(db, project_id, payload, user)


@router.get("/projects/{project_id}/plans", response_model=list[TestPlanOut])
def list_plans(project_id: str, db: DB, _user: ReadUser) -> list[TestPlanOut]:
    return service.list_plans(db, project_id)


@router.get("/projects/{project_id}/cycles", response_model=list[TestCycleOut])
def list_cycles(
    project_id: str,
    db: DB,
    _user: ReadUser,
    plan_id: Optional[str] = Query(default=None),
) -> list[TestCycleOut]:
    return service.list_cycles(db, project_id, plan_id=plan_id)


@router.post("/projects/{project_id}/cycles", response_model=TestCycleOut, status_code=status.HTTP_201_CREATED)
def create_cycle(project_id: str, payload: TestCycleCreate, db: DB, user: WriteUser) -> TestCycleOut:
    return service.create_cycle(db, project_id, payload, user)


@router.post("/projects/{project_id}/regression/suggest", response_model=list[RegressionCandidateOut])
def suggest_regression_candidates(
    project_id: str,
    payload: RegressionSelectionFilter,
    db: DB,
    _user: ReadUser,
) -> list[RegressionCandidateOut]:
    return service.suggest_regression_candidates(db, project_id, payload)


@router.get("/projects/{project_id}/regression/sets", response_model=list[RegressionSetOut])
def list_regression_sets(project_id: str, db: DB, _user: ReadUser) -> list[RegressionSetOut]:
    return service.list_regression_sets(db, project_id)  # type: ignore[return-value]


@router.post(
    "/projects/{project_id}/regression/sets",
    response_model=RegressionSetOut,
    status_code=status.HTTP_201_CREATED,
)
def create_regression_set(
    project_id: str,
    payload: RegressionSetCreate,
    db: DB,
    user: WriteUser,
) -> RegressionSetOut:
    return service.create_regression_set(db, project_id, payload, user)  # type: ignore[return-value]


@router.get("/projects/{project_id}/runs", response_model=list[TestRunOut])
def list_runs(
    project_id: str,
    db: DB,
    _user: ReadUser,
    status: Optional[str] = Query(default=None, description="Filter by run status"),
) -> list[TestRunOut]:
    return service.list_runs(db, project_id, status_filter=status)


@router.post("/projects/{project_id}/runs", response_model=TestRunOut, status_code=status.HTTP_201_CREATED)
def create_run(project_id: str, payload: TestRunCreate, db: DB, user: WriteUser) -> TestRunOut:
    return service.create_run(db, project_id, payload, user)


@router.get("/projects/{project_id}/runs/{run_id}", response_model=RunDetailOut)
def get_run(project_id: str, run_id: str, db: DB, _user: ReadUser) -> RunDetailOut:
    return service.get_run(db, project_id, run_id)


@router.patch("/projects/{project_id}/run-cases/{run_case_id}/steps/{step_no}", response_model=RunCaseOut)
def update_step_result(
    project_id: str,
    run_case_id: str,
    step_no: int,
    payload: StepResultUpdate,
    db: DB,
    user: ExecuteUser,
) -> RunCaseOut:
    return service.update_step_result(db, project_id, run_case_id, step_no, payload, user)


@router.get("/projects/{project_id}/reports/execution-summary", response_model=ExecutionSummaryOut)
def execution_summary(project_id: str, db: DB, _user: ReadUser) -> ExecutionSummaryOut:
    return service.execution_summary(db, project_id)


@router.get("/projects/{project_id}/reports/release", response_model=ReleaseReportOut)
def release_report(project_id: str, db: DB, _user: ReadUser) -> ReleaseReportOut:
    return service.release_report(db, project_id)


@router.get("/projects/{project_id}/reports/release/signoffs", response_model=list[ReleaseSignoffOut])
def list_release_signoffs(project_id: str, db: DB, _user: ReadUser) -> list[ReleaseSignoffOut]:
    return service.list_release_signoffs(db, project_id)


@router.post(
    "/projects/{project_id}/reports/release/signoffs",
    response_model=ReleaseSignoffOut,
    status_code=status.HTTP_201_CREATED,
)
def create_release_signoff(
    project_id: str,
    payload: ReleaseSignoffCreate,
    db: DB,
    user: WriteUser,
) -> ReleaseSignoffOut:
    return service.create_release_signoff(db, project_id, payload, user)


@router.get("/projects/{project_id}/requirements/traceability", response_model=list[TraceabilityRow])
def requirement_traceability(project_id: str, db: DB, _user: ReadUser) -> list[TraceabilityRow]:
    """Return the requirements ↔ test-case traceability matrix."""
    return service.requirement_traceability(db, project_id)  # type: ignore[return-value]


@router.get("/projects/{project_id}/requirements/catalog", response_model=list[RequirementOut])
def list_requirements(project_id: str, db: DB, _user: ReadUser) -> list[RequirementOut]:
    return service.list_requirements(db, project_id)


@router.post(
    "/projects/{project_id}/requirements/catalog",
    response_model=RequirementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement(
    project_id: str,
    payload: RequirementCreate,
    db: DB,
    user: WriteUser,
) -> RequirementOut:
    return service.create_requirement(db, project_id, payload, user)


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementLinkOut])
def list_requirement_links(
    project_id: str,
    db: DB,
    _user: ReadUser,
    case_id: Optional[str] = Query(default=None),
) -> list[RequirementLinkOut]:
    return service.list_requirement_links(db, project_id, case_id=case_id)


@router.post(
    "/projects/{project_id}/requirements",
    response_model=RequirementLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def create_requirement_link(
    project_id: str,
    payload: RequirementLinkCreate,
    db: DB,
    user: WriteUser,
) -> RequirementLinkOut:
    return service.create_requirement_link(db, project_id, payload, user)


@router.get("/projects/{project_id}/defects", response_model=list[DefectLinkOut])
def list_defect_links(project_id: str, db: DB, _user: ReadUser) -> list[DefectLinkOut]:
    return service.list_defect_links(db, project_id)


@router.post(
    "/projects/{project_id}/defects",
    response_model=DefectLinkOut,
    status_code=status.HTTP_201_CREATED,
)
def create_defect_link(project_id: str, payload: DefectLinkCreate, db: DB, user: WriteUser) -> DefectLinkOut:
    return service.create_defect_link(db, project_id, payload, user)


@router.patch("/projects/{project_id}/defects/{defect_id}", response_model=DefectLinkOut)
def update_defect_link(
    project_id: str,
    defect_id: str,
    payload: DefectLinkUpdate,
    db: DB,
    user: WriteUser,
) -> DefectLinkOut:
    return service.update_defect_link(db, project_id, defect_id, payload, user)


@router.get("/projects/{project_id}/imports", response_model=list[TestImportJobOut])
def list_import_jobs(project_id: str, db: DB, _user: ReadUser) -> list[TestImportJobOut]:
    return service.list_import_jobs(db, project_id)


@router.get("/projects/{project_id}/imports/{job_id}", response_model=ImportJobDetailOut)
def get_import_job(project_id: str, job_id: str, db: DB, _user: ReadUser) -> ImportJobDetailOut:
    return service.get_import_job(db, project_id, job_id)


@router.post(
    "/projects/{project_id}/imports/{job_id}/commit",
    response_model=TestImportJobOut,
)
def commit_import_job(project_id: str, job_id: str, db: DB, user: WriteUser) -> TestImportJobOut:
    return service.commit_import_job(db, project_id, job_id, user)


@router.post(
    "/projects/{project_id}/imports",
    response_model=TestImportJobOut,
    status_code=status.HTTP_201_CREATED,
)
def create_import_job(project_id: str, payload: TestImportJobCreate, db: DB, user: WriteUser) -> TestImportJobOut:
    return service.create_import_job(db, project_id, payload, user)


@router.post(
    "/projects/{project_id}/cases/search-similar",
    response_model=list[SimilarCaseResult],
    summary="Semantic similarity search across test cases",
)
def search_similar_cases(
    project_id: str,
    payload: SimilarCaseQuery,
    db: DB,
    _user: ReadUser,
) -> list[SimilarCaseResult]:
    """Find test cases semantically similar to a natural-language query.

    Uses the AI Gateway embedding model (bge-m3 / multilingual) to compute
    cosine similarity.  Returns an empty list when the gateway is unavailable.
    """
    from app.domains.test_management.semantic_search import find_similar_cases

    results = find_similar_cases(
        db,
        project_id,
        payload.query,
        k=payload.k,
        min_score=payload.min_score,
        exclude_case_id=payload.exclude_case_id,
    )
    return [
        SimilarCaseResult(
            case_id=r.case_id,
            case_key=r.case_key,
            title=r.title,
            score=r.score,
            project_id=r.project_id,
            tags=r.tags,
            last_run_status=r.last_run_status,
        )
        for r in results
    ]


@router.post(
    "/projects/{project_id}/runs/{run_id}/cases/{run_case_id}/evidence",
    response_model=EvidenceOut,
    status_code=status.HTTP_201_CREATED,
    summary="Upload evidence file for a run case",
)
async def upload_evidence(
    project_id: str,
    run_id: str,
    run_case_id: str,
    db: DB,
    user: ExecuteUser,
    file: UploadFile = File(...),
) -> EvidenceOut:
    content = await file.read()
    result = service.upload_evidence(
        db,
        project_id=project_id,
        run_id=run_id,
        run_case_id=run_case_id,
        filename=file.filename or "evidence",
        content_type=file.content_type or "application/octet-stream",
        content=content,
        user=user,
    )
    return EvidenceOut(**result)


@router.get(
    "/projects/{project_id}/runs/{run_id}/cases/{run_case_id}/evidence",
    response_model=list[EvidenceOut],
    summary="List evidence files for a run case",
)
def list_evidence(
    project_id: str,
    run_id: str,
    run_case_id: str,
    db: DB,
    _user: ReadUser,
) -> list[EvidenceOut]:
    return [EvidenceOut(**item) for item in service.list_evidence(db, project_id, run_id, run_case_id)]
