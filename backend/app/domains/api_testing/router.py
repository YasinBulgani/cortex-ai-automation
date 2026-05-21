"""
API Testing Router — FastAPI Endpoint'leri
==========================================

Prefix: /api/v1/api-testing/projects/{project_id}/...

Gruplar:
  - /environments     — Ortam degisken yonetimi
  - /specs            — OpenAPI spec import + yonetim
  - /endpoints        — Spec endpoint envanteri
  - /test-cases       — Test case CRUD + execution
  - /chains           — API call chain yonetimi
  - /ai               — AI test generation
  - /execute          — Tek request calistirma
"""

import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.infra.database import get_db
from app.deps import get_current_user
from app.domains.api_testing.environment import resolve_string
from app.domains.api_testing.network_security import UnsafeTargetError, validate_outbound_url
from app.domains.api_testing.analytics_router import router as analytics_router
from app.domains.tspm.models import TspmProject, TspmProjectMember

from app.domains.api_testing.models import (
    ApiChain,
    ApiEndpoint,
    ApiEnvironment,
    ApiExecutionDetail,
    ApiSpec,
    ApiTestCase,
)
from app.domains.api_testing.schemas import (
    AIGenerateRequest,
    AIGenerateResponse,
    ChainCreate,
    ChainOut,
    EndpointOut,
    EnvironmentCreate,
    EnvironmentOut,
    EnvironmentUpdate,
    ExecuteRequest,
    ExecuteTestCasesRequest,
    ExecutionHistoryResponse,
    ExecutionResultOut,
    ExecutionRunDetailResponse,
    ExecutionSummaryOut,
    FlakyTestItem,
    FlakyTestListResponse,
    FlakyTrendItem,
    FlakyTrendResponse,
    QuarantineActionResponse,
    QuarantineItem,
    QuarantineListResponse,
    QuarantineRequest,
    SpecDetailOut,
    SpecImportRequest,
    SpecOut,
    TestCaseCreate,
    TestCaseOut,
    TestCaseUpdate,
    TrendResponse,
)

logger = logging.getLogger(__name__)


def _is_admin_user(user: Any) -> bool:
    for role in getattr(user, "roles", []):
        for role_permission in getattr(role, "permissions", []):
            if getattr(role_permission, "permission", "") == "admin.*":
                return True
    return False


def _require_project_access(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
) -> None:
    if not db.get(TspmProject, project_id):
        raise HTTPException(404, "Proje bulunamadi")
    if _is_admin_user(user):
        return
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(403, "Bu projeye erisim yetkiniz yok")


