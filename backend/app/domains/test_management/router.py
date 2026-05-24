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
    DefectLinkCreate,
    DefectLinkOut,
    EvidenceOut,
    ExecutionSummaryOut,
    ImportJobDetailOut,
    ImportJobRowOut,
    ManagementProjectCreate,
    ManagementProjectOut,
    RepositoryOut,
    RequirementLinkCreate,
    RequirementLinkOut,
    RunCaseOut,
    RunDetailOut,
    StepResultUpdate,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
    TestCycleCreate,
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


@router.patch("/projects/{project_id}/cases/{case_id}", response_model=TestCaseOut)
def update_case(project_id: str, case_id: str, payload: TestCaseUpdate, db: DB, user: WriteUser) -> TestCaseOut:
    return service.update_case(db, project_id, case_id, payload, user)


@router.post("/projects/{project_id}/cases/{case_id}/archive", response_model=TestCaseOut)
def archive_case(project_id: str, case_id: str, db: DB, user: WriteUser) -> TestCaseOut:
    return service.archive_case(db, project_id, case_id, user)


@router.post("/projects/{project_id}/plans", response_model=TestPlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(project_id: str, payload: TestPlanCreate, db: DB, user: WriteUser) -> TestPlanOut:
    return service.create_plan(db, project_id, payload, user)


@router.post("/projects/{project_id}/cycles", status_code=status.HTTP_201_CREATED)
def create_cycle(project_id: str, payload: TestCycleCreate, db: DB, user: WriteUser) -> dict[str, str]:
    cycle = service.create_cycle(db, project_id, payload, user)
    return {"id": cycle.id, "status": cycle.status}


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
    _user: ExecuteUser,
    file: UploadFile = File(...),
) -> EvidenceOut:
    content = await file.read()
    result = service.upload_evidence(
        db,
        project_id=project_id,
        run_case_id=run_case_id,
        filename=file.filename or "evidence",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return EvidenceOut(**result)
