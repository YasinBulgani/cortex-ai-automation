"""Neurex Management API.

Manual QA operation endpoints under /api/v1/test-management/*.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.deps import require_permission
from app.domains.test_management import comments_service, design_service, service, intelligence_service
from fastapi import File, UploadFile

from app.domains.test_management.intelligence_schemas import (
    RunIntelligenceReportOut,
    ETAPredictionOut,
    TesterProfileOut,
    AnomalyOut,
    CaseRiskScoreOut,
    ReleaseReadinessPredictionOut,
    TesterPerformanceOut,
)
from app.domains.test_management.schemas import (
    ALLOWED_COMMENT_ENTITY_TYPES,
    ALLOWED_TECHNIQUES,
    AuditEventOut,
    BvaRunCreate,
    CaseDataGenerateRequest,
    CaseDataRowIn,
    CaseDataRowOut,
    CaseParamSetCreate,
    CaseParamSetOut,
    DesignRunOut,
    EqRunCreate,
    ExpandCaseResponse,
    PromoteCasesRequest,
    PromoteCasesResponse,
    MgmtCommentCreate,
    MgmtCommentOut,
    MgmtCommentReact,
    MgmtCommentUpdate,
    MgmtNotificationCreate,
    MgmtNotificationOut,
    NotificationUnreadCount,
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
    RegressionSetAddCases,
    RegressionSetCreate,
    RegressionSetOut,
    RegressionSetUpdate,
    ReleaseReportOut,
    ReleaseSignoffCreate,
    ReleaseSignoffOut,
    RepositoryOut,
    RequirementCreate,
    RequirementLinkCreate,
    RequirementLinkOut,
    RequirementOut,
    RunCaseOut,
    RunCaseUpdate,
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
    TestFolderUpdate,
    TestImportJobCreate,
    TestImportJobOut,
    TestPlanCreate,
    TestPlanOut,
    TestRunCreate,
    TestRunOut,
    StandupOut,
    TestCaseCloneRequest,
    TestCaseImproveRequest,
    TestCaseImproveResponse,
    TestPlanAIGenerateRequest,
    TestPlanAIGenerateResponse,
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    TestSuiteCreate,
    TestSuiteOut,
    TestSuiteUpdate,
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


@router.patch("/projects/{project_id}/suites/{suite_id}", response_model=TestSuiteOut)
def update_suite(project_id: str, suite_id: str, payload: TestSuiteUpdate, db: DB, user: WriteUser) -> TestSuiteOut:
    try:
        return service.update_suite(db, project_id, suite_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/projects/{project_id}/suites/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_suite(project_id: str, suite_id: str, db: DB, user: WriteUser) -> None:
    try:
        service.delete_suite(db, project_id, suite_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/projects/{project_id}/folders/{folder_id}", response_model=TestFolderOut)
def update_folder(project_id: str, folder_id: str, payload: TestFolderUpdate, db: DB, user: WriteUser) -> TestFolderOut:
    try:
        return service.update_folder(db, project_id, folder_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/projects/{project_id}/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(project_id: str, folder_id: str, db: DB, user: WriteUser) -> None:
    try:
        service.delete_folder(db, project_id, folder_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@router.delete(
    "/projects/{project_id}/cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Test case'i kalıcı olarak sil",
)
def delete_case(project_id: str, case_id: str, db: DB, user: WriteUser) -> None:
    try:
        service.delete_case(db, project_id, case_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc



@router.post(
    "/projects/{project_id}/cases/{case_id}/clone",
    response_model=TestCaseOut,
    status_code=status.HTTP_201_CREATED,
    summary="Mevcut test case'i kopyalar",
)
def clone_case(project_id: str, case_id: str, payload: TestCaseCloneRequest, db: DB, user: WriteUser) -> TestCaseOut:
    try:
        return service.clone_case(db, project_id, case_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/improve",
    response_model=TestCaseImproveResponse,
    summary="AI ile mevcut test case'i iyileştir",
)
def improve_case(project_id: str, case_id: str, payload: TestCaseImproveRequest, db: DB, user: WriteUser) -> TestCaseImproveResponse:
    try:
        return service.improve_case(db, project_id, case_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"İyileştirme hatası: {exc}") from exc


@router.post(
    "/projects/{project_id}/cases/generate",
    response_model=TestCaseGenerateResponse,
    summary="AI ile test case üret (save=true ise DB'ye kaydeder)",
)
def generate_cases(project_id: str, payload: TestCaseGenerateRequest, db: DB, user: WriteUser) -> TestCaseGenerateResponse:
    try:
        cases = service.generate_test_cases(db, project_id, payload, user)
        return TestCaseGenerateResponse(cases=cases)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Üretim hatası: {exc}") from exc


@router.get(
    "/projects/{project_id}/standup",
    response_model=StandupOut,
    summary="Aktif run için standup verisini döner",
)
def get_standup(
    project_id: str,
    run_id: Optional[str] = Query(default=None),
    db: DB = Depends(get_db),
    _user: ReadUser = Depends(require_permission("read")),
) -> StandupOut:
    try:
        return service.get_standup(db, project_id, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/plans", response_model=TestPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(project_id: str, payload: TestPlanCreate, db: DB, user: WriteUser) -> TestPlanOut:
    return service.create_plan(db, project_id, payload, user)


@router.post(
    "/projects/{project_id}/plans/ai-generate",
    response_model=TestPlanAIGenerateResponse,
    summary="AI ile test planı önerileri üret",
)
def ai_generate_plan(project_id: str, payload: TestPlanAIGenerateRequest, db: DB, user: WriteUser) -> TestPlanAIGenerateResponse:
    try:
        return service.ai_generate_plan(db, project_id, payload, user)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan üretim hatası: {exc}") from exc


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


@router.patch(
    "/projects/{project_id}/regression/sets/{set_id}",
    response_model=RegressionSetOut,
)
def update_regression_set(
    project_id: str,
    set_id: str,
    payload: RegressionSetUpdate,
    db: DB,
    user: WriteUser,
) -> RegressionSetOut:
    return service.update_regression_set(db, project_id, set_id, payload, user)  # type: ignore[return-value]


@router.post(
    "/projects/{project_id}/regression/sets/{set_id}/cases",
    response_model=RegressionSetOut,
)
def add_cases_to_regression_set(
    project_id: str,
    set_id: str,
    payload: RegressionSetAddCases,
    db: DB,
    user: WriteUser,
) -> RegressionSetOut:
    return service.add_cases_to_regression_set(db, project_id, set_id, payload.case_ids, user)  # type: ignore[return-value]


@router.delete(
    "/projects/{project_id}/regression/sets/{set_id}/cases/{case_id}",
    response_model=RegressionSetOut,
)
def remove_case_from_regression_set(
    project_id: str,
    set_id: str,
    case_id: str,
    db: DB,
    user: WriteUser,
) -> RegressionSetOut:
    return service.remove_case_from_regression_set(db, project_id, set_id, case_id, user)  # type: ignore[return-value]


@router.delete(
    "/projects/{project_id}/regression/sets/{set_id}",
    status_code=204,
)
def delete_regression_set(
    project_id: str,
    set_id: str,
    db: DB,
    user: WriteUser,
) -> None:
    service.delete_regression_set(db, project_id, set_id, user)


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


@router.patch("/projects/{project_id}/run-cases/{run_case_id}", response_model=RunCaseOut)
def update_run_case(
    project_id: str,
    run_case_id: str,
    payload: RunCaseUpdate,
    db: DB,
    user: ExecuteUser,
) -> RunCaseOut:
    """Update the overall status of a test case in a run (TestRail-style case-level result)."""
    return service.update_run_case(db, project_id, run_case_id, payload, user)


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


# ── M-50 Threaded Comments ───────────────────────────────────────────────────


def _require_tenant(user: User) -> str:
    """Return the user's tenant_id or raise 403 if missing.

    Hardening against accidental cross-tenant queries: any caller without
    a tenant context cannot list/scope comment or notification data.
    """
    tenant_id = getattr(user, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="User has no tenant context")
    return str(tenant_id)


def _is_admin(user: User) -> bool:
    perms = getattr(user, "permissions", None) or []
    try:
        return "test_management.admin" in set(perms) or bool(getattr(user, "is_superuser", False))
    except TypeError:
        return bool(getattr(user, "is_superuser", False))


@router.post(
    "/comments",
    response_model=MgmtCommentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a threaded comment on a management entity",
)
def create_comment(payload: MgmtCommentCreate, db: DB, user: WriteUser) -> MgmtCommentOut:
    try:
        comment = comments_service.create_comment(db, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MgmtCommentOut.model_validate(comment)


@router.get(
    "/comments",
    response_model=list[MgmtCommentOut],
    summary="List comments for an entity (chronological, includes deleted-as-tombstone optionally)",
)
def list_comments(
    db: DB,
    user: ReadUser,
    entity_type: str = Query(..., min_length=1),
    entity_id: str = Query(..., min_length=1),
    include_deleted: bool = Query(default=False),
) -> list[MgmtCommentOut]:
    if entity_type not in ALLOWED_COMMENT_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="entity_type not allowed")
    tenant_id = _require_tenant(user)
    comments = comments_service.list_comments(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        include_deleted=include_deleted,
        tenant_id=tenant_id,
    )
    return [MgmtCommentOut.model_validate(c) for c in comments]


@router.patch(
    "/comments/{comment_id}",
    response_model=MgmtCommentOut,
    summary="Edit a comment (author only)",
)
def patch_comment(
    comment_id: str,
    payload: MgmtCommentUpdate,
    db: DB,
    user: WriteUser,
) -> MgmtCommentOut:
    try:
        comment = comments_service.update_comment(db, comment_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MgmtCommentOut.model_validate(comment)


@router.delete(
    "/comments/{comment_id}",
    response_model=MgmtCommentOut,
    summary="Soft-delete a comment (author or admin)",
)
def remove_comment(comment_id: str, db: DB, user: WriteUser) -> MgmtCommentOut:
    try:
        comment = comments_service.delete_comment(db, comment_id, user, is_admin=_is_admin(user))
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MgmtCommentOut.model_validate(comment)


@router.post(
    "/comments/{comment_id}/react",
    response_model=MgmtCommentOut,
    summary="Add or remove an emoji reaction on a comment",
)
def react_comment(
    comment_id: str,
    payload: MgmtCommentReact,
    db: DB,
    user: WriteUser,
) -> MgmtCommentOut:
    try:
        comment = comments_service.react_to_comment(db, comment_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MgmtCommentOut.model_validate(comment)


# ── M-45 Notification Inbox ──────────────────────────────────────────────────


@router.get(
    "/notifications",
    response_model=list[MgmtNotificationOut],
    summary="List the current user's notifications",
)
def list_notifications(
    db: DB,
    user: ReadUser,
    unread_only: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[MgmtNotificationOut]:
    tenant_id = _require_tenant(user)
    notifications = comments_service.list_notifications(
        db,
        user_id=str(user.id),
        tenant_id=tenant_id,
        unread_only=unread_only,
        include_archived=include_archived,
        limit=limit,
        project_id=project_id,
    )
    return [MgmtNotificationOut.model_validate(n) for n in notifications]


@router.get(
    "/notifications/unread-count",
    response_model=NotificationUnreadCount,
    summary="Lightweight badge count for the bell icon",
)
def unread_count(db: DB, user: ReadUser) -> NotificationUnreadCount:
    tenant_id = _require_tenant(user)
    unread, total = comments_service.count_notifications(
        db, user_id=str(user.id), tenant_id=tenant_id
    )
    return NotificationUnreadCount(unread=unread, total=total)


@router.post(
    "/notifications",
    response_model=MgmtNotificationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a notification for another user (admin)",
)
def create_notification(
    payload: MgmtNotificationCreate,
    db: DB,
    user: AdminUser,
) -> MgmtNotificationOut:
    try:
        n = comments_service.create_notification(db, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return MgmtNotificationOut.model_validate(n)


@router.post(
    "/notifications/{notification_id}/read",
    response_model=MgmtNotificationOut,
    summary="Mark a notification as read",
)
def read_notification(
    notification_id: str,
    db: DB,
    user: ReadUser,
) -> MgmtNotificationOut:
    try:
        n = comments_service.mark_read(db, notification_id=notification_id, user_id=str(user.id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MgmtNotificationOut.model_validate(n)


@router.post(
    "/notifications/{notification_id}/archive",
    response_model=MgmtNotificationOut,
    summary="Archive a notification",
)
def archive_notification(
    notification_id: str,
    db: DB,
    user: ReadUser,
) -> MgmtNotificationOut:
    try:
        n = comments_service.mark_archived(db, notification_id=notification_id, user_id=str(user.id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MgmtNotificationOut.model_validate(n)


@router.post(
    "/notifications/read-all",
    response_model=dict,
    summary="Mark every unread notification as read",
)
def read_all_notifications(db: DB, user: ReadUser) -> dict[str, int]:
    affected = comments_service.mark_all_read(db, user_id=str(user.id))
    return {"updated": affected}


@router.post(
    "/comments/summarize",
    summary="AI-generated TL;DR / decisions / open questions for a comment thread",
)
def summarize_comment_thread(
    payload: dict,
    db: DB,
    user: ReadUser,
) -> dict:
    entity_type = str(payload.get("entity_type") or "")
    entity_id = str(payload.get("entity_id") or "")
    if not entity_type or not entity_id:
        raise HTTPException(status_code=400, detail="entity_type and entity_id required")
    if entity_type not in ALLOWED_COMMENT_ENTITY_TYPES:
        raise HTTPException(status_code=400, detail="entity_type not allowed")
    tenant_id = _require_tenant(user)
    try:
        return comments_service.summarize_thread(
            db,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/notifications/digest",
    summary="AI-grouped digest of recent notifications for the current user",
)
def notifications_digest(
    db: DB,
    user: ReadUser,
    window: str = Query(default="24h", description="24h | 7d"),
) -> dict:
    tenant_id = _require_tenant(user)
    if window not in {"24h", "7d"}:
        raise HTTPException(status_code=400, detail="window must be 24h or 7d")
    return comments_service.digest_notifications(
        db,
        tenant_id=tenant_id,
        user_id=str(user.id),
        window=window,
    )


@router.get(
    "/notifications/stream",
    summary="Server-Sent Events stream of live notifications for the current user",
)
async def notification_stream(user: ReadUser) -> StreamingResponse:
    user_id = str(user.id)

    async def gen():
        async for chunk in comments_service.stream_events(user_id):
            yield chunk

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ── M-1 / M-2 / M-9 Design Techniques ────────────────────────────────────────


@router.post(
    "/design/bva",
    response_model=DesignRunOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Boundary Value Analysis run (LLM with deterministic fallback)",
)
def design_create_bva(payload: BvaRunCreate, db: DB, user: WriteUser) -> DesignRunOut:
    tenant_id = _require_tenant(user)
    try:
        return design_service.create_bva_run(db, tenant_id, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/design/eq",
    response_model=DesignRunOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate an Equivalence Partitioning run",
)
def design_create_eq(payload: EqRunCreate, db: DB, user: WriteUser) -> DesignRunOut:
    tenant_id = _require_tenant(user)
    try:
        return design_service.create_eq_run(db, tenant_id, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/design/runs",
    response_model=list[DesignRunOut],
    summary="List design technique runs for the current tenant",
)
def design_list_runs(
    db: DB,
    user: ReadUser,
    technique: Optional[str] = Query(default=None),
    requirement_id: Optional[str] = Query(default=None),
    project_id: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
) -> list[DesignRunOut]:
    tenant_id = _require_tenant(user)
    if technique and technique not in ALLOWED_TECHNIQUES:
        raise HTTPException(status_code=400, detail="technique not allowed")
    try:
        return design_service.list_design_runs(
            db,
            tenant_id,
            technique=technique,
            requirement_id=requirement_id,
            project_id=project_id,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/design/runs/{run_id}",
    response_model=DesignRunOut,
    summary="Get a single design technique run",
)
def design_get_run(run_id: str, db: DB, user: ReadUser) -> DesignRunOut:
    tenant_id = _require_tenant(user)
    try:
        return design_service.get_design_run(db, tenant_id, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/design/runs/{run_id}/promote",
    response_model=PromoteCasesResponse,
    summary="Promote selected generated drafts to real TestCase rows",
)
def design_promote(
    run_id: str,
    payload: PromoteCasesRequest,
    db: DB,
    user: WriteUser,
) -> PromoteCasesResponse:
    tenant_id = _require_tenant(user)
    try:
        ids = design_service.promote_cases(db, tenant_id, user, run_id, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PromoteCasesResponse(case_ids=ids)


@router.post(
    "/cases/{case_id}/params",
    response_model=CaseParamSetOut,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a parameter schema (M-9) to a TestCase",
)
def design_create_param_set(
    case_id: str,
    payload: CaseParamSetCreate,
    db: DB,
    user: WriteUser,
) -> CaseParamSetOut:
    tenant_id = _require_tenant(user)
    if payload.case_id != case_id:
        raise HTTPException(status_code=400, detail="case_id mismatch")
    try:
        ps = design_service.create_param_set(db, tenant_id, user, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return CaseParamSetOut.model_validate(ps)


@router.get(
    "/cases/{case_id}/params",
    response_model=list[CaseParamSetOut],
    summary="List parameter schemas attached to a TestCase",
)
def design_list_param_sets(case_id: str, db: DB, user: ReadUser) -> list[CaseParamSetOut]:
    tenant_id = _require_tenant(user)
    sets = design_service.list_param_sets(db, tenant_id, case_id)
    return [CaseParamSetOut.model_validate(s) for s in sets]


@router.post(
    "/cases/{case_id}/data",
    response_model=list[CaseDataRowOut],
    status_code=status.HTTP_201_CREATED,
    summary="Append data rows to a parameter set (manual / csv / llm-generated)",
)
def design_add_data_rows(
    case_id: str,
    payload: CaseDataGenerateRequest,
    db: DB,
    user: WriteUser,
) -> list[CaseDataRowOut]:
    tenant_id = _require_tenant(user)
    try:
        rows = design_service.generate_data_rows(db, tenant_id, user, payload)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return [CaseDataRowOut.model_validate(r) for r in rows]


@router.get(
    "/cases/{case_id}/params/{param_set_id}/data",
    response_model=list[CaseDataRowOut],
    summary="List data rows for a parameter set",
)
def design_list_data_rows(
    case_id: str,
    param_set_id: str,
    db: DB,
    user: ReadUser,
) -> list[CaseDataRowOut]:
    tenant_id = _require_tenant(user)
    try:
        rows = design_service.list_data_rows(db, tenant_id, param_set_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [CaseDataRowOut.model_validate(r) for r in rows]


@router.post(
    "/cases/{case_id}/params/{param_set_id}/rows",
    response_model=list[CaseDataRowOut],
    status_code=status.HTTP_201_CREATED,
    summary="Append manually-edited data rows to a parameter set",
)
def design_add_manual_rows(
    case_id: str,
    param_set_id: str,
    rows: list[CaseDataRowIn],
    db: DB,
    user: WriteUser,
) -> list[CaseDataRowOut]:
    tenant_id = _require_tenant(user)
    try:
        created = design_service.add_data_rows(db, tenant_id, user, param_set_id, rows)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return [CaseDataRowOut.model_validate(r) for r in created]


@router.post(
    "/cases/{case_id}/expand",
    response_model=ExpandCaseResponse,
    summary="Materialise one execution stub per data row across the case's param sets",
)
def design_expand_case(case_id: str, db: DB, user: WriteUser) -> ExpandCaseResponse:
    tenant_id = _require_tenant(user)
    try:
        result = design_service.expand_case(db, tenant_id, user, case_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ExpandCaseResponse(**result)


# ══════════════════════════════════════════════════════════════════════════════
# TEST ZEKÂ MOTORU — Intelligence Engine
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/projects/{project_id}/intelligence/runs/{run_id}",
    response_model=RunIntelligenceReportOut,
    summary="Bir koşum için tam zeka raporu: ETA, tester profilleri, anomaliler, risk sıralaması",
)
def run_intelligence(project_id: str, run_id: str, db: DB, _user: ReadUser) -> RunIntelligenceReportOut:
    try:
        report = intelligence_service.get_run_intelligence(db, project_id, run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return RunIntelligenceReportOut(
        run_id=report.run_id,
        run_name=report.run_name,
        generated_at=report.generated_at,
        eta=ETAPredictionOut(**report.eta.__dict__),
        testers=[TesterProfileOut(**t.__dict__) for t in report.testers],
        anomalies=[AnomalyOut(**a.__dict__) for a in report.anomalies],
        risk_sorted_remaining=[CaseRiskScoreOut(**c.__dict__) for c in report.risk_sorted_remaining],
        summary_health=report.summary_health,
        health_score=report.health_score,
    )


@router.get(
    "/projects/{project_id}/intelligence/runs/{run_id}/eta",
    response_model=ETAPredictionOut,
    summary="Koşum için hız tabanlı ETA tahmini",
)
def run_eta(project_id: str, run_id: str, db: DB, _user: ReadUser) -> ETAPredictionOut:
    from sqlalchemy import select as _select
    from app.domains.test_management.models import TestRun, TestRunCase

    run = db.execute(_select(TestRun).where(TestRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadı")

    run_cases = db.execute(
        _select(TestRunCase).where(TestRunCase.run_id == run_id)
    ).scalars().all()

    eta = intelligence_service._predict_eta(run, run_cases)
    return ETAPredictionOut(**eta.__dict__)


@router.get(
    "/projects/{project_id}/intelligence/runs/{run_id}/anomalies",
    response_model=list[AnomalyOut],
    summary="Koşumdaki anomalileri tespit et: takılı case, inaktif tester, yüksek blocked oranı",
)
def run_anomalies(project_id: str, run_id: str, db: DB, _user: ReadUser) -> list[AnomalyOut]:
    from sqlalchemy import select as _select
    from app.domains.test_management.models import TestRun, TestRunCase

    run = db.execute(_select(TestRun).where(TestRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadı")

    run_cases = db.execute(
        _select(TestRunCase).where(TestRunCase.run_id == run_id)
    ).scalars().all()

    eta = intelligence_service._predict_eta(run, run_cases)
    testers = intelligence_service._build_tester_profiles(run_cases)
    anomalies = intelligence_service._detect_anomalies(run, run_cases, testers, eta)
    return [AnomalyOut(**a.__dict__) for a in anomalies]


@router.get(
    "/projects/{project_id}/intelligence/runs/{run_id}/risk-queue",
    response_model=list[CaseRiskScoreOut],
    summary="Kalan case'leri risk skoruna göre sırala — en riskli önce",
)
def run_risk_queue(project_id: str, run_id: str, db: DB, _user: ReadUser) -> list[CaseRiskScoreOut]:
    from sqlalchemy import select as _select
    from app.domains.test_management.models import TestRunCase

    run_cases = db.execute(
        _select(TestRunCase).where(TestRunCase.run_id == run_id)
    ).scalars().all()

    scored = intelligence_service._risk_sort_remaining(db, run_cases)
    return [CaseRiskScoreOut(**c.__dict__) for c in scored]


@router.get(
    "/projects/{project_id}/intelligence/release-prediction",
    response_model=ReleaseReadinessPredictionOut,
    summary="Mevcut ilerlemeye göre release gate'e ulaşılıp ulaşılamayacağını tahmin et",
)
def release_prediction(project_id: str, db: DB, _user: ReadUser) -> ReleaseReadinessPredictionOut:
    result = intelligence_service.predict_release_readiness(db, project_id)
    return ReleaseReadinessPredictionOut(**result.__dict__)


@router.get(
    "/projects/{project_id}/intelligence/testers/{user_id}",
    response_model=TesterPerformanceOut,
    summary="Bir tester'ın bu proje genelindeki performans profili",
)
def tester_performance(project_id: str, user_id: str, db: DB, _user: ReadUser) -> TesterPerformanceOut:
    data = intelligence_service.get_tester_performance(db, project_id, user_id)
    return TesterPerformanceOut(**data)


# ── Tester Home: bana atanmış case'ler ───────────────────────────────────────

@router.get(
    "/projects/{project_id}/my-cases",
    summary="Aktif run'larda oturum açmış kullanıcıya atanmış case'leri döner",
)
def my_assigned_cases(project_id: str, db: DB, user: ReadUser) -> list[dict]:
    from sqlalchemy import select as _sel
    from app.domains.test_management.models import TestRun, TestRunCase, TestCycle

    rows = db.execute(
        _sel(TestRunCase, TestRun)
        .join(TestRun, TestRunCase.run_id == TestRun.id)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .where(TestRunCase.assigned_to == user.id)
        .where(TestRun.status.in_(["not_started", "in_progress"]))
        .order_by(TestRun.created_at.desc())
    ).all()

    result = []
    for rc, run in rows:
        snapshot = rc.case_snapshot or {}
        snap_case = snapshot.get("case", {})
        result.append({
            "run_case_id": rc.id,
            "run_id": run.id,
            "run_name": run.name,
            "run_status": run.status,
            "case_id": rc.case_id,
            "case_key": snap_case.get("case_key"),
            "title": snap_case.get("title"),
            "status": rc.status,
            "priority": snap_case.get("priority", "medium"),
            "started_at": rc.started_at.isoformat() if rc.started_at else None,
            "completed_at": rc.completed_at.isoformat() if rc.completed_at else None,
            "duration_seconds": rc.duration_seconds,
            "step_count": len(snapshot.get("steps", [])),
            "completed_steps": len(rc.step_results),
        })
    return result