router = APIRouter(
    prefix="/api/v1/api-testing/projects/{project_id}",
    tags=["api-testing"],
    dependencies=[Depends(_require_project_access)],
)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENVIRONMENT CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/environments", response_model=EnvironmentOut, status_code=201)
def create_environment(
    project_id: str,
    body: EnvironmentCreate,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Yeni ortam degiskeni seti oluştur."""
    env = ApiEnvironment(
        project_id=project_id,
        name=body.name,
        description=body.description,
        variables=body.variables,
        sensitive_keys=body.sensitive_keys,
        is_default=body.is_default,
    )
    db.add(env)

    # is_default ise diger default'lari kaldır
    if body.is_default:
        db.query(ApiEnvironment).filter(
            ApiEnvironment.project_id == project_id,
            ApiEnvironment.id != env.id,
        ).update({"is_default": False})

    db.commit()
    db.refresh(env)
    return env


@router.get("/environments", response_model=List[EnvironmentOut])
def list_environments(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Proje ortamlarini listele."""
    return db.query(ApiEnvironment).filter(
        ApiEnvironment.project_id == project_id,
    ).order_by(ApiEnvironment.created_at).offset(offset).limit(limit).all()


@router.put("/environments/{env_id}", response_model=EnvironmentOut)
def update_environment(
    project_id: str,
    env_id: str,
    body: EnvironmentUpdate,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Ortam guncelle."""
    env = db.query(ApiEnvironment).filter(
        ApiEnvironment.id == env_id,
        ApiEnvironment.project_id == project_id,
    ).first()
    if not env:
        raise HTTPException(404, "Ortam bulunamadi")

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(env, k, v)

    db.commit()
    db.refresh(env)
    return env


@router.delete("/environments/{env_id}", status_code=204)
def delete_environment(
    project_id: str,
    env_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Ortam sil."""
    deleted = db.query(ApiEnvironment).filter(
        ApiEnvironment.id == env_id,
        ApiEnvironment.project_id == project_id,
    ).delete()
    if not deleted:
        raise HTTPException(404, "Ortam bulunamadi")
    db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPEC IMPORT & MANAGEMENT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/specs/import", response_model=SpecOut, status_code=201)
async def import_spec_endpoint(
    project_id: str,
    body: SpecImportRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """
    OpenAPI/Swagger spec import et (URL veya inline content).
    Spec parse edilir, endpoint'ler cikarilir, risk analizi yapilir.
    """
    from app.domains.api_testing.service import import_spec

    content = None

    if body.source_url:
        # URL'den indir
        try:
            validate_outbound_url(body.source_url)
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(body.source_url)
                resp.raise_for_status()
                content = resp.text
        except UnsafeTargetError as exc:
            raise HTTPException(400, f"Guvensiz spec URL'i: {exc}")
        except httpx.HTTPError as exc:
            logger.exception("Spec download failed for project %s from %s", project_id, body.source_url)
            raise HTTPException(400, f"Spec indirme hatasi: {exc}")
    elif body.content:
        content = body.content
    else:
        raise HTTPException(400, "source_url veya content gerekli")

    try:
        spec, analysis = import_spec(
            db, project_id, content,
            name=body.name,
            source_url=body.source_url,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    return spec


@router.post("/specs/upload", response_model=SpecOut, status_code=201)
async def upload_spec_file(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Spec dosyasi yükle (JSON/YAML)."""
    from app.domains.api_testing.service import import_spec

    content = await file.read()
    try:
        spec, _ = import_spec(
            db, project_id, content.decode("utf-8"),
            name=file.filename,
            source_file=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    return spec


@router.get("/specs", response_model=List[SpecOut])
def list_specs(
    project_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Proje spec'lerini listele."""
    return db.query(ApiSpec).filter(
        ApiSpec.project_id == project_id,
    ).order_by(ApiSpec.created_at.desc()).offset(offset).limit(limit).all()


@router.get("/specs/{spec_id}", response_model=SpecDetailOut)
def get_spec_detail(
    project_id: str,
    spec_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Spec detay — endpoint listesi dahil."""
    spec = db.query(ApiSpec).filter(
        ApiSpec.id == spec_id,
        ApiSpec.project_id == project_id,
    ).first()
    if not spec:
        raise HTTPException(404, "Spec bulunamadi")

    # Endpoint'leri yükle
    endpoints = db.query(ApiEndpoint).filter(
        ApiEndpoint.spec_id == spec_id,
    ).all()

    # Test case sayilarini ekle
    ep_out_list = []
    for ep in endpoints:
        tc_count = db.query(ApiTestCase).filter(
            ApiTestCase.endpoint_id == ep.id,
        ).count()
        ep_dict = EndpointOut.model_validate(ep).model_dump()
        ep_dict["test_case_count"] = tc_count
        ep_out_list.append(ep_dict)

    result = SpecOut.model_validate(spec).model_dump()
    result["endpoints"] = ep_out_list
    return result


@router.delete("/specs/{spec_id}", status_code=204)
def delete_spec(
    project_id: str,
    spec_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Spec ve iliskili endpoint'leri sil."""
    deleted = db.query(ApiSpec).filter(
        ApiSpec.id == spec_id,
        ApiSpec.project_id == project_id,
    ).delete()
    if not deleted:
        raise HTTPException(404, "Spec bulunamadi")
    db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENDPOINTS (Read-only — spec'ten turetilir)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/endpoints", response_model=List[EndpointOut])
def list_endpoints(
    project_id: str,
    spec_id: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    has_pii: Optional[bool] = Query(None),
    has_financial: Optional[bool] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Proje endpoint'lerini filtrele + listele."""
    q = db.query(ApiEndpoint).join(ApiSpec).filter(
        ApiSpec.project_id == project_id,
    )
    if spec_id:
        q = q.filter(ApiEndpoint.spec_id == spec_id)
    if risk_level:
        q = q.filter(ApiEndpoint.risk_level == risk_level)
    if has_pii is not None:
        q = q.filter(ApiEndpoint.has_pii == has_pii)
    if has_financial is not None:
        q = q.filter(ApiEndpoint.has_financial == has_financial)

    return q.order_by(ApiEndpoint.path).offset(offset).limit(limit).all()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TEST CASE CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/test-cases", response_model=TestCaseOut, status_code=201)
def create_test_case(
    project_id: str,
    body: TestCaseCreate,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Manuel test case oluştur."""
    tc = ApiTestCase(
        project_id=project_id,
        **body.model_dump(),
    )
    db.add(tc)
    db.commit()
    db.refresh(tc)
    return tc


@router.get("/test-cases", response_model=List[TestCaseOut])
def list_test_cases(
    project_id: str,
    endpoint_id: Optional[str] = Query(None),
    test_type: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
    ai_generated: Optional[bool] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Test case'leri filtrele + listele."""
    q = db.query(ApiTestCase).filter(ApiTestCase.project_id == project_id)
    if endpoint_id:
        q = q.filter(ApiTestCase.endpoint_id == endpoint_id)
    if test_type:
        q = q.filter(ApiTestCase.test_type == test_type)
    if review_status:
        q = q.filter(ApiTestCase.review_status == review_status)
    if ai_generated is not None:
        q = q.filter(ApiTestCase.ai_generated == ai_generated)
    if priority:
        q = q.filter(ApiTestCase.priority == priority)

    return q.order_by(ApiTestCase.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()


@router.get("/test-cases/{tc_id}", response_model=TestCaseOut)
def get_test_case(
    project_id: str,
    tc_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Test case detay."""
    tc = db.query(ApiTestCase).filter(
        ApiTestCase.id == tc_id,
        ApiTestCase.project_id == project_id,
    ).first()
    if not tc:
        raise HTTPException(404, "Test case bulunamadi")
    return tc


@router.put("/test-cases/{tc_id}", response_model=TestCaseOut)
def update_test_case(
    project_id: str,
    tc_id: str,
    body: TestCaseUpdate,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Test case guncelle."""
    tc = db.query(ApiTestCase).filter(
        ApiTestCase.id == tc_id,
        ApiTestCase.project_id == project_id,
    ).first()
    if not tc:
        raise HTTPException(404, "Test case bulunamadi")

    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(tc, k, v)

    # Review status degisirse reviewer_id set et
    if body.review_status and user:
        tc.reviewer_id = getattr(user, "id", None)

    db.commit()
    db.refresh(tc)
    return tc


@router.delete("/test-cases/{tc_id}", status_code=204)
def delete_test_case(
    project_id: str,
    tc_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Test case sil."""
    deleted = db.query(ApiTestCase).filter(
        ApiTestCase.id == tc_id,
        ApiTestCase.project_id == project_id,
    ).delete()
    if not deleted:
        raise HTTPException(404, "Test case bulunamadi")
    db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AI GENERATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/ai/generate", response_model=AIGenerateResponse)
def ai_generate_tests(
    project_id: str,
    body: AIGenerateRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """
    AI ile test case / guvenlik testi / chain üret.

    mode:
      - test_generation  : Kapsamli test case uretimi (9 kategori)
      - security_audit   : OWASP API Top 10 guvenlik testleri
      - chain_builder    : API call chain is akislari
    """
    from app.domains.api_testing.service import generate_tests_with_ai

    result = generate_tests_with_ai(
        db, project_id,
        spec_id=body.spec_id,
        endpoint_ids=body.endpoint_ids,
        mode=body.mode,
        regulations=body.regulations,
        test_types=body.test_types,
        max_tests_per_endpoint=body.max_tests_per_endpoint,
        owasp_focus=body.owasp_focus,
        additional_context=body.additional_context,
    )

    # Test case'leri yükle
    test_cases = []
    if result.get("test_case_ids"):
        test_cases = db.query(ApiTestCase).filter(
            ApiTestCase.id.in_(result["test_case_ids"]),
        ).all()

    return AIGenerateResponse(
        mode=result["mode"],
        generated_count=result["generated_count"],
        test_cases=[TestCaseOut.model_validate(tc) for tc in test_cases],
        security_findings=result.get("security_findings"),
        chains=result.get("chains"),
        warnings=result.get("warnings", []),
        ai_model=result.get("ai_model"),
        duration_ms=result.get("duration_ms", 0),
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXECUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/execute/single", response_model=ExecutionResultOut)
async def execute_single_request(
    project_id: str,
    body: ExecuteRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """
    Tek bir HTTP istegi çalıştır (Postman-style).
    Degisken cozumleme, assertion degerlendirme, schema dogrulama dahil.
    """
    from app.domains.api_testing.request_executor import execute_request
    from app.domains.api_testing.environment import merge_variables

    # Environment degiskenlerini al
    env_vars: Dict[str, str] = {}
    if body.environment_id:
        env = db.query(ApiEnvironment).filter(
            ApiEnvironment.id == body.environment_id,
            ApiEnvironment.project_id == project_id,
        ).first()
        if env:
            env_vars = env.variables or {}

    resolved_url = resolve_string(body.url, env_vars)
    try:
        validate_outbound_url(resolved_url)
    except UnsafeTargetError as exc:
        raise HTTPException(400, f"Guvensiz hedef URL: {exc}")

    result = await execute_request(
        method=body.method,
        url=body.url,
        headers=body.headers,
        params=body.params,
        body=body.body,
        variables=env_vars,
        assertions=body.assertions,
        expected_schema=body.expected_schema,
        timeout=body.timeout,
    )

    return ExecutionResultOut(
        method=result.method,
        url=result.url,
        status_code=result.status_code,
        response_size_bytes=result.response_size_bytes,
        total_ms=round(result.timing.total_ms, 2),
        passed=result.assertion_report.all_passed if result.assertion_report else (result.status_code or 0) < 400,
        error=result.error,
        assertion_results=[r.to_dict() for r in (result.assertion_report.results if result.assertion_report else [])],
        schema_valid=result.schema_valid,
        schema_errors=result.schema_errors,
        extracted_variables=result.extracted_variables,
        response_body=result.response_body[:50_000] if result.response_body else None,
        response_headers=result.response_headers,
    )


@router.post("/execute/test-cases", response_model=ExecutionSummaryOut)
async def execute_test_cases_endpoint(
    project_id: str,
    body: ExecuteTestCasesRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Toplu test case calistirma."""
    from app.domains.api_testing.service import execute_test_cases

    result = await execute_test_cases(
        db, project_id,
        body.test_case_ids,
        environment_id=body.environment_id,
        stop_on_failure=body.stop_on_failure,
    )

    return ExecutionSummaryOut(
        run_id=result["run_id"],
        total=result["total"],
        passed=result["passed"],
        failed=result["failed"],
        errors=result["errors"],
        duration_ms=result["duration_ms"],
        results=[ExecutionResultOut(**r) for r in result.get("results", [])],
    )


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CHAIN CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post("/chains", response_model=ChainOut, status_code=201)
def create_chain(
    project_id: str,
    body: ChainCreate,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """API call chain oluştur."""
    chain = ApiChain(
        project_id=project_id,
        **body.model_dump(),
    )
    db.add(chain)
    db.commit()
    db.refresh(chain)
    return chain


@router.get("/chains", response_model=List[ChainOut])
def list_chains(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Chain listesi."""
    return db.query(ApiChain).filter(
        ApiChain.project_id == project_id,
    ).order_by(ApiChain.created_at.desc()).all()


@router.get("/chains/{chain_id}", response_model=ChainOut)
def get_chain(
    project_id: str,
    chain_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Chain detay."""
    chain = db.query(ApiChain).filter(
        ApiChain.id == chain_id,
        ApiChain.project_id == project_id,
    ).first()
    if not chain:
        raise HTTPException(404, "Chain bulunamadi")
    return chain


@router.delete("/chains/{chain_id}", status_code=204)
def delete_chain(
    project_id: str,
    chain_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Chain sil."""
    deleted = db.query(ApiChain).filter(
        ApiChain.id == chain_id,
        ApiChain.project_id == project_id,
    ).delete()
    if not deleted:
        raise HTTPException(404, "Chain bulunamadi")
    db.commit()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DASHBOARD / STATS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/stats")
def get_api_testing_stats(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """API Testing modulu istatistikleri."""
    from app.domains.api_testing.query_service import build_api_testing_stats
    return build_api_testing_stats(db, project_id)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# EXECUTION HISTORY & TRENDS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/executions", response_model=ExecutionHistoryResponse)
def list_executions(
    project_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    test_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),  # passed / failed / mixed
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Paginated execution run listesi — her run'in ozeti."""
    from app.domains.api_testing.query_service import build_execution_history

    return build_execution_history(
        db,
        project_id,
        page=page,
        per_page=per_page,
        test_type=test_type,
        status=status,
    )


@router.get("/executions/{run_id}", response_model=ExecutionRunDetailResponse)
def get_execution_detail(
    project_id: str,
    run_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Tek bir run'in tam detayi — tüm assertion sonuclari dahil."""
    from app.domains.api_testing.query_service import build_execution_run_detail
    try:
        return build_execution_run_detail(db, project_id, run_id)
    except ValueError:
        raise HTTPException(404, "Run bulunamadi") from None


@router.get("/trends", response_model=TrendResponse)
def get_test_trends(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Aggregated trend verisi — gunluk pass/fail, avg response time, test type dagilimi."""
    from app.domains.api_testing.query_service import build_execution_trends

    return build_execution_trends(db, project_id, days=days)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# FLAKY TEST DETECTION & QUARANTINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/flaky", response_model=FlakyTestListResponse)
def get_flaky_tests(
    project_id: str,
    window_days: int = Query(30, ge=1, le=365),
    min_runs: int = Query(3, ge=1, le=100),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Flaky testleri tespit et — flaky_score'a gore sirali."""
    from app.domains.api_testing.flaky_detector import detect_flaky_tests

    items = detect_flaky_tests(
        db,
        project_id,
        window_days=window_days,
        min_runs=min_runs,
    )

    return FlakyTestListResponse(
        items=[FlakyTestItem(**item) for item in items],
        total_count=len(items),
        quarantine_threshold=0.6,
        investigate_threshold=0.3,
    )


@router.get("/flaky/trends", response_model=FlakyTrendResponse)
def get_flaky_test_trends(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Gunluk flaky test trend verisi."""
    from app.domains.api_testing.flaky_detector import get_flaky_trends

    items = get_flaky_trends(db, project_id, days=days)

    return FlakyTrendResponse(
        items=[FlakyTrendItem(**item) for item in items],
        days=days,
    )


@router.post(
    "/flaky/{test_case_id}/quarantine",
    response_model=QuarantineActionResponse,
)
def quarantine_test_case(
    project_id: str,
    test_case_id: str,
    body: QuarantineRequest,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Test case'i karantinaya al."""
    from app.domains.api_testing.flaky_detector import quarantine_test

    # Verify the test case belongs to this project
    tc = db.query(ApiTestCase).filter(
        ApiTestCase.id == test_case_id,
        ApiTestCase.project_id == project_id,
    ).first()
    if not tc:
        raise HTTPException(404, "Test case bulunamadi")

    try:
        result = quarantine_test(db, test_case_id, reason=body.reason)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

    return QuarantineActionResponse(**result)


@router.delete(
    "/flaky/{test_case_id}/quarantine",
    response_model=QuarantineActionResponse,
)
def unquarantine_test_case(
    project_id: str,
    test_case_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Test case'i karantinadan cikar."""
    from app.domains.api_testing.flaky_detector import unquarantine_test

    # Verify the test case belongs to this project
    tc = db.query(ApiTestCase).filter(
        ApiTestCase.id == test_case_id,
        ApiTestCase.project_id == project_id,
    ).first()
    if not tc:
        raise HTTPException(404, "Test case bulunamadi")

    try:
        result = unquarantine_test(db, test_case_id)
    except ValueError as exc:
        raise HTTPException(404, str(exc))

    return QuarantineActionResponse(**result)


@router.get("/quarantine", response_model=QuarantineListResponse)
def get_quarantine_list_endpoint(
    project_id: str,
    db: Session = Depends(get_db),
    user: Any = Depends(get_current_user),
):
    """Karantinaya alinmis test case'leri listele."""
    from app.domains.api_testing.flaky_detector import get_quarantine_list

    items = get_quarantine_list(db, project_id)

    return QuarantineListResponse(
        items=[QuarantineItem(**item) for item in items],
        total_count=len(items),
    )


# Coverage/prioritization/healing/assertion/security routes are split into a dedicated module.
router.include_router(analytics_router)
