"""qa/ REST API endpoints.

Frontend (`apps/web/app/(dashboard)/qa/`) ve external bot'lar buradan
qa/ klasörü ile etkileşir. Read endpoint'leri her zaman; write
endpoint'leri (POST run, PATCH TC) admin permission gerektirir.

Mount prefix: /api/v1/qa (router_registry'de)
"""
from __future__ import annotations

import logging
from typing import List, Optional

from fastapi import APIRouter, Body, HTTPException, Path, Query, status

from . import service
from .models import (
    CoverageResponse,
    CreateRunRequest,
    CreateTestCaseRequest,
    HealthReport,
    OpenDefectIssueRequest,
    OpenDefectIssueResponse,
    Plan,
    PreCondition,
    Requirement,
    TestCase,
    TestCaseListResponse,
    TestRun,
    TestRunListItem,
    UpdateTestCaseRequest,
)

router = APIRouter(prefix="/qa", tags=["qa"])
logger = logging.getLogger(__name__)


# ── Cases ───────────────────────────────────────────────────────────────

@router.get("/cases", response_model=TestCaseListResponse)
def list_cases(
    suite: Optional[str] = Query(None),
    priority: Optional[str] = Query(None, pattern="^P[0-3]$"),
    automation_status: Optional[str] = Query(None),
    search: Optional[str] = Query(None, max_length=120),
    limit: int = Query(200, ge=1, le=1000),
) -> TestCaseListResponse:
    items = service.list_test_cases(
        suite=suite,
        priority=priority,
        automation_status=automation_status,
        search=search,
    )
    return TestCaseListResponse(total=len(items), items=items[:limit])


@router.get("/cases/{tc_id}", response_model=TestCase)
def get_case(tc_id: str = Path(..., pattern="^TC-[A-Z0-9]+-\\d+$")) -> TestCase:
    tc = service.get_test_case(tc_id)
    if not tc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"TC not found: {tc_id}")
    return tc


@router.post("/cases", response_model=TestCase, status_code=status.HTTP_201_CREATED)
def create_case(req: CreateTestCaseRequest) -> TestCase:
    try:
        return service.create_test_case(req)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))


@router.patch("/cases/{tc_id}", response_model=TestCase)
def update_case(
    tc_id: str = Path(..., pattern="^TC-[A-Z0-9]+-\\d+$"),
    req: UpdateTestCaseRequest = Body(...),
) -> TestCase:
    updates = req.model_dump(exclude_none=True)
    tc = service.update_test_case(tc_id, updates)
    if not tc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"TC not found: {tc_id}")
    return tc


# ── Runs ────────────────────────────────────────────────────────────────

@router.get("/runs", response_model=List[TestRunListItem])
def list_runs(limit: int = Query(50, ge=1, le=500)) -> List[TestRunListItem]:
    return service.list_runs()[:limit]


@router.get("/runs/{run_id}", response_model=TestRun)
def get_run(run_id: str = Path(..., pattern="^TR-\\d{4}-\\d{2}-\\d{2}-[A-Z0-9-]+-\\d+$")) -> TestRun:
    run = service.get_run(run_id)
    if not run:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Run not found: {run_id}")
    return run


@router.post("/runs", response_model=TestRun, status_code=status.HTTP_201_CREATED)
def create_run(req: CreateRunRequest) -> TestRun:
    return service.create_run(
        plan=req.plan,
        executor=req.executor,
        environment=req.environment.model_dump(),
        results=[r.model_dump() for r in req.results],
    )


# ── Plans ───────────────────────────────────────────────────────────────

@router.get("/plans", response_model=List[Plan])
def list_plans() -> List[Plan]:
    return service.list_plans()


# ── Requirements ────────────────────────────────────────────────────────

@router.get("/requirements", response_model=List[Requirement])
def list_requirements() -> List[Requirement]:
    return service.list_requirements()


# ── Pre-conditions ──────────────────────────────────────────────────────

@router.get("/pre-conditions", response_model=List[PreCondition])
def list_pre_conditions() -> List[PreCondition]:
    return service.list_pre_conditions()


# ── Coverage + Health ───────────────────────────────────────────────────

@router.get("/coverage", response_model=CoverageResponse)
def coverage() -> CoverageResponse:
    return service.coverage_summary()


@router.get("/health", response_model=HealthReport)
def health() -> HealthReport:
    return service.health_score()


# ── Defect Issue (GitHub bridge) ────────────────────────────────────────

@router.post("/defects/open-issue", response_model=OpenDefectIssueResponse)
def open_defect_issue(req: OpenDefectIssueRequest) -> OpenDefectIssueResponse:
    """Failed run → GitHub Issue (qa-defect label).

    Şu an dry-run modunda — gerçek `gh issue create` çağrısı
    GITHUB_TOKEN + gh CLI gerektirir. Production'da bu endpoint
    `subprocess.run(["gh", "issue", "create", ...])` çağıracak.
    """
    body = (
        f"### İlgili Test Case\n{req.tc_id}\n\n"
        f"### Bulunduğu Run\n{req.run_id or '(belirtilmedi)'}\n\n"
        f"### Severity\n{req.severity}\n\n"
        f"### Tekrar üretme adımları\n{req.reproduce}\n\n"
        f"### Beklenen davranış\n{req.expected}\n\n"
        f"### Gerçekleşen davranış\n{req.actual}\n\n"
        f"### Ortam\n{req.environment or '-'}\n"
    )
    return OpenDefectIssueResponse(
        dry_run=True,
        message=(
            "Dry-run — `gh issue create` çağrısı production'da yapılır. "
            f"Title: {req.title} | TC: {req.tc_id}"
        ),
    )
