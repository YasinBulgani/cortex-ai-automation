"""TSPM router — projects, scenarios, executions, flows, regression, approvals, imports,
requirements, versions, schedules, test-data, integrations, api-testing, members,
faz3: ai test case generation + bulk review."""

from __future__ import annotations

import json
import logging
import os
import ipaddress
import re
import socket
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional, Union
from urllib.parse import urlparse

import httpx
import jwt
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user, get_optional_user, require_permission
from app.domains.auth.service import decode_token
from app.domains.tspm.scheduler import add_schedule_job, remove_schedule_job, compute_next_run, _run_schedule_job
from app.domains.auth.permissions import Permission
from app.infra.database import get_db
from app.infra.models import User
from app.domains.tspm.models import (
    TspmAiBatch,
    TspmApiCollection,
    TspmApiRequest,
    TspmApiTestRun,
    TspmApproval,
    TspmAutomationArtifact,
    TspmExecution,
    TspmExecutionMetrics,
    TspmExecutionResult,
    TspmFlow,
    TspmImport,
    TspmIntegration,
    TspmProject,
    TspmProjectMember,
    TspmRegressionSet,
    TspmRequirement,
    TspmScenario,
    TspmScenarioDataBinding,
    TspmScenarioRequirement,
    TspmScenarioVersion,
    TspmSchedule,
    TspmN8nExecution,
    TspmN8nWorkflow,
    TspmTestCase,
    TspmTestDataSet,
    utcnow,
)
from app.domains.tspm.schemas import (
    AcceptSuggestedSetsRequest,
    AddScenariosRequest,
    ApiCollectionCreate,
    ApiCollectionDetailOut,
    ApiCollectionOut,
    ApiRequestCreate,
    ApiRequestOut,
    ApiRequestUpdate,
    ApiTestRunOut,
    PostmanImportRequest,
    PostmanImportResponse,
    ApprovalCreate,
    ApprovalOut,
    AutomationArtifactOut,
    BddGenerateRequest,
    BddGenerateResponse,
    BddGeneratedScenario,
    BddSaveRequest,
    BulkBddRequest,
    BulkBddResponse,
    BulkDeleteRequest,
    CoverageMatrixOut,
    CoverageMatrixRow,
    DashboardStats,
    DataBindingCreate,
    DataBindingOut,
    DecideRequest,
    EdgeCaseRequest,
    EdgeCaseResponse,
    EnhancedBddGenerateRequest,
    EnhancedBddGenerateResponse,
    ExecutionCreate,
    ExecutionDetailOut,
    ExecutionOut,
    ExecutionResultOut,
    ExecutionStatsOut,
    ExecutionTrendsOut,
    ExpandedScenarioOut,
    ExpandedScenarioRow,
    ExpandedStep,
    FlakyTestOut,
    FlowCreate,
    FlowDetailOut,
    FlowGraphUpdate,
    FlowOut,
    GlobalDashboardActivity,
    GlobalDashboardOut,
    GlobalDashboardProjectRow,
    ImportCreate,
    ImportOut,
    IntegrationCreate,
    IntegrationOut,
    IntegrationUpdate,
    LinkRequirementRequest,
    ProjectCreate,
    ProjectMemberCreate,
    ProjectMemberOut,
    ProjectOut,
    ProjectUpdate,
    RegressionSetCreate,
    RegressionSetDetailOut,
    RegressionSetOut,
    RegressionSuggestRequest,
    RegressionSuggestResponse,
    RequirementCreate,
    RequirementOut,
    RequirementUpdate,
    ResultStatusUpdate,
    ScenarioCreate,
    ScenarioOut,
    ScenarioUpdate,
    ScenarioVersionDiff,
    ScenarioVersionOut,
    ScheduleCreate,
    ScheduleOut,
    ScheduleUpdate,
    SyncResultOut,
    AiBatchDetailOut,
    AiBatchOut,
    AllureExportRequest,
    AllureExportResponse,
    BulkReviewRequest,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionOut,
    DebugAnalysisItem,
    DebugAnalysisResponse,
    GenerateAutomationRequest,
    QuickAction,
    GenerateAutomationResponse,
    GenerateTestCasesRequest,
    GenerateTestCasesResponse,
    GherkinValidateRequest,
    GherkinValidateResponse,
    GherkinResult,
    JavaResult,
    PlaywrightResult,
    RunDebugRequest,
    StepLibraryResponse,
    TestCaseOut,
    TestCaseReviewAction,
    TestCaseUpdate,
    TestDataSetCreate,
    TestDataSetOut,
    TestDataSetUpdate,
    TrendDataPoint,
    WeeklyTrendPoint,
    MobileRunCreate,
    MobileRunOut,
)
from app.infra.models import AuditEvent
from app.domains.audit.service import log_audit
from app.domains.tspm import test_case_service as tc_svc
from app.domains.tspm import automation_gen_service as auto_gen
from app.domains.tspm import ai_debug_service as debug_svc
from app.domains.tspm import ai_chat_service as chat_svc
from app.domains.tspm import approval_service as approval_svc
from app.domains.tspm import binding_service as binding_svc
from app.domains.tspm import execution_service as execution_svc
from app.domains.tspm import flow_regression_service as flow_regression_svc
from app.domains.tspm import import_service as import_svc
from app.domains.tspm import integration_service as integration_svc
from app.domains.tspm import project_service as project_svc
from app.domains.tspm import schedule_service as schedule_svc
from app.domains.tspm import scenario_service as scenario_svc
from app.domains.tspm import test_data_service as test_data_svc
from app.domains.tspm import test_data_simulation_service as test_data_sim_svc
from app.domains.tspm import test_runner_service as runner_svc
from app.domains.ai.context_builder import build_project_ai_context

router = APIRouter(prefix="/tspm", tags=["tspm"])
logger = logging.getLogger(__name__)

DB = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def _get_project(db: Session, project_id: str, user: User | None = None) -> TspmProject:
    # Gecersiz UUID formatinda 500 (DataError) yerine 404 don — bilgi sizintisini onler.
    import uuid as _uuid
    try:
        _uuid.UUID(str(project_id))
    except (ValueError, AttributeError, TypeError):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")
    try:
        p = db.get(TspmProject, project_id)
    except Exception:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")
    if user is not None:
        user_perms = set()
        for role in user.roles:
            for rp in role.permissions:
                user_perms.add(rp.permission)
        if "admin.*" not in user_perms:
            is_member = db.scalar(
                select(func.count()).where(
                    TspmProjectMember.project_id == project_id,
                    TspmProjectMember.user_id == user.id,
                )
            )
            if not is_member:
                raise HTTPException(
                    status.HTTP_403_FORBIDDEN,
                    "Bu projeye erişim yetkiniz yok",
                )
    return p


def _slugify_filename(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", text.strip())
    cleaned = cleaned.strip("._")
    return cleaned or "artifact"


def _resolve_query_token_user(db: Session, token: Optional[str]) -> Optional[User]:
    if not token:
        return None
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    user = db.get(User, sub)
    if user is None or not user.is_active:
        return None
    return user


def _persist_generated_automation_artifacts(
    db: Session,
    project_id: str,
    feature_name: str,
    batch_id: Optional[str],
    test_case_count: int,
    result: dict,
) -> list[AutomationArtifactOut]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_dir = (
        Path(settings.artifacts_dir)
        / "tspm"
        / project_id
        / "automation"
        / f"{_slugify_filename(feature_name)}_{timestamp}"
    )
    out_dir.mkdir(parents=True, exist_ok=True)

    persisted: list[AutomationArtifactOut] = []
    artifact_specs = [
        ("gherkin", result.get("gherkin"), "gherkin", "text/x-gherkin+plain"),
        ("java", result.get("java"), "java_code", "text/x-java-source"),
        ("playwright", result.get("playwright"), "ts_code", "text/typescript"),
    ]

    for artifact_type, payload, content_key, mime_type in artifact_specs:
        if not payload:
            continue
        content = payload.get(content_key, "")
        if not isinstance(content, str) or not content.strip():
            continue

        filename = _slugify_filename(payload.get("filename") or f"{artifact_type}.txt")
        file_path = out_dir / filename
        file_path.write_text(content, encoding="utf-8")

        artifact = TspmAutomationArtifact(
            project_id=project_id,
            batch_id=batch_id,
            artifact_type=artifact_type,
            feature_name=feature_name,
            filename=filename,
            storage_path=str(file_path.resolve()),
            mime_type=mime_type,
            size_bytes=file_path.stat().st_size,
            source_test_case_count=test_case_count,
        )
        db.add(artifact)
        db.flush()
        persisted.append(
            AutomationArtifactOut(
                id=artifact.id,
                artifact_type=artifact.artifact_type,
                filename=artifact.filename,
                download_url=f"/api/v1/tspm/projects/{project_id}/automation/artifacts/{artifact.id}/download",
                size_bytes=artifact.size_bytes,
                created_at=artifact.created_at,
            )
        )

    db.commit()
    return persisted


def _extract_postman_items(items: list[dict], folder_stack: Optional[list[str]] = None) -> list[tuple[list[str], dict]]:
    folder_stack = folder_stack or []
    flattened: list[tuple[list[str], dict]] = []
    for item in items:
        request = item.get("request")
        if request:
            flattened.append((folder_stack, item))
            continue
        child_items = item.get("item") or []
        if child_items:
            flattened.extend(
                _extract_postman_items(child_items, [*folder_stack, item.get("name", "").strip()])
            )
    return flattened


def _header_array_to_dict(headers: Optional[list[dict]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for header in headers or []:
        key = str(header.get("key", "")).strip()
        if not key or header.get("disabled"):
            continue
        result[key] = str(header.get("value", ""))
    return result


def _postman_url_to_path(url_value: Optional[Union[dict, str]]) -> str:
    if isinstance(url_value, str):
        parsed = urlparse(url_value)
        path = parsed.path or "/"
        if parsed.query:
            path = f"{path}?{parsed.query}"
        return path
    if isinstance(url_value, dict):
        path_segments = url_value.get("path") or []
        path = "/" + "/".join(str(part).strip("/") for part in path_segments if str(part).strip("/"))
        query_items = url_value.get("query") or []
        query_parts = []
        for item in query_items:
            if item.get("disabled"):
                continue
            key = str(item.get("key", "")).strip()
            if not key:
                continue
            value = str(item.get("value", ""))
            query_parts.append(f"{key}={value}")
        if query_parts:
            path = f"{path or '/'}?{'&'.join(query_parts)}"
        if path and path != "/":
            return path
        raw = url_value.get("raw")
        if isinstance(raw, str) and raw.strip():
            return _postman_url_to_path(raw)
        return path or "/"
    return "/"


def _postman_body_to_json(body: Optional[dict]) -> Optional[dict]:
    body = body or {}
    mode = body.get("mode")
    if mode == "raw":
        raw = body.get("raw")
        if not isinstance(raw, str) or not raw.strip():
            return None
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"value": parsed}
        except json.JSONDecodeError:
            return {"raw": raw}
    if mode == "urlencoded":
        payload: dict[str, Any] = {}
        for item in body.get("urlencoded") or []:
            if item.get("disabled"):
                continue
            key = str(item.get("key", "")).strip()
            if key:
                payload[key] = item.get("value")
        return payload or None
    return None


def _parse_postman_assertions(events: Optional[list[dict]]) -> list[dict[str, Any]]:
    assertions: list[dict[str, Any]] = []
    for event in events or []:
        if event.get("listen") != "test":
            continue
        script = event.get("script") or {}
        lines = script.get("exec") or []
        if not isinstance(lines, list):
            continue
        for line in lines:
            text = str(line).strip()
            status_match = re.search(r"pm\.response\.to\.have\.status\((\d{3})\)", text)
            if status_match:
                assertions.append({"type": "status_code", "operator": "equals", "expected": int(status_match.group(1))})
            header_match = re.search(r"pm\.response\.to\.have\.header\(['\"]([^'\"]+)['\"]\)", text)
            if header_match:
                assertions.append({"type": "header_present", "header": header_match.group(1)})
            body_match = re.search(r"pm\.response\.text\(\)\.to\.include\(['\"](.+?)['\"]\)", text)
            if body_match:
                assertions.append({"type": "body_contains", "expected": body_match.group(1)})
    return assertions


def _is_disallowed_api_host(base_url: str) -> bool:
    parsed = urlparse(base_url)
    host = parsed.hostname
    if not host:
        return False
    if host in {"localhost", "127.0.0.1"}:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        try:
            resolved = socket.gethostbyname(host)
            ip = ipaddress.ip_address(resolved)
        except OSError as exc:
            logger.warning("Could not resolve API host %s: %s", host, exc)
            return False
    return (
        ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ) and not ip.is_loopback


def _extract_json_path(data: Any, path: str) -> Any:
    normalized = path.strip()
    if normalized.startswith("$."):
        normalized = normalized[2:]
    elif normalized.startswith("$"):
        normalized = normalized[1:]
    if not normalized:
        return data

    current = data
    for part in normalized.split("."):
        match = re.match(r"^([^\[]+)(?:\[(\d+)\])?$", part)
        if not match:
            raise KeyError(path)
        key, index = match.groups()
        if isinstance(current, dict):
            current = current[key]
        else:
            raise KeyError(path)
        if index is not None:
            if not isinstance(current, list):
                raise KeyError(path)
            current = current[int(index)]
    return current


def _evaluate_api_assertions(assertions: Optional[list[dict[str, Any]]], response: httpx.Response) -> tuple[bool, list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    if not assertions:
        ok = 200 <= response.status_code < 300
        checks.append({
            "type": "default_status_2xx",
            "passed": ok,
            "actual": response.status_code,
            "expected": "2xx",
        })
        return ok, checks

    response_text = response.text
    try:
        response_json = response.json()
    except ValueError:
        response_json = None

    overall = True
    for assertion in assertions:
        a_type = assertion.get("type", "status_code")
        passed = False
        actual: Any = None
        expected = assertion.get("expected")
        detail = ""
        try:
            if a_type == "status_code":
                actual = response.status_code
                operator = assertion.get("operator", "equals")
                if operator == "gte":
                    passed = actual >= int(expected)
                elif operator == "lte":
                    passed = actual <= int(expected)
                else:
                    passed = actual == int(expected)
            elif a_type == "body_contains":
                actual = response_text[:500]
                passed = str(expected) in response_text
            elif a_type == "header_contains":
                header_name = str(assertion.get("header", ""))
                actual = response.headers.get(header_name, "")
                passed = str(expected) in actual
            elif a_type == "header_present":
                header_name = str(assertion.get("header", ""))
                actual = response.headers.get(header_name)
                passed = actual is not None
                expected = "present"
            elif a_type == "response_time_lt":
                actual = response.elapsed.total_seconds() * 1000
                passed = actual < float(expected)
            elif a_type == "jsonpath_exists":
                actual = _extract_json_path(response_json, str(assertion.get("path", "$")))
                passed = actual is not None
                expected = "exists"
            elif a_type == "jsonpath_equals":
                actual = _extract_json_path(response_json, str(assertion.get("path", "$")))
                passed = actual == expected
            else:
                detail = f"Desteklenmeyen assertion type: {a_type}"
        except Exception as exc:
            logger.debug("API assertion evaluation failed for %s: %s", a_type, exc)
            detail = str(exc)
            passed = False

        overall = overall and passed
        checks.append({
            "type": a_type,
            "passed": passed,
            "expected": expected,
            "actual": actual,
            "detail": detail,
        })
    return overall, checks


# ═══════════════════════════════════════════════════════════════════════
# Projects
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: DB, user: CurrentUser):
    """Projeleri listeler."""
    return project_svc.list_projects_for_user(db, user)


@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=201,
    responses={
        201: {
            "description": "Proje basariyla olusturuldu",
            "content": {
                "application/json": {
                    "example": {
                        "id": "2c8fe4e2-4b64-4fcf-bf84-0dff7cc1d8f5",
                        "name": "Mobil Bankacilik Regression",
                        "description": "Kritik regresyon testleri icin proje",
                        "archived": False,
                    }
                }
            },
        },
        401: {"description": "Kimlik dogrulama gerekli"},
        403: {"description": "Proje olusturma yetkisi yok"},
        422: {"description": "Gecersiz proje verisi"},
    },
)
def create_project(
    body: ProjectCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """Yeni proje olusturur."""
    return project_svc.create_project_for_user(db, body, user)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: DB, user: CurrentUser):
    """Tek proje detayını getirir."""
    project = _get_project(db, project_id, user)
    return project


@router.put("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str, body: ProjectUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """Proje adını, açıklamasını ve test URL'ini günceller."""
    project = _get_project(db, project_id, user)
    project.name = body.name.strip()
    project.description = body.description.strip()
    project.base_url = body.base_url.strip()
    db.commit()
    db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=204)
def delete_project(
    project_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """Projeyi siler."""
    project = _get_project(db, project_id, user)
    db.delete(project)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════
# Dashboard
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/dashboard", response_model=DashboardStats)
def project_dashboard(project_id: str, db: DB, user: CurrentUser):
    """Proje ozet istatistiklerini getirir."""
    _get_project(db, project_id, user)
    return project_svc.build_project_dashboard(db, project_id)


@router.get("/dashboard/global", response_model=GlobalDashboardOut)
def global_dashboard(db: DB, user: CurrentUser):
    """Platform genelinde ozet istatistikler."""
    return project_svc.build_global_dashboard(db, user)


# ═══════════════════════════════════════════════════════════════════════
# Scenarios
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/scenarios", response_model=list[ScenarioOut])
def list_scenarios(
    project_id: str, db: DB, user: CurrentUser,
    q: Optional[str] = Query(None),
    tag: Optional[str] = Query(None, description="Tek tag ile filtrele"),
    tags: Optional[str] = Query(None, description="Virgülle ayrılmış çoklu tag filtresi"),
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0, description="Kaç kayıt atlanacak"),
    limit: int = Query(100, ge=1, le=500, description="Sayfa başına kayıt (maks 500)"),
):
    """Projeye ait test senaryolarini listeler."""
    _get_project(db, project_id, user)
    return scenario_svc.list_scenarios_for_project(
        db,
        project_id,
        q=q,
        tag=tag,
        tags=tags,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post("/projects/{project_id}/scenarios", response_model=ScenarioOut, status_code=201)
def create_scenario(
    project_id: str, body: ScenarioCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Yeni test senaryosu olusturur."""
    _get_project(db, project_id, user)
    return scenario_svc.create_scenario_for_project(
        db,
        project_id,
        body,
        actor_user_id=user.id,
    )


@router.get("/projects/{project_id}/scenarios/{scenario_id}", response_model=ScenarioOut)
def get_scenario(project_id: str, scenario_id: str, db: DB, user: CurrentUser):
    """Test senaryosu detayini getirir."""
    return scenario_svc.get_scenario_or_404(db, project_id, scenario_id)


@router.put("/projects/{project_id}/scenarios/{scenario_id}", response_model=ScenarioOut)
def update_scenario(
    project_id: str, scenario_id: str, body: ScenarioUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_UPDATE))],
):
    """Test senaryosunu gunceller."""
    return scenario_svc.update_scenario_for_project(
        db,
        project_id,
        scenario_id,
        body,
        actor_user_id=user.id,
    )


@router.post("/projects/{project_id}/scenarios/generate-bdd", response_model=BddGenerateResponse)
def generate_bdd_scenarios(
    project_id: str, body: BddGenerateRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Analiz dokümanından BDD senaryoları üret (OpenAI)."""
    _get_project(db, project_id, user)
    from app.domains.tspm.bdd_generator import generate_bdd_scenarios as _generate
    raw_scenarios = _generate(body.analysis_text, body.extra_instructions)
    scenarios = [BddGeneratedScenario(**s) for s in raw_scenarios]
    return BddGenerateResponse(scenarios=scenarios)


@router.post(
    "/projects/{project_id}/scenarios/save-bdd",
    response_model=list[ScenarioOut],
    status_code=201,
)
def save_bdd_scenarios(
    project_id: str, body: BddSaveRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Üretilen BDD senaryolarını veritabanına toplu kaydet."""
    _get_project(db, project_id, user)
    created = []
    for sc in body.scenarios:
        steps = [
            {"order": i, "keyword": step.get("keyword", ""), "text": step.get("text", "")}
            for i, step in enumerate(sc.steps)
        ]
        s = TspmScenario(
            project_id=project_id,
            title=sc.title,
            description=f"{sc.description}\n\n---\n{sc.gherkin}" if sc.gherkin else sc.description,
            status="draft",
            steps=steps,
        )
        db.add(s)
        created.append(s)
    db.commit()
    for s in created:
        db.refresh(s)
    return created


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BDD GENERATION (Enhanced)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.post(
    "/projects/{project_id}/bdd/generate",
    response_model=EnhancedBddGenerateResponse,
    summary="Generate enriched BDD scenarios for a requirement",
)
def enhanced_bdd_generate(
    project_id: str,
    body: EnhancedBddGenerateRequest,
    db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Context-enriched BDD generation: step reuse, banking domain, quality scoring."""
    _get_project(db, project_id, user)
    from app.domains.tspm.bdd_generator import BDDGenerator
    gen = BDDGenerator(db, project_id)
    result = gen.generate_scenarios(body.requirement_id, body.options)
    return EnhancedBddGenerateResponse(**result)


@router.post(
    "/projects/{project_id}/bdd/bulk-generate",
    response_model=BulkBddResponse,
    summary="Bulk BDD generation for multiple requirements",
)
def enhanced_bdd_bulk_generate(
    project_id: str,
    body: BulkBddRequest,
    db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Generate BDD scenarios for a batch of requirements."""
    _get_project(db, project_id, user)
    from app.domains.tspm.bdd_generator import BDDGenerator
    gen = BDDGenerator(db, project_id)
    result = gen.bulk_generate(body.requirement_ids, body.options)
    return BulkBddResponse(**result)


@router.post(
    "/projects/{project_id}/bdd/edge-cases",
    response_model=EdgeCaseResponse,
    summary="Suggest edge cases for a requirement",
)
def bdd_suggest_edge_cases(
    project_id: str,
    body: EdgeCaseRequest,
    db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Analyze existing scenarios and suggest missing edge case / negative / boundary tests."""
    _get_project(db, project_id, user)
    from app.domains.tspm.bdd_generator import BDDGenerator
    gen = BDDGenerator(db, project_id)
    result = gen.suggest_edge_cases(body.requirement_id)
    return EdgeCaseResponse(**result)


@router.get(
    "/projects/{project_id}/bdd/step-library",
    response_model=StepLibraryResponse,
    summary="Get the project step library",
)
def bdd_step_library(
    project_id: str,
    db: DB,
    user: CurrentUser,
):
    """Extract reusable step patterns from all project scenarios."""
    _get_project(db, project_id, user)
    from app.domains.tspm.bdd_generator import BDDGenerator
    gen = BDDGenerator(db, project_id)
    result = gen.get_step_library()
    return StepLibraryResponse(**result)


@router.post(
    "/projects/{project_id}/bdd/validate",
    response_model=GherkinValidateResponse,
    summary="Validate Gherkin syntax",
)
def bdd_validate_gherkin(
    project_id: str,
    body: GherkinValidateRequest,
    db: DB,
    user: CurrentUser,
):
    """Validate Gherkin text for syntax correctness (Turkish + English keywords)."""
    _get_project(db, project_id, user)
    from app.domains.tspm.bdd_generator import BDDGenerator
    gen = BDDGenerator(db, project_id)
    result = gen.validate_gherkin(body.gherkin)
    return GherkinValidateResponse(**result)


@router.post(
    "/projects/{project_id}/scenarios/{scenario_id}/clone",
    response_model=ScenarioOut,
    status_code=201,
)
def clone_scenario(
    project_id: str, scenario_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Mevcut senaryoyu kopyalayarak yeni bir draft senaryo oluşturur."""
    return scenario_svc.clone_scenario_for_project(db, project_id, scenario_id)


@router.post("/projects/{project_id}/scenarios/bulk-delete", status_code=204)
def bulk_delete_scenarios(
    project_id: str, body: BulkDeleteRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_DELETE))],
):
    """Secilen senaryolari toplu olarak siler."""
    _get_project(db, project_id, user)
    scenario_svc.bulk_delete_scenarios_for_project(
        db,
        project_id,
        body,
        actor_user_id=user.id,
    )


# ═══════════════════════════════════════════════════════════════════════
# Requirements & Coverage
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/requirements", response_model=RequirementOut, status_code=201)
def create_requirement(
    project_id: str, body: RequirementCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.REQUIREMENT_MANAGE))],
):
    """Yeni gereksinim kaydi olusturur."""
    _get_project(db, project_id, user)
    return scenario_svc.create_requirement_for_project(db, project_id, body)


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementOut])
def list_requirements(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Gereksinimleri listeler."""
    _get_project(db, project_id, user)
    return scenario_svc.list_requirements_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.put("/projects/{project_id}/requirements/{requirement_id}", response_model=RequirementOut)
def update_requirement(
    project_id: str, requirement_id: str, body: RequirementUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.REQUIREMENT_MANAGE))],
):
    """Gereksinim bilgilerini gunceller."""
    return scenario_svc.update_requirement_for_project(
        db,
        project_id,
        requirement_id,
        body,
    )


@router.delete("/projects/{project_id}/requirements/{requirement_id}", status_code=204)
def delete_requirement(
    project_id: str, requirement_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.REQUIREMENT_MANAGE))],
):
    """Gereksinim kaydini siler."""
    scenario_svc.delete_requirement_for_project(db, project_id, requirement_id)


@router.post("/projects/{project_id}/scenarios/{scenario_id}/requirements", status_code=201)
def link_scenario_requirements(
    project_id: str, scenario_id: str, body: LinkRequirementRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.REQUIREMENT_MANAGE))],
):
    """Senaryoyu gereksinimlerle eslestirir."""
    _get_project(db, project_id, user)
    return scenario_svc.link_scenario_requirements_for_project(
        db,
        project_id,
        scenario_id,
        body,
    )


@router.delete(
    "/projects/{project_id}/scenarios/{scenario_id}/requirements/{requirement_id}",
    status_code=204,
)
def unlink_scenario_requirement(
    project_id: str, scenario_id: str, requirement_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.REQUIREMENT_MANAGE))],
):
    """Senaryo ile gereksinim baglantisini kaldirir."""
    scenario_svc.unlink_scenario_requirement_for_project(
        db,
        scenario_id,
        requirement_id,
    )


@router.get("/projects/{project_id}/coverage-matrix", response_model=CoverageMatrixOut)
def get_coverage_matrix(project_id: str, db: DB, user: CurrentUser):
    """Gereksinim kapsama matrisini getirir."""
    _get_project(db, project_id, user)
    return scenario_svc.build_coverage_matrix_for_project(db, project_id)


@router.get("/projects/{project_id}/coverage-gaps", response_model=list[RequirementOut])
def get_coverage_gaps(project_id: str, db: DB, user: CurrentUser):
    """Kapsama bosluklarini listeler."""
    _get_project(db, project_id, user)
    return scenario_svc.get_coverage_gaps_for_project(db, project_id)


# ═══════════════════════════════════════════════════════════════════════
# Scenario Versions
# ═══════════════════════════════════════════════════════════════════════

@router.get(
    "/projects/{project_id}/scenarios/{scenario_id}/versions",
    response_model=list[ScenarioVersionOut],
)
def list_scenario_versions(project_id: str, scenario_id: str, db: DB, user: CurrentUser):
    """Senaryo surumlerini listeler."""
    s = db.get(TspmScenario, scenario_id)
    if s is None or s.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Senaryo bulunamadı")
    return list(db.scalars(
        select(TspmScenarioVersion)
        .where(TspmScenarioVersion.scenario_id == scenario_id)
        .order_by(TspmScenarioVersion.version_number.desc())
    ))


@router.get(
    "/projects/{project_id}/scenarios/{scenario_id}/versions/{v1}/diff/{v2}",
    response_model=ScenarioVersionDiff,
)
def diff_scenario_versions(
    project_id: str, scenario_id: str, v1: int, v2: int, db: DB, user: CurrentUser,
):
    """Iki senaryo surumu arasindaki farklari getirir."""
    s = db.get(TspmScenario, scenario_id)
    if s is None or s.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Senaryo bulunamadı")
    ver1 = db.scalar(
        select(TspmScenarioVersion).where(
            TspmScenarioVersion.scenario_id == scenario_id,
            TspmScenarioVersion.version_number == v1,
        )
    )
    ver2 = db.scalar(
        select(TspmScenarioVersion).where(
            TspmScenarioVersion.scenario_id == scenario_id,
            TspmScenarioVersion.version_number == v2,
        )
    )
    if ver1 is None or ver2 is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Versiyon bulunamadı")
    snap1 = ScenarioVersionOut.model_validate(ver1)
    snap2 = ScenarioVersionOut.model_validate(ver2)
    return ScenarioVersionDiff(
        v1=v1, v2=v2,
        title_changed=ver1.title != ver2.title,
        description_changed=ver1.description != ver2.description,
        steps_changed=ver1.steps != ver2.steps,
        status_changed=ver1.status != ver2.status,
        v1_snapshot=snap1, v2_snapshot=snap2,
    )


# ═══════════════════════════════════════════════════════════════════════
# Executions
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/executions", response_model=list[ExecutionOut])
def list_executions(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0, description="Kaç kayıt atlanacak"),
    limit: int = Query(50, ge=1, le=200, description="Sayfa başına kayıt (maks 200)"),
    platform: Optional[str] = Query(None, description="Platform filtresi: ios | android | desktop"),
):
    """Test kosularini listeler."""
    _get_project(db, project_id, user)
    return execution_svc.list_executions_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
        platform=platform,
    )


@router.post("/projects/{project_id}/executions", response_model=ExecutionOut, status_code=201)
def create_execution(
    project_id: str, body: ExecutionCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_CREATE))],
):
    """Yeni test kosusu olusturur."""
    _get_project(db, project_id, user)
    ex = TspmExecution(
        project_id=project_id,
        name=body.name,
        status="running",
        platform=body.platform,
        device_name=body.device_name,
        app_upload_id=body.app_upload_id,
    )
    db.add(ex)
    db.flush()
    for sid in body.scenario_ids:
        db.add(TspmExecutionResult(execution_id=ex.id, scenario_id=sid, status="pending"))
    metrics = TspmExecutionMetrics(
        project_id=project_id,
        execution_id=ex.id,
        total=len(body.scenario_ids),
        passed=0,
        failed=0,
        skipped=0,
        pass_rate=0.0,
    )
    db.add(metrics)
    db.commit()
    db.refresh(ex)
    log_audit(db, actor_user_id=user.id, action="execution.create",
              resource_type="execution", resource_id=ex.id,
              payload={
                  "name": ex.name,
                  "scenario_count": len(body.scenario_ids),
                  "project_id": project_id,
                  "platform": body.platform,
                  "device_name": body.device_name,
              }, ip=None)
    db.commit()
    return ExecutionOut(
        id=ex.id, name=ex.name, status=ex.status,
        created_at=ex.created_at, scenario_total=len(body.scenario_ids),
        passed_count=0, failed_count=0,
        platform=ex.platform,
        device_name=ex.device_name,
        app_upload_id=ex.app_upload_id,
    )


@router.get("/projects/{project_id}/executions/compare")
def compare_executions(
    project_id: str,
    run1: str = Query(...),
    run2: str = Query(...),
    db: DB = ...,
    user: CurrentUser = ...,
):
    """İki koşuyu karşılaştır."""
    _get_project(db, project_id, user)
    return execution_svc.compare_executions_for_project(db, project_id, run1, run2)


@router.get("/projects/{project_id}/executions/{run_id}", response_model=ExecutionDetailOut)
def get_execution(project_id: str, run_id: str, db: DB, user: CurrentUser):
    """Test kosusu detayini getirir."""
    return execution_svc.get_execution_detail_for_project(db, project_id, run_id)


@router.patch("/projects/{project_id}/executions/{run_id}/results/{result_id}")
def update_result_status(
    project_id: str, run_id: str, result_id: str, body: ResultStatusUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_UPDATE))],
):
    """Kosu sonucunun durumunu gunceller."""
    return execution_svc.update_execution_result_status(db, run_id, result_id, body.status)


@router.post("/projects/{project_id}/executions/{run_id}", response_model=ExecutionOut, status_code=201)
def rerun_execution(
    project_id: str, run_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_CREATE))],
):
    """Mevcut kosuyu yeniden baslatir."""
    return execution_svc.rerun_execution_for_project(db, project_id, run_id)


@router.post("/projects/{project_id}/executions/{run_id}/cancel", status_code=200)
def cancel_execution(project_id: str, run_id: str, db: DB, user: CurrentUser):
    """Devam eden bir koşumu iptal eder; bekleyen sonuçları 'skipped' yapar."""
    execution = db.get(TspmExecution, run_id)
    if execution is None or execution.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")
    if execution.status not in ("running", "pending"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu koşum zaten tamamlanmış veya iptal edilmiş")
    execution.status = "cancelled"
    pending = list(
        db.scalars(
            select(TspmExecutionResult).where(
                TspmExecutionResult.execution_id == run_id,
                TspmExecutionResult.status == "pending",
            )
        )
    )
    for result in pending:
        result.status = "skipped"
    db.commit()
    return {"ok": True, "execution_id": run_id, "cancelled_results": len(pending)}


# ═══════════════════════════════════════════════════════════════════════
# Execution Trends & Stats
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/execution-trends", response_model=ExecutionTrendsOut)
def get_execution_trends(project_id: str, db: DB, user: CurrentUser, days: int = Query(30)):
    """Test kosusu trendlerini getirir."""
    _get_project(db, project_id, user)
    return execution_svc.build_execution_trends_for_project(db, project_id, days=days)


@router.get("/projects/{project_id}/execution-stats", response_model=ExecutionStatsOut)
def get_execution_stats(project_id: str, db: DB, user: CurrentUser):
    """Test kosusu istatistiklerini getirir."""
    _get_project(db, project_id, user)
    return execution_svc.build_execution_stats_for_project(db, project_id)


@router.get("/projects/{project_id}/flaky-tests", response_model=list[FlakyTestOut])
def get_flaky_tests(project_id: str, db: DB, user: CurrentUser):
    """Flaky testleri listeler."""
    _get_project(db, project_id, user)
    return execution_svc.get_flaky_tests_for_project(db, project_id)


# ═══════════════════════════════════════════════════════════════════════
# Flows
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/flows", response_model=list[FlowOut])
def list_flows(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Akislari listeler."""
    _get_project(db, project_id, user)
    return flow_regression_svc.list_flows_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.post("/projects/{project_id}/flows", response_model=FlowOut, status_code=201)
def create_flow(
    project_id: str, body: FlowCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.FLOW_MANAGE))],
):
    """Yeni akis olusturur."""
    _get_project(db, project_id, user)
    return flow_regression_svc.create_flow_for_project(db, project_id, body)


@router.get("/projects/{project_id}/flows/{flow_id}", response_model=FlowDetailOut)
def get_flow(project_id: str, flow_id: str, db: DB, user: CurrentUser):
    """Akis detayini getirir."""
    return flow_regression_svc.get_flow_or_404(db, project_id, flow_id)


@router.put("/projects/{project_id}/flows/{flow_id}/graph", response_model=FlowDetailOut)
def update_flow_graph(
    project_id: str, flow_id: str, body: FlowGraphUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.FLOW_MANAGE))],
):
    """Akis grafigini gunceller."""
    return flow_regression_svc.update_flow_graph_for_project(
        db,
        project_id,
        flow_id,
        body,
    )


# ═══════════════════════════════════════════════════════════════════════
# Regression Sets
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/regression-sets", response_model=list[RegressionSetOut])
def list_regression_sets(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Regresyon setlerini listeler."""
    _get_project(db, project_id, user)
    return flow_regression_svc.list_regression_sets_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.post("/projects/{project_id}/regression-sets", response_model=RegressionSetOut, status_code=201)
def create_regression_set(
    project_id: str, body: RegressionSetCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """Yeni regresyon seti olusturur."""
    _get_project(db, project_id, user)
    return flow_regression_svc.create_regression_set_for_project(db, project_id, body)


@router.get("/projects/{project_id}/regression-sets/{set_id}", response_model=RegressionSetDetailOut)
def get_regression_set(project_id: str, set_id: str, db: DB, user: CurrentUser):
    """Regresyon seti detayini getirir."""
    return flow_regression_svc.get_regression_set_detail_for_project(
        db,
        project_id,
        set_id,
    )


@router.post("/projects/{project_id}/regression-sets/{set_id}/add", status_code=200)
def add_scenarios_to_regression(
    project_id: str, set_id: str, body: AddScenariosRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_UPDATE))],
):
    """Senaryolari regresyon setine ekler."""
    return flow_regression_svc.add_scenarios_to_regression_set(
        db,
        project_id,
        set_id,
        body,
    )


@router.post(
    "/projects/{project_id}/regression-sets/suggest",
    response_model=RegressionSuggestResponse,
)
def suggest_regression_sets(project_id: str, body: RegressionSuggestRequest, db: DB, user: CurrentUser):
    """Projedeki senaryoları AI ile analiz edip regresyon seti önerileri döndürür."""
    _get_project(db, project_id, user)
    return flow_regression_svc.suggest_regression_sets_for_project(db, project_id, body)


@router.post(
    "/projects/{project_id}/regression-sets/accept-suggestions",
    response_model=list[RegressionSetOut],
    status_code=201,
)
def accept_suggested_sets(
    project_id: str, body: AcceptSuggestedSetsRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_CREATE))],
):
    """AI önerilerinden seçilen setleri toplu oluşturur."""
    _get_project(db, project_id, user)
    return flow_regression_svc.accept_suggested_sets_for_project(
        db,
        project_id,
        body,
    )


# ═══════════════════════════════════════════════════════════════════════
# Approvals
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/approvals", response_model=list[ApprovalOut])
def list_approvals(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Onay kayitlarini listeler."""
    _get_project(db, project_id, user)
    return approval_svc.list_approvals_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.post("/projects/{project_id}/approvals", response_model=ApprovalOut, status_code=201)
def create_approval(
    project_id: str, body: ApprovalCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.APPROVAL_DECIDE))],
):
    """Yeni onay kaydi olusturur."""
    _get_project(db, project_id, user)
    return approval_svc.create_approval_for_project(db, project_id, body)


@router.post("/projects/{project_id}/approvals/{approval_id}/decide")
def decide_approval(
    project_id: str, approval_id: str, body: DecideRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.APPROVAL_DECIDE))],
):
    """Onay kaydi icin karar verir."""
    return approval_svc.decide_approval_for_project(db, project_id, approval_id, body)


# ═══════════════════════════════════════════════════════════════════════
# Imports
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/imports", response_model=ImportOut, status_code=201)
def create_import(
    project_id: str, body: ImportCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.IMPORT_CREATE))],
):
    """Icerik aktarim kaydi olusturur."""
    _get_project(db, project_id, user)
    return import_svc.create_import_for_project(db, project_id, body)


# ═══════════════════════════════════════════════════════════════════════
# Schedules
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/schedules", response_model=ScheduleOut, status_code=201)
def create_schedule(
    project_id: str, body: ScheduleCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCHEDULE_MANAGE))],
):
    """Yeni zamanlama kaydi olusturur."""
    _get_project(db, project_id, user)
    return schedule_svc.create_schedule_for_project(
        db,
        project_id,
        body,
        actor_user_id=user.id,
    )


@router.get("/projects/{project_id}/schedules", response_model=list[ScheduleOut])
def list_schedules(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """Zamanlamalari listeler."""
    _get_project(db, project_id, user)
    return schedule_svc.list_schedules_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.put("/projects/{project_id}/schedules/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    project_id: str, schedule_id: str, body: ScheduleUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCHEDULE_MANAGE))],
):
    """Zamanlama bilgilerini gunceller."""
    return schedule_svc.update_schedule_for_project(
        db,
        project_id,
        schedule_id,
        body,
    )


@router.delete("/projects/{project_id}/schedules/{schedule_id}", status_code=204)
def delete_schedule(
    project_id: str, schedule_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCHEDULE_MANAGE))],
):
    """Zamanlama kaydini siler."""
    schedule_svc.delete_schedule_for_project(db, project_id, schedule_id)


@router.post(
    "/projects/{project_id}/schedules/{schedule_id}/trigger",
    response_model=ExecutionOut,
    status_code=201,
)
def trigger_schedule(
    project_id: str, schedule_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCHEDULE_MANAGE))],
):
    """Zamanlamayi manuel olarak tetikler."""
    _get_project(db, project_id, user)
    return schedule_svc.trigger_schedule_for_project(db, project_id, schedule_id)


# ═══════════════════════════════════════════════════════════════════════
# Test Data
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/test-data", response_model=TestDataSetOut, status_code=201)
def create_test_data(
    project_id: str, body: TestDataSetCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.TEST_DATA_MANAGE))],
):
    """Yeni test verisi seti olusturur."""
    _get_project(db, project_id, user)
    return test_data_svc.create_test_data_for_project(db, project_id, body)


@router.get("/projects/{project_id}/test-data", response_model=list[TestDataSetOut])
def list_test_data(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Test verisi setlerini listeler."""
    _get_project(db, project_id, user)
    return test_data_svc.list_test_data_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.put("/projects/{project_id}/test-data/{data_id}", response_model=TestDataSetOut)
def update_test_data(
    project_id: str, data_id: str, body: TestDataSetUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.TEST_DATA_MANAGE))],
):
    """Test verisi setini gunceller."""
    return test_data_svc.update_test_data_for_project(
        db,
        project_id,
        data_id,
        body,
    )


@router.delete("/projects/{project_id}/test-data/{data_id}", status_code=204)
def delete_test_data(
    project_id: str, data_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.TEST_DATA_MANAGE))],
):
    """Test verisi setini siler."""
    test_data_svc.delete_test_data_for_project(db, project_id, data_id)


@router.get("/projects/{project_id}/test-data/{data_id}/export")
def export_test_data(project_id: str, data_id: str, format: str = "csv", db: DB = ..., user: CurrentUser = ...):
    """Veri setini CSV veya JSON olarak dışa aktarır."""
    return test_data_svc.export_test_data_for_project(
        db,
        project_id,
        data_id,
        format=format,
    )


@router.post("/projects/{project_id}/test-data/{data_id}/mask")
def mask_test_data(project_id: str, data_id: str, body: dict, db: DB, user: CurrentUser):
    """Belirtilen sütunlardaki PII verilerini maskeler."""
    return test_data_svc.mask_test_data_for_project(
        db,
        project_id,
        data_id,
        body,
    )


@router.post("/projects/{project_id}/test-data/generate")
def generate_test_data(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Faker ile sentetik veri üretir."""
    _get_project(db, project_id, user)
    return test_data_svc.generate_test_data_preview(body)


@router.post("/projects/{project_id}/test-data/simulate-schema")
def simulate_schema(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Çok tablolu, kurallı şema simülasyonu.

    Body örneği:
    {
      "locale": "tr_TR",
      "tables": [
        {
          "name": "kullanicilar",
          "row_count": 20,
          "columns": [
            {"name": "id",     "type": "auto_increment"},
            {"name": "email",  "type": "email",   "unique": true},
            {"name": "yas",    "type": "integer",  "min": 18, "max": 65},
            {"name": "durum",  "type": "enum",     "values": ["aktif","pasif","beklemede"]},
            {"name": "bakiye", "type": "decimal",  "min": 0, "max": 50000, "precision": 2},
            {"name": "regex_ornek", "type": "regex", "pattern": "[A-Z]{3}[0-9]{4}"}
          ]
        },
        {
          "name": "siparisler",
          "row_count": 50,
          "columns": [
            {"name": "siparis_id", "type": "uuid"},
            {"name": "kullanici_id", "type": "foreign_key", "references": "kullanicilar.id"},
            {"name": "tutar",       "type": "decimal", "min": 10, "max": 5000, "precision": 2},
            {"name": "durum",       "type": "enum", "values": ["beklemede","tamamlandi","iptal"]}
          ]
        }
      ]
    }
    """
    _get_project(db, project_id, user)
    return test_data_sim_svc.simulate_schema_for_project(body)


# ── DB-Aware Smart Simulation endpoints ──────────────────────────────────────

@router.post("/test-data/parse-schema")
def parse_schema_from_ddl(body: dict, user: CurrentUser):
    """DDL SQL metnini WizardTable[] şemasına dönüştür (LLM destekli)."""
    return test_data_sim_svc.parse_schema_from_ddl(body)


@router.post("/test-data/parse-csv-schema")
def parse_schema_from_csv(body: dict, user: CurrentUser):
    """CSV başlıkları ve örnek satırlardan WizardTable[] şeması çıkar."""
    return test_data_sim_svc.parse_schema_from_csv(body)


@router.post("/test-data/parse-natural-language")
def parse_schema_from_natural_language(body: dict, user: CurrentUser):
    """Doğal dil açıklamasından WizardTable[] şeması üret (LLM gerekli)."""
    return test_data_sim_svc.parse_schema_from_natural_language(body)


@router.post("/test-data/parse-db-connection")
def parse_schema_from_db(body: dict, user: CurrentUser):
    """
    Canlı veritabanına bağlan ve şemayı WizardTable[]'a dönüştür.
    Body: { connection_string, schema_name?, exclude_tables? }
    """
    return test_data_sim_svc.parse_schema_from_db(body)


@router.post("/test-data/simulate")
def standalone_simulate(body: dict, user: CurrentUser):
    """
    Proje gerektirmeyen standalone şema simülasyonu.
    Body: { locale?, tables: [...WizardTable], quality_check? }
    Döner: { tables, table_count, quality_score?, quality_report? }
    """
    return test_data_sim_svc.standalone_simulate(body)


@router.post("/test-data/write-to-db")
def write_simulated_to_db(body: dict, user: CurrentUser):
    """
    Simüle edilmiş veriyi hedef veritabanına yazar.
    Body: { connection_string, tables: {tbl: {columns, rows}} }
    Döner: { written: {tbl: n}, total_rows, errors }
    """
    return test_data_sim_svc.write_simulated_to_db(body)


@router.post("/test-data/ai-enrich-schema")
def ai_enrich_schema(body: dict, user: CurrentUser):
    """WizardTable[] şemasını AI ile zenginleştir: iş kuralları, PII tespiti, kalite ipuçları."""
    return test_data_sim_svc.ai_enrich_schema(body)


@router.post("/projects/{project_id}/test-data/full-simulate")
def full_simulate(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Simüle et + FK bütünlüğü doğrula + kalite skoru döndür."""
    _get_project(db, project_id, user)
    return test_data_sim_svc.full_simulate(body)


@router.post(
    "/projects/{project_id}/scenarios/{scenario_id}/bind-data",
    response_model=DataBindingOut,
    status_code=201,
)
def bind_data_to_scenario(
    project_id: str, scenario_id: str, body: DataBindingCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.TEST_DATA_MANAGE))],
):
    """Veri setini senaryoya baglar."""
    return binding_svc.bind_data_to_scenario_for_project(
        db,
        project_id,
        scenario_id,
        body,
    )


@router.get(
    "/projects/{project_id}/scenarios/{scenario_id}/expanded",
    response_model=ExpandedScenarioOut,
)
def get_expanded_scenario(project_id: str, scenario_id: str, db: DB, user: CurrentUser):
    """Veri bagli senaryonun genisletilmis halini getirir."""
    return binding_svc.get_expanded_scenario_for_project(db, project_id, scenario_id)


# ═══════════════════════════════════════════════════════════════════════
# Integrations
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/integrations", response_model=IntegrationOut, status_code=201)
def create_integration(
    project_id: str, body: IntegrationCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.INTEGRATION_MANAGE))],
):
    """Yeni entegrasyon tanimi olusturur."""
    _get_project(db, project_id, user)
    return integration_svc.create_integration_for_project(db, project_id, body)


@router.get("/projects/{project_id}/integrations", response_model=list[IntegrationOut])
def list_integrations(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """Entegrasyonlari listeler."""
    _get_project(db, project_id, user)
    return integration_svc.list_integrations_for_project(
        db,
        project_id,
        skip=skip,
        limit=limit,
    )


@router.put("/projects/{project_id}/integrations/{integration_id}", response_model=IntegrationOut)
def update_integration(
    project_id: str, integration_id: str, body: IntegrationUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.INTEGRATION_MANAGE))],
):
    """Entegrasyon bilgilerini gunceller."""
    return integration_svc.update_integration_for_project(
        db,
        project_id,
        integration_id,
        body,
    )


@router.delete("/projects/{project_id}/integrations/{integration_id}", status_code=204)
def delete_integration(
    project_id: str, integration_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.INTEGRATION_MANAGE))],
):
    """Entegrasyonu siler."""
    integration_svc.delete_integration_for_project(db, project_id, integration_id)


@router.post("/projects/{project_id}/integrations/{integration_id}/sync", response_model=SyncResultOut)
def sync_integration(
    project_id: str, integration_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.INTEGRATION_MANAGE))],
):
    """Entegrasyonu manuel olarak senkronize eder."""
    return integration_svc.sync_integration_for_project(db, project_id, integration_id)


@router.post("/projects/{project_id}/integrations/{integration_id}/test-notification")
def test_notification(project_id: str, integration_id: str, db: DB, user: CurrentUser):
    """Slack veya Teams webhook'una test bildirimi gönderir."""
    intg = db.get(TspmIntegration, integration_id)
    if intg is None or intg.project_id != project_id:
        raise HTTPException(404, "Entegrasyon bulunamadı")

    config = intg.config or {}
    webhook_url = config.get("webhook_url", "")
    if not webhook_url:
        raise HTTPException(400, "Bu entegrasyon için webhook_url yapılandırılmamış")

    project = db.get(TspmProject, project_id)
    project_name = project.name if project else project_id

    if intg.provider == "slack":
        payload = {
            "text": f"✅ TestwrightAI Test Bildirimi — *{project_name}* projesi için entegrasyon test edildi.",
            "blocks": [{"type": "section", "text": {"type": "mrkdwn",
                "text": f"✅ *TestwrightAI* bağlantı testi başarılı!\nProje: `{project_name}`"}}]
        }
    else:  # microsoft_teams
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": "TestwrightAI Test Bildirimi",
            "themeColor": "0076D7",
            "title": "TestwrightAI Test Bildirimi",
            "text": f"✅ **{project_name}** projesi için entegrasyon testi başarılı."
        }

    try:
        resp = httpx.post(webhook_url, json=payload, timeout=10.0)
        if resp.status_code >= 400:
            raise HTTPException(502, f"Webhook yanıt kodu: {resp.status_code}")
        return {"ok": True, "status_code": resp.status_code}
    except httpx.TimeoutException:
        raise HTTPException(504, "Webhook zaman aşımı")
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════
# API Testing
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/api-tests/import-postman",
    response_model=PostmanImportResponse,
    status_code=201,
)
def import_postman_collection(
    project_id: str,
    body: PostmanImportRequest,
    db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """Postman koleksiyonunu ice aktarir."""
    _get_project(db, project_id, user)
    collection_doc = body.collection or {}
    info = collection_doc.get("info") or {}
    collection_name = (body.name or info.get("name") or "Imported Postman Collection").strip()
    flattened_items = _extract_postman_items(collection_doc.get("item") or [])

    variables = {
        str(var.get("key", "")).strip(): str(var.get("value", ""))
        for var in collection_doc.get("variable") or []
        if str(var.get("key", "")).strip()
    }
    base_url = (body.base_url or variables.get("baseUrl") or variables.get("base_url") or "").strip()
    collection_headers = _header_array_to_dict(
        ((collection_doc.get("auth") or {}).get("apikey") or [])
    )

    col = TspmApiCollection(
        project_id=project_id,
        name=collection_name,
        description=(info.get("description") or "")[:2000],
        base_url=base_url,
        headers=collection_headers,
    )
    db.add(col)
    db.flush()

    imported = 0
    skipped = 0
    for order, (folders, item) in enumerate(flattened_items):
        request = item.get("request") or {}
        method = str(request.get("method", "GET")).upper().strip() or "GET"
        path = _postman_url_to_path(request.get("url"))
        name_prefix = " / ".join(filter(None, [body.folder_prefix.strip(), *folders]))
        request_name = item.get("name") or f"{method} {path}"
        if name_prefix:
            request_name = f"{name_prefix} / {request_name}"
        if not path:
            skipped += 1
            continue
        api_request = TspmApiRequest(
            collection_id=col.id,
            name=request_name[:300],
            method=method,
            path=path,
            headers=_header_array_to_dict(request.get("header")),
            body=_postman_body_to_json(request.get("body")),
            assertions=_parse_postman_assertions(item.get("event")),
            order=order,
        )
        db.add(api_request)
        imported += 1

    db.commit()
    db.refresh(col)
    return PostmanImportResponse(
        collection=ApiCollectionOut(
            id=col.id,
            name=col.name,
            description=col.description,
            base_url=col.base_url,
            request_count=imported,
            created_at=col.created_at,
        ),
        imported_request_count=imported,
        skipped_request_count=skipped,
    )


@router.post(
    "/projects/{project_id}/api-tests/collections",
    response_model=ApiCollectionOut,
    status_code=201,
)
def create_api_collection(
    project_id: str, body: ApiCollectionCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """Yeni API test koleksiyonu olusturur."""
    _get_project(db, project_id, user)
    col = TspmApiCollection(
        project_id=project_id,
        name=body.name,
        description=body.description,
        base_url=body.base_url,
        headers=body.headers,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return ApiCollectionOut(
        id=col.id, name=col.name, description=col.description,
        base_url=col.base_url, request_count=0, created_at=col.created_at,
    )


@router.get("/projects/{project_id}/api-tests/collections", response_model=list[ApiCollectionOut])
def list_api_collections(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """API test koleksiyonlarini listeler."""
    _get_project(db, project_id, user)
    cols = list(db.scalars(
        select(TspmApiCollection)
        .where(TspmApiCollection.project_id == project_id)
        .order_by(TspmApiCollection.created_at.desc())
        .offset(skip).limit(limit)
    ))
    if not cols:
        return []
    # N+1 önleme: tek GROUP BY
    col_ids = [c.id for c in cols]
    rc_rows = db.execute(
        select(TspmApiRequest.collection_id, func.count().label("cnt"))
        .where(TspmApiRequest.collection_id.in_(col_ids))
        .group_by(TspmApiRequest.collection_id)
    ).all()
    rc_map: dict[str, int] = {row.collection_id: row.cnt for row in rc_rows}
    return [
        ApiCollectionOut(
            id=c.id, name=c.name, description=c.description,
            base_url=c.base_url, request_count=rc_map.get(c.id, 0), created_at=c.created_at,
        )
        for c in cols
    ]


@router.get(
    "/projects/{project_id}/api-tests/collections/{collection_id}",
    response_model=ApiCollectionDetailOut,
)
def get_api_collection(project_id: str, collection_id: str, db: DB, user: CurrentUser):
    """API test koleksiyonu detayini getirir."""
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    return col


@router.delete("/projects/{project_id}/api-tests/collections/{collection_id}", status_code=204)
def delete_api_collection(
    project_id: str, collection_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """API test koleksiyonunu siler."""
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    db.delete(col)
    db.commit()


@router.post(
    "/projects/{project_id}/api-tests/collections/{collection_id}/requests",
    response_model=ApiRequestOut,
    status_code=201,
)
def create_api_request(
    project_id: str, collection_id: str, body: ApiRequestCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """Koleksiyona yeni API istegi ekler."""
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    req = TspmApiRequest(
        collection_id=collection_id,
        name=body.name,
        method=body.method,
        path=body.path,
        headers=body.headers,
        body=body.body,
        assertions=body.assertions,
        order=body.order,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.get(
    "/projects/{project_id}/api-tests/collections/{collection_id}/requests",
    response_model=list[ApiRequestOut],
)
def list_api_requests(project_id: str, collection_id: str, db: DB, user: CurrentUser):
    """Koleksiyondaki API isteklerini listeler."""
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    return list(db.scalars(
        select(TspmApiRequest)
        .where(TspmApiRequest.collection_id == collection_id)
        .order_by(TspmApiRequest.order)
    ))


@router.put(
    "/projects/{project_id}/api-tests/collections/{collection_id}/requests/{request_id}",
    response_model=ApiRequestOut,
)
def update_api_request(
    project_id: str, collection_id: str, request_id: str,
    body: ApiRequestUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """API istegi bilgilerini gunceller."""
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    req = db.get(TspmApiRequest, request_id)
    if req is None or req.collection_id != collection_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "İstek bulunamadı")
    if body.name is not None:
        req.name = body.name
    if body.method is not None:
        req.method = body.method
    if body.path is not None:
        req.path = body.path
    if body.headers is not None:
        req.headers = body.headers
    if body.body is not None:
        req.body = body.body
    if body.assertions is not None:
        req.assertions = body.assertions
    if body.order is not None:
        req.order = body.order
    db.commit()
    db.refresh(req)
    return req


@router.delete(
    "/projects/{project_id}/api-tests/collections/{collection_id}/requests/{request_id}",
    status_code=204,
)
def delete_api_request(
    project_id: str, collection_id: str, request_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """API istegini siler."""
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    req = db.get(TspmApiRequest, request_id)
    if req is None or req.collection_id != collection_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "İstek bulunamadı")
    db.delete(req)
    db.commit()


@router.post(
    "/projects/{project_id}/api-tests/collections/{collection_id}/run",
    response_model=ApiTestRunOut,
)
def run_api_collection(
    project_id: str, collection_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.API_TEST_MANAGE))],
):
    """API test koleksiyonunu calistirir."""
    _get_project(db, project_id, user)
    col = db.get(TspmApiCollection, collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koleksiyon bulunamadı")
    requests = list(db.scalars(
        select(TspmApiRequest)
        .where(TspmApiRequest.collection_id == collection_id)
        .order_by(TspmApiRequest.order)
    ))
    results: list[dict] = []
    base_url = col.base_url or ""
    if _is_disallowed_api_host(base_url):
        for req in requests:
            results.append({
                "request_id": req.id,
                "name": req.name,
                "status_code": 0,
                "duration_ms": 0,
                "passed": False,
                "assertions": [],
                "error": f"Disallowed target host: {base_url}",
            })
        run = TspmApiTestRun(collection_id=collection_id, status="completed", results=results)
        db.add(run)
        db.commit()
        db.refresh(run)
        return run
    with httpx.Client(timeout=30) as client:
        for req in requests:
            url = f"{base_url.rstrip('/')}{req.path}"
            merged_headers = {**(col.headers or {}), **(req.headers or {})}
            try:
                resp = client.request(req.method, url, headers=merged_headers, json=req.body)
                passed, checks = _evaluate_api_assertions(req.assertions, resp)
                results.append({
                    "request_id": req.id,
                    "name": req.name,
                    "status_code": resp.status_code,
                    "duration_ms": resp.elapsed.total_seconds() * 1000,
                    "passed": passed,
                    "assertions": checks,
                    "response_body": resp.text[:2000],
                })
            except Exception as exc:
                results.append({
                    "request_id": req.id,
                    "name": req.name,
                    "status_code": 0,
                    "duration_ms": 0,
                    "passed": False,
                    "assertions": [],
                    "error": str(exc),
                })
    run = TspmApiTestRun(collection_id=collection_id, status="completed", results=results)
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


@router.get("/projects/{project_id}/api-tests/runs", response_model=list[ApiTestRunOut])
def list_api_runs(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """API test kosularini listeler."""
    _get_project(db, project_id, user)
    return list(db.scalars(
        select(TspmApiTestRun)
        .join(TspmApiCollection, TspmApiTestRun.collection_id == TspmApiCollection.id)
        .where(TspmApiCollection.project_id == project_id)
        .order_by(TspmApiTestRun.created_at.desc())
        .offset(skip).limit(limit)
    ))


@router.get("/projects/{project_id}/api-tests/runs/{api_run_id}", response_model=ApiTestRunOut)
def get_api_run(project_id: str, api_run_id: str, db: DB, user: CurrentUser):
    """API test kosusu detayini getirir."""
    run = db.get(TspmApiTestRun, api_run_id)
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test koşusu bulunamadı")
    col = db.get(TspmApiCollection, run.collection_id)
    if col is None or col.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Test koşusu bulunamadı")
    return run


# ═══════════════════════════════════════════════════════════════════════
# Project Members
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/members", response_model=ProjectMemberOut, status_code=201)
def add_project_member(
    project_id: str, body: ProjectMemberCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """Projeye yeni uye ekler."""
    _get_project(db, project_id, user)
    # user_id'nin gerçekte var olduğunu önceden doğrula — FK ihlalini
    # HTTP 500 yerine 404 olarak raporla.
    target_user = db.get(User, body.user_id)
    if target_user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Kullanıcı bulunamadı")
    member = TspmProjectMember(
        project_id=project_id,
        user_id=body.user_id,
        role=body.role,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.get("/projects/{project_id}/members", response_model=list[ProjectMemberOut])
def list_project_members(
    project_id: str, db: DB, user: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """Proje uyelerini listeler."""
    _get_project(db, project_id, user)
    return list(db.scalars(
        select(TspmProjectMember)
        .where(TspmProjectMember.project_id == project_id)
        .order_by(TspmProjectMember.created_at.desc())
        .offset(skip).limit(limit)
    ))


@router.delete("/projects/{project_id}/members/{member_id}", status_code=204)
def remove_project_member(
    project_id: str, member_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.PROJECT_UPDATE))],
):
    """Projeden uyeyi kaldirir."""
    member = db.get(TspmProjectMember, member_id)
    if member is None or member.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Üye bulunamadı")
    db.delete(member)
    db.commit()


# ═══════════════════════════════════════════════════════════════════════
# Wizard — Proje Sihirbazı
# ═══════════════════════════════════════════════════════════════════════

ENGINE_BASE_URL = os.environ.get("ENGINE_BASE_URL", "http://127.0.0.1:5001")
_ENGINE_KEY = os.environ.get("ENGINE_INTERNAL_KEY", "bgts-internal-key-change-me")
_IKEY = {"X-Internal-Key": _ENGINE_KEY}


@router.post("/projects/{project_id}/wizard/analyze")
def wizard_analyze(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Analiz dokümanından AI ile manuel test senaryoları + BDD üretir.
    Nexus QA: Önce AI Gateway (Groq→Gemini→Ollama→g4f) denenir,
    başarısız olursa eski engine/backend AI yolu kullanılır.
    """
    _get_project(db, project_id, user)
    text = body.get("text", "")
    extra = body.get("extra_instructions", "")
    if not text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Analiz metni gereklidir")

    results: dict = {"manual_tests": [], "bdd_scenarios": [], "ai_provider": None}

    # ── 1) Nexus QA AI Gateway (birincil yol) ──────────────────────────────
    try:
        from app.domains.ai.gateway_client import gateway_analyze_document
        analysis = gateway_analyze_document(
            doc_text=text,
            extra_instructions=extra,
            project_id=project_id,
        )
        # AI Gateway analizi → BDD senaryolara çevir
        modules = analysis.get("modules", [])
        bdd_from_gateway = []
        for module in modules:
            module_name = module.get("name", "Genel")
            for area in module.get("test_areas", []):
                bdd_from_gateway.append({
                    "title": f"{module_name} — {area}",
                    "description": module.get("description", ""),
                    "tags": [module_name.lower().replace(" ", "_"), "ai-generated"],
                    "steps": [
                        {"keyword": "Olduğu gibi", "text": f"kullanıcı {module_name} modülündedir"},
                        {"keyword": "Eğer", "text": f"{area} gerçekleştirilir"},
                        {"keyword": "O zaman", "text": "işlem başarıyla tamamlanır"},
                    ],
                })

        # Manuel testler için test case üret
        import json as _json
        from app.domains.ai.gateway_client import gateway_complete
        manual_raw = gateway_complete(
            task_type="generate_test_cases",
            user_message=f"Doküman:\n{text[:3000]}\n\nEk talimatlar: {extra}",
            temperature=0.5,
            max_tokens=3000,
            project_id=project_id,
        )
        manual_cleaned = manual_raw.strip()
        if manual_cleaned.startswith("```"):
            lines = manual_cleaned.split("\n")
            manual_cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        try:
            manual_parsed = _json.loads(manual_cleaned)
            manual_tests_raw = manual_parsed if isinstance(manual_parsed, list) else manual_parsed.get("test_cases", [])
            # Frontend formatına çevir
            results["manual_tests"] = [
                {
                    "title": tc.get("title", "Test Case"),
                    "steps": [
                        {"action": step, "expected": f"{step} başarılı"}
                        for step in (tc.get("steps", []) if isinstance(tc.get("steps", []), list) else [])
                    ] or [{"action": tc.get("description", "Adım"), "expected": tc.get("expected_result", "Başarılı")}],
                }
                for tc in manual_tests_raw[:20]  # max 20 test
            ]
        except _json.JSONDecodeError:
            results["manual_tests"] = []

        results["bdd_scenarios"] = bdd_from_gateway
        results["ai_provider"] = "nexusqa-gateway"
        results["analysis_summary"] = {
            "modules": len(modules),
            "critical_flows": analysis.get("critical_flows", []),
            "total_estimated": analysis.get("total_estimated_cases", 0),
        }

    except Exception as gateway_err:
        # AI Gateway başarısız — eski yola düş
        import logging
        logging.getLogger(__name__).warning(
            f"AI Gateway başarısız, eski yol deneniyor: {gateway_err}"
        )
        results["gateway_error"] = str(gateway_err)

        # ── 2) Eski yol: BDD generator ──────────────────────────────────────
        try:
            from app.domains.tspm.bdd_generator import generate_bdd_scenarios
            bdd = generate_bdd_scenarios(text, extra)
            results["bdd_scenarios"] = bdd
        except Exception as e:
            results["bdd_error"] = str(e)

        # ── 3) Eski yol: Engine veya backend AI ─────────────────────────────
        try:
            resp = httpx.post(
                f"{ENGINE_BASE_URL}/api/wizard/analyze-document",
                json={"text": text},
                headers=_IKEY,
                timeout=60.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                results["manual_tests"] = data.get("manual_tests", [])
        except Exception:
            try:
                from app.domains.ai.service import call_llm
                import json as _json
                raw = call_llm(
                    "Sen QA mühendisisin. Dokümanlardan manuel test senaryosu üret.",
                    f"Doküman:\n{text}\n\nJSON liste döndür: [{{\"title\":\"...\", \"steps\":[{{\"action\":\"...\", \"expected\":\"...\"}}]}}]",
                    json_mode=True,
                )
                parsed = _json.loads(raw)
                results["manual_tests"] = parsed if isinstance(parsed, list) else parsed.get("tests", [])
            except Exception as e2:
                results["manual_error"] = str(e2)

    return results


@router.post("/projects/{project_id}/wizard/upload-document")
async def wizard_upload_document(
    project_id: str,
    file: UploadFile = File(...),
    db: DB = ...,
    user: CurrentUser = ...,
):
    """
    Nexus QA Faz 2 — Doküman Yükleme + AI Analiz Pipeline
    PDF, DOCX, TXT, MD dosyalarını parse eder ve AI Gateway'e gönderir.
    Büyük dosyalar chunk'lara bölünür; her chunk ayrı analiz edilir.

    Dönen format:
    {
        "full_text": "...",
        "filename": "analiz.pdf",
        "format": "pdf",
        "page_count": 12,
        "word_count": 3400,
        "chunks": 2,
        "needs_chunking": true,
        "sections": ["Giriş", "Modüller"],
        "preview": "ilk 500 karakter..."
    }
    """
    _get_project(db, project_id, user)

    # Dosya boyutu kontrolü (max 20MB)
    MAX_SIZE = 20 * 1024 * 1024
    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Dosya çok büyük ({len(data) // 1024}KB). Maksimum: 20MB",
        )

    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Dosya boş")

    # Format kontrolü
    allowed_exts = {"pdf", "docx", "txt", "md"}
    filename = file.filename or "document.txt"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "txt"
    if ext not in allowed_exts:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Desteklenmeyen format: .{ext}. Desteklenenler: {', '.join(allowed_exts)}",
        )

    # Dokümanı parse et — blocking I/O'yu event loop dışına taşı
    import asyncio
    from app.domains.tspm.document_parser import parse_document
    doc = await asyncio.to_thread(parse_document, data, filename, file.content_type)

    if doc.error:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Doküman parse hatası: {doc.error}",
        )

    if doc.is_empty():
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Doküman içeriği boş veya okunamıyor",
        )

    return {
        "full_text": doc.full_text,
        "filename": doc.filename,
        "format": doc.format,
        "page_count": doc.page_count,
        "word_count": doc.word_count,
        "char_count": doc.char_count,
        "chunk_count": len(doc.chunks),
        "needs_chunking": doc.needs_chunking(),
        "sections": doc.sections[:20],   # İlk 20 başlık
        "preview": doc.full_text[:500],  # İlk 500 karakter önizleme
        "message": f"Doküman başarıyla yüklendi: {doc.word_count} kelime, {len(doc.chunks)} chunk",
    }


@router.post("/projects/{project_id}/wizard/analyze-chunked")
async def wizard_analyze_chunked(
    project_id: str,
    body: dict,
    db: DB,
    user: CurrentUser,
):
    """
    Nexus QA Faz 2 — Chunk'lı AI Analiz Pipeline
    Büyük dokümanlar için her chunk ayrı analiz edilir, sonuçlar birleştirilir.

    body: {
        "chunks": ["chunk1 metni", "chunk2 metni"],
        "filename": "analiz.pdf",
        "extra_instructions": "opsiyonel"
    }
    """
    _get_project(db, project_id, user)
    chunks: list[str] = body.get("chunks", [])
    filename = body.get("filename", "document")
    extra = body.get("extra_instructions", "")

    if not chunks:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "chunks listesi boş")

    from app.domains.ai.gateway_client import gateway_analyze_document

    all_modules = []
    all_critical_flows = []
    total_estimated = 0
    errors = []

    for i, chunk in enumerate(chunks[:5]):  # Max 5 chunk analiz et
        if not chunk.strip():
            continue
        try:
            analysis = gateway_analyze_document(
                doc_text=chunk,
                extra_instructions=extra + (f"\nBu metin, orijinal dokümanın {i+1}/{len(chunks)}. parçasıdır." if len(chunks) > 1 else ""),
                project_id=project_id,
            )
            modules = analysis.get("modules", [])
            all_modules.extend(modules)
            all_critical_flows.extend(analysis.get("critical_flows", []))
            total_estimated += analysis.get("total_estimated_cases", 0)
        except Exception as e:
            logger.warning("Document chunk analysis failed for project %s chunk %s: %s", project_id, i + 1, e)
            errors.append(f"Chunk {i+1}: {str(e)[:100]}")

    # Tekrar eden modülleri temizle
    seen_names = set()
    unique_modules = []
    for m in all_modules:
        name = m.get("name", "")
        if name not in seen_names:
            seen_names.add(name)
            unique_modules.append(m)

    return {
        "modules": unique_modules,
        "critical_flows": list(dict.fromkeys(all_critical_flows)),  # Tekrar temizle
        "total_estimated_cases": total_estimated,
        "chunks_analyzed": len(chunks),
        "errors": errors,
        "suggested_test_types": ["smoke", "regression", "e2e", "api"],
    }


@router.post("/projects/{project_id}/database/test-connection")
def test_db_connection(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Verilen DB bağlantı dizesini test eder; başarılı ise şema özetini döner."""
    _get_project(db, project_id, user)
    connection_string: str = body.get("connection_string", "").strip()
    if not connection_string:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "connection_string gereklidir")

    try:
        from sqlalchemy import create_engine, text, inspect as sa_inspect

        # psycopg2 yoksa asyncpg veya psycopg3 olabilir; driver prefix normalize et
        if connection_string.startswith("postgresql://") or connection_string.startswith("postgres://"):
            connection_string = connection_string.replace("postgresql://", "postgresql+psycopg2://", 1)
            connection_string = connection_string.replace("postgres://", "postgresql+psycopg2://", 1)

        engine = create_engine(connection_string, pool_pre_ping=True, connect_args={"connect_timeout": 8})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            inspector = sa_inspect(engine)
            tables = inspector.get_table_names()

        engine.dispose()
        return {
            "ok": True,
            "table_count": len(tables),
            "tables": tables[:30],  # ilk 30 tablo
            "message": f"Bağlantı başarılı — {len(tables)} tablo bulundu",
        }
    except Exception as exc:
        logger.exception("Database connection test failed for project %s", project_id)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Bağlantı hatası: {exc}")


@router.post("/projects/{project_id}/wizard/crawl")
def wizard_crawl(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Engine crawler ile hedef uygulamayı keşfeder."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/wizard/crawl",
            json=body,
            headers=_IKEY,
            timeout=120.0,
        )
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru (engine) çalışmıyor. Port 5001'i kontrol edin.")
    except Exception as e:
        logger.exception("Wizard crawl failed for project %s", project_id)
        raise HTTPException(500, str(e))


@router.post("/projects/{project_id}/wizard/discover-selectors")
def wizard_discover(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Tek sayfadaki tüm elementlerin selector/XPath bilgilerini keşfeder."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/wizard/discover-selectors",
            json=body,
            headers=_IKEY,
            timeout=60.0,
        )
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru çalışmıyor.")
    except Exception as e:
        logger.exception("Wizard selector discovery failed for project %s", project_id)
        raise HTTPException(500, str(e))


@router.post("/projects/{project_id}/wizard/monkey-test")
def wizard_monkey_test(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Monkey testing — rastgele etkileşim ile hata avcılığı."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/wizard/monkey-test",
            json=body,
            headers=_IKEY,
            timeout=180.0,
        )
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru çalışmıyor.")
    except Exception as e:
        logger.exception("Wizard monkey test failed for project %s", project_id)
        raise HTTPException(500, str(e))


@router.post("/projects/{project_id}/wizard/generate-automation")
def wizard_generate_automation(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Senaryolardan + selectorlardan otomasyon kodu üretir.
    Frontend 'scenario_ids' (UUID list) gönderir; biz DB'den çekip
    engine'in beklediği {title, steps} formatına dönüştürürüz.
    """
    project = _get_project(db, project_id, user)

    # ── 1. scenario_ids → senaryo objeleri ──────────────────────────────
    scenario_ids: list[str] = body.get("scenario_ids", [])

    # Eğer zaten tam senaryo objeleri geldiyse (eski kullanım) direkt kullan
    raw_scenarios: list[dict] = body.get("scenarios", [])

    if scenario_ids and not raw_scenarios:
        from app.domains.tspm.models import TspmScenario
        rows = db.scalars(
            select(TspmScenario).where(
                TspmScenario.id.in_(scenario_ids),
                TspmScenario.project_id == project_id,
            )
        ).all()

        for row in rows:
            # steps JSONB: [{keyword, text}] veya [{action, expected}] olabilir
            raw_steps = row.steps or []
            engine_steps: list[dict] = []
            for s in raw_steps:
                if "action" in s:
                    engine_steps.append({"action": s["action"], "expected": s.get("expected", "")})
                elif "text" in s:
                    kw = s.get("keyword", "").strip().upper()
                    text_val: str = s["text"]
                    # "eylem → beklenti" şeklinde kaydedilmişse böl
                    if "→" in text_val:
                        parts = text_val.split("→", 1)
                        engine_steps.append({"action": parts[0].strip(), "expected": parts[1].strip()})
                    elif kw in ("GIVEN", "WHEN", "AND", "BUT", "VE", "EĞER", "OLDUĞU GİBİ"):
                        engine_steps.append({"action": text_val, "expected": ""})
                    else:  # THEN / O ZAMAN
                        if engine_steps:
                            engine_steps[-1]["expected"] = text_val
                        else:
                            engine_steps.append({"action": "", "expected": text_val})
                else:
                    engine_steps.append({"action": str(s), "expected": ""})

            raw_scenarios.append({
                "title": row.title,
                "steps": engine_steps,
            })

    if not raw_scenarios:
        raise HTTPException(400, "Senaryo bulunamadı. Önce test case kaydedin.")

    # ── 2. Engine'e ilet ────────────────────────────────────────────────
    engine_payload = {
        "scenarios": raw_scenarios,
        "selectors": body.get("selectors", []),
        "url": body.get("url", ""),
        "project_name": (project.name or "project").replace(" ", "_").lower()[:30],
    }

    write_to_disk: bool = body.get("write_to_disk", True)

    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/wizard/generate-automation",
            json=engine_payload,
            headers=_IKEY,
            timeout=120.0,
        )
        result = resp.json()
        if (
            not resp.is_success
            or result.get("error")
            or (not result.get("feature_files") and not result.get("test_files"))
        ):
            result = _fallback_automation(raw_scenarios, engine_payload["project_name"])
    except httpx.ConnectError:
        result = _fallback_automation(raw_scenarios, engine_payload["project_name"])
    except Exception as e:
        logger.exception("Wizard automation generation failed for project %s", project_id)
        raise HTTPException(500, str(e))

    # ── 3. Üretilen dosyaları diske yaz ─────────────────────────────────
    if write_to_disk:
        _write_generated_files(result, project_id, engine_payload["project_name"])

    return result


def _write_generated_files(result: dict, project_id: str, project_name: str) -> None:
    """Üretilen feature ve .spec.ts dosyalarını e2e/ai-generated/ dizinine yazar."""
    import pathlib, logging
    _log = logging.getLogger(__name__)

    # Proje kökünü bul (backend/app/domains/tspm/router.py → 4 üst)
    base = pathlib.Path(__file__).parent.parent.parent.parent.parent
    out_dir = base / "e2e" / "ai-generated" / project_name
    out_dir.mkdir(parents=True, exist_ok=True)

    written: list[str] = []
    for ff in result.get("feature_files", []):
        name = ff.get("name", "").strip()
        content = ff.get("content", "")
        if not name or not content:
            continue
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(str(path.relative_to(base)))

    for tf in result.get("test_files", []):
        name = tf.get("name", "").strip()
        content = tf.get("content", "")
        if not name or not content:
            continue
        path = out_dir / name
        path.write_text(content, encoding="utf-8")
        written.append(str(path.relative_to(base)))

    if written:
        _log.info("Otomasyon dosyaları yazıldı: %s", written)
        result["written_files"] = written
        result["output_dir"] = str(out_dir.relative_to(base))


def _fallback_automation(scenarios: list[dict], project_name: str) -> dict:
    """Engine erişilemezse temel Gherkin + Playwright şablonu üretir."""
    feature_files = []
    test_files = []

    for i, sc in enumerate(scenarios, 1):
        title = sc.get("title", f"Senaryo_{i}")
        steps = sc.get("steps", [])

        # Gherkin
        gherkin_lines = [
            "# language: tr",
            f"Özellik: {project_name.replace('_', ' ').title()}",
            "",
            f"  Senaryo: {title}",
        ]
        for step in steps:
            action = step.get("action", "")
            expected = step.get("expected", "")
            if action:
                gherkin_lines.append(f"    Eğer {action}")
            if expected:
                gherkin_lines.append(f"    O zaman {expected}")

        gherkin_content = "\n".join(gherkin_lines)
        feature_files.append({
            "name": f"{project_name}_{i}.feature",
            "content": gherkin_content,
            "scenario_title": title,
        })

        # Playwright TypeScript
        safe_name = title.lower().replace(" ", "_").replace("'", "")[:40]
        ts_steps = "\n".join(
            f"  // {step.get('action', '')} → {step.get('expected', '')}"
            for step in steps
        )
        ts_content = (
            "import { test, expect } from '@playwright/test';\n\n"
            f"test('{title}', async ({{ page }}) => {{\n"
            f"{ts_steps}\n"
            "  // TODO: Adımları otomasyona çevirin\n"
            "});\n"
        )
        test_files.append({
            "name": f"test_{project_name}_{i}.ts",
            "content": ts_content,
            "scenario_title": title,
        })

    return {"feature_files": feature_files, "test_files": test_files}


# ═══════════════════════════════════════════════════════════════════════
# NexusQA Otomasyon — Lokator + Feature Üretimi
# ═══════════════════════════════════════════════════════════════════════

NEXUSQA_STEP_DEFS = """
NexusQA adım tanımları (Java/Selenium/Cucumber):
- Given I open the application url "URL"
- When I click on "LocatorKey"
- When I double click on "LocatorKey"
- When I enter "value" into the input "LocatorKey"
- When I clear the input "LocatorKey"
- When I clear and enter "value" into the input "LocatorKey"
- Then I see the element "LocatorKey"
- Then I don't see element "LocatorKey"
- Then I verify element "LocatorKey" text is "value"
- When I wait for {int} seconds
- When I wait for element "LocatorKey" to be clickable

Test verisi referansları:
- @key  → data.json dosyasındaki değeri okur
- +-key → 15 karakterlik rastgele string üretir
"""


def _sanitize_locator_key(value: str, fallback: str = "Element") -> str:
    cleaned = re.sub(r"[^0-9A-Za-zÇĞİÖŞÜçğıöşü]+", " ", str(value or "")).strip()
    if not cleaned:
        return fallback
    parts = [part for part in cleaned.split() if part]
    pascal = "".join(part[:1].upper() + part[1:] for part in parts)
    return pascal or fallback


@router.post("/projects/{project_id}/wizard/generate-nexusqa")
@router.post("/projects/{project_id}/wizard/generate-maviyaka")
def wizard_generate_nexusqa(project_id: str, body: dict, db: DB, user: CurrentUser):
    """NexusQA formatında Cucumber feature dosyaları üretir."""
    project = _get_project(db, project_id, user)

    scenario_ids: list[str] = body.get("scenario_ids", [])
    url: str = body.get("url", "")
    domain: str = body.get("domain", "hrnexusqa")
    locators: list[dict] = body.get("locators", [])

    # Senaryoları DB'den çek
    scenarios: list[dict] = []
    if scenario_ids:
        rows = db.scalars(
            select(TspmScenario).where(
                TspmScenario.id.in_(scenario_ids),
                TspmScenario.project_id == project_id,
            )
        ).all()
        for row in rows:
            scenarios.append({"title": row.title, "steps": row.steps or []})

    if not scenarios:
        raise HTTPException(400, "Senaryo bulunamadı")

    locator_keys = [l.get("key", "") for l in locators if l.get("key")]
    locator_list_str = "\n".join(f"- {l['key']} ({l.get('type','?')}={l.get('value','?')})" for l in locators[:30])

    # AI ile NexusQA feature dosyaları üret
    try:
        from app.domains.ai.service import call_llm
        import json as _json

        features_out = []
        test_data_map: dict[str, str] = {}

        for sc in scenarios:
            title = sc["title"]
            steps_txt = "\n".join(
                f"  {s.get('keyword','')} {s.get('text', s.get('action',''))}"
                for s in sc["steps"]
            ) or f"(adım tanımlı değil)"

            prompt = f"""Aşağıdaki test senaryosunu NexusQA Cucumber feature dosyasına çevir.

{NEXUSQA_STEP_DEFS}

Mevcut lokator listesi:
{locator_list_str or "(lokator tanımlı değil)"}

Hedef URL: {url}
Domain: {domain}

Test senaryosu:
Başlık: {title}
Adımlar:
{steps_txt}

KURALLAR:
1. Yalnızca yukarıdaki NexusQA adım tanımlarını kullan
2. Lokator adları olarak mevcut lokator listesindeki KEY değerlerini kullan (yoksa uygun Türkçe/İngilizce PascalCase isim koy)
3. Test verisini @dataKey şeklinde referansla; data_json nesnesine de ekle
4. Doğrudan JSON döndür: {{"title": "...", "content": "Feature: ...\\n  Scenario: ...\\n    ...", "data_json": {{"key": "value"}}}}
5. JSON dışında hiçbir şey yazma"""

            raw = call_llm(
                "Sen NexusQA Cucumber uzmanısın. JSON çıktısı ver.",
                prompt,
                json_mode=True,
            )
            try:
                parsed = _json.loads(raw) if isinstance(raw, str) else raw
                features_out.append({
                    "title": parsed.get("title", title),
                    "content": parsed.get("content", f"Feature: {title}\n\n  Scenario: {title}\n    Given I open the application url \"{url}\"\n"),
                })
                test_data_map.update(parsed.get("data_json", {}))
            except Exception:
                # Fallback: minimal NexusQA feature
                features_out.append({
                    "title": title,
                    "content": (
                        f"Feature: {title}\n\n"
                        f"  Scenario: {title}\n"
                        f"    Given I open the application url \"{url}\"\n"
                        f"    When I click on \"LoginButton\"\n"
                        f"    Then I see the element \"HomePage\"\n"
                    ),
                })

        return {"features": features_out, "test_data": test_data_map}

    except Exception as e:
        # Fallback without AI
        features_out = []
        for sc in scenarios:
            title = sc["title"]
            features_out.append({
                "title": title,
                "content": (
                    f"Feature: {title}\n\n"
                    f"  Scenario: {title}\n"
                    f"    Given I open the application url \"{url}\"\n"
                    f"    When I click on \"Element\"\n"
                    f"    Then I see the element \"Result\"\n"
                ),
            })
        return {"features": features_out, "test_data": {}}


@router.post("/projects/{project_id}/wizard/crawl-locators")
def wizard_crawl_locators(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Hedef URL'yi Playwright ile tarar, NexusQA lokator JSON üretir."""
    _get_project(db, project_id, user)
    url: str = body.get("url", "")
    if not url:
        raise HTTPException(400, "url zorunlu")

    # URL normalizasyonu — engine https zorunlu
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    # Engine'e proxy et; yoksa AI ile örnek üret
    engine_ok = False
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/wizard/discover-selectors",
            json={"url": url, "domain": body.get("domain", "")},
            headers=_IKEY,
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        if data.get("error"):
            raise RuntimeError(f"engine error: {data.get('error')}")

        # Engine response şeması:
        # { "elements": [{ "tag", "type", "text", "id", "name", "css", "xpath", "testid", ... }] }
        raw = data.get("elements") or data.get("selectors") or []
        locators = []
        used_keys: set[str] = set()
        for el in raw:
            if not isinstance(el, dict):
                continue
            # Görünmeyen elementleri atla
            if el.get("is_visible") is False:
                continue

            tag = (el.get("tag") or "").lower()
            el_type = (el.get("type") or "").lower()
            text = (el.get("text") or "").strip()[:30]
            el_id = el.get("id")
            el_name = el.get("name")
            testid = el.get("testid")
            css_sel = el.get("css") or ""
            xpath_sel = el.get("xpath") or ""
            # Geri uyumluluk (eski şema)
            legacy_sel = el.get("selector") or el.get("value") or ""

            # Öncelik sırası: id > testid > name > css > xpath
            loc_type: str | None = None
            loc_value: str | None = None
            if el_id:
                loc_type, loc_value = "id", el_id
            elif testid:
                loc_type, loc_value = "css", f'[data-testid="{testid}"]'
            elif el_name:
                loc_type, loc_value = "name", el_name
            elif css_sel:
                if css_sel.startswith("#"):
                    loc_type, loc_value = "id", css_sel[1:]
                else:
                    loc_type, loc_value = "css", css_sel
            elif xpath_sel:
                loc_type, loc_value = "xpath", xpath_sel
            elif legacy_sel:
                if legacy_sel.startswith("#"):
                    loc_type, loc_value = "id", legacy_sel[1:]
                elif legacy_sel.startswith(".") or "[" in legacy_sel:
                    loc_type, loc_value = "css", legacy_sel
                else:
                    loc_type, loc_value = "xpath", legacy_sel

            if not loc_value:
                continue

            base_key = _sanitize_locator_key(text or el_name or el_id or tag or "Element")
            suffix = ""
            if tag == "input" or el_type in {"textbox", "text", "email", "password", "search"}:
                suffix = "Input"
            elif tag == "button" or el_type == "button":
                suffix = "Button"
            elif tag == "a" or el_type == "link":
                suffix = "Link"
            key = f"{base_key}{suffix}" if suffix and not base_key.endswith(suffix) else base_key

            # Unique key garantisi
            final_key = key
            i = 2
            while final_key in used_keys:
                final_key = f"{key}{i}"
                i += 1
            used_keys.add(final_key)

            locators.append({"key": final_key, "type": loc_type, "value": loc_value})

        engine_ok = bool(locators)
        if engine_ok:
            return {"locators": locators}
    except Exception:
        pass

    if not engine_ok:
        # AI fallback: URL ve domain'e göre akıllı lokator öner
        try:
            from app.domains.ai.service import call_llm
            import json as _json
            ai_raw = call_llm(
                "Sen NexusQA Selenium lokator uzmanısın. Yalnızca JSON döndür.",
                f"""Hedef URL: {url}
Domain/Uygulama: {body.get('domain', 'web')}

Bu URL'ye ait web uygulaması için en önemli 8-10 UI elementini tahmin ederek NexusQA lokator listesi oluştur.
Her lokator için PascalCase Türkçe/İngilizce key, uygun tip (id/name/css/xpath) ve gerçekçi selector değeri belirle.

JSON formatı: [{{"key": "GirisButon", "type": "id", "value": "btnLogin"}}, ...]
Başka hiçbir şey yazma.""",
                json_mode=True,
            )
            locators = _json.loads(ai_raw) if isinstance(ai_raw, str) else ai_raw
            if isinstance(locators, list):
                return {"locators": locators}
        except Exception:
            pass
        # Son fallback: genel web element örnekleri
        domain_hint = url.lower()
        if any(k in domain_hint for k in ["login", "giris", "auth"]):
            return {"locators": [
                {"key": "KullaniciAdiInput", "type": "name", "value": "username"},
                {"key": "SifreInput", "type": "name", "value": "password"},
                {"key": "GirisButon", "type": "css", "value": "button[type='submit']"},
                {"key": "HataMessaji", "type": "css", "value": ".error-message"},
            ]}
        return {"locators": [
            {"key": "AnaBaslik", "type": "css", "value": "h1"},
            {"key": "NavMenu", "type": "css", "value": "nav"},
            {"key": "GonderButon", "type": "css", "value": "button[type='submit']"},
            {"key": "FormInput", "type": "css", "value": "input[type='text']"},
            {"key": "AramaInput", "type": "css", "value": "input[type='search']"},
        ]}


@router.post("/projects/{project_id}/wizard/suggest-locator")
def wizard_suggest_locator(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Eksik bir lokator key için AI önerisi üretir."""
    _get_project(db, project_id, user)
    key: str = body.get("key", "")
    url: str = body.get("url", "")
    domain: str = body.get("domain", "")

    try:
        from app.domains.ai.service import call_llm
        import json as _json
        raw = call_llm(
            "Sen NexusQA Selenium lokator uzmanısın. JSON döndür.",
            f""""{key}" isimli lokator için uygun Selenium lokator öner.
URL: {url}
Domain: {domain}

Lokator tipi id, name, css veya xpath olabilir.
JSON: {{"key": "{key}", "type": "id/name/css/xpath", "value": "selector_değeri"}}
Başka hiçbir şey yazma.""",
            json_mode=True,
        )
        suggestion = _json.loads(raw) if isinstance(raw, str) else raw
        return {"suggestion": suggestion}
    except Exception:
        # Heuristic fallback
        type_ = "id"
        val = key.lower().replace("button", "btn").replace("input", "")
        return {"suggestion": {"key": key, "type": type_, "value": val}}


@router.post("/projects/{project_id}/locators")
def save_locator(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Lokator object repository'ye kaydeder (engine DB'si)."""
    _get_project(db, project_id, user)
    name = body.get("name", "")
    locator_value = body.get("locator_value", "")
    page_url = body.get("page_url", "")
    if not name or not locator_value:
        raise HTTPException(400, "name ve locator_value zorunlu")
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/object-repository",
            json={"name": name, "locator_value": locator_value, "page_url": page_url},
            headers=_IKEY,
            timeout=10.0,
        )
        return resp.json()
    except Exception:
        return {"saved": True, "note": "engine unavailable, skipped"}


@router.post("/projects/{project_id}/wizard/run-nexusqa")
@router.post("/projects/{project_id}/wizard/run-maviyaka")
def wizard_run_nexusqa(project_id: str, body: dict, db: DB, user: CurrentUser):
    """NexusQA feature dosyalarını Python Playwright engine ile çalıştırır."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/wizard/run-nexusqa",
            json=body,
            headers=_IKEY,
            timeout=300.0,
        )
        content_type = resp.headers.get("content-type", "")
        if "application/json" in content_type.lower():
            data = resp.json()
        else:
            text = resp.text.strip()
            if resp.is_success:
                data = {
                    "ok": False,
                    "error": "Otomasyon motoru JSON yerine beklenmeyen bir yanıt döndürdü.",
                    "raw_response": text[:2000],
                }
            else:
                # Engine 401/403 dönerse bu BİR UPSTREAM sorunudur (internal
                # key mismatch, session vs.), client'ın auth durumuyla ilgisi yok.
                # Client'ı yanlışlıkla login'e atmasın diye 502'ye normalize edelim.
                upstream_status = 502 if resp.status_code in (401, 403) else resp.status_code
                raise HTTPException(
                    upstream_status,
                    text or "Otomasyon motoru beklenmeyen bir hata döndürdü.",
                )

        if resp.is_error:
            detail = data.get("error") if isinstance(data, dict) else None
            upstream_status = 502 if resp.status_code in (401, 403) else resp.status_code
            raise HTTPException(upstream_status, detail or "MaviYaka koşusu başarısız oldu.")
        return data
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru (port 5001) çalışmıyor.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════
# Monkey Testing — Bağımsız analist endpoint'i
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/monkey-testing/run")
def monkey_testing_run(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Gelişmiş Monkey Testing — analiz ve senaryo üretimi ile."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/monkey-testing/run",
            json=body,
            headers=_IKEY,
            timeout=300.0,
        )
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru (port 5001) çalışmıyor. Lütfen engine servisini başlatın.")
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════
# Önyüz Otomasyon Koşucusu — Engine SSE Proxy
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/automation/run", status_code=200)
def automation_run(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Senaryo listesini engine'in /api/nexus/run endpoint'ine gönderir.
    Body: { scenario_ids: [str], browser?: str, base_url?: str }
    Returns: { run_id: str, browser: str }
    """
    _get_project(db, project_id, user)
    scenario_ids: list[str] = body.get("scenario_ids", [])
    browser: str = str(body.get("browser", "chromium")).lower()
    base_url: str = str(body.get("base_url", "") or "")

    # DB'den senaryo başlık ve adımlarını çek
    from app.domains.tspm.models import TspmScenario as _TspmScenario
    rows = db.scalars(
        select(_TspmScenario).where(
            _TspmScenario.id.in_(scenario_ids),
            _TspmScenario.project_id == project_id,
        )
    ).all()

    scenarios_payload = [
        {
            "id": str(row.id),
            "title": row.title,
            "steps": row.steps or [],
        }
        for row in rows
    ]

    if not scenarios_payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Koşturulacak senaryo bulunamadı")

    try:
        resp = httpx.post(
            f"{ENGINE_BASE_URL}/api/nexus/run",
            json={"scenarios": scenarios_payload, "browser": browser, "base_url": base_url},
            headers=_IKEY,
            timeout=30.0,
        )
        if resp.is_error:
            raise HTTPException(resp.status_code, resp.text or "Engine hatası")
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru (port 5001) çalışmıyor.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/projects/{project_id}/automation/run/{run_id}", status_code=200)
def automation_cancel(project_id: str, run_id: str, user: CurrentUser):
    """Engine'deki çalışan Playwright koşumunu iptal eder."""
    try:
        resp = httpx.delete(
            f"{ENGINE_BASE_URL}/api/run/{run_id}/cancel",
            headers=_IKEY,
            timeout=10.0,
        )
        if resp.status_code == 404:
            return {"ok": True, "note": "Koşum zaten bitmişti"}
        if resp.is_error:
            raise HTTPException(resp.status_code, resp.text)
        return resp.json()
    except httpx.ConnectError:
        raise HTTPException(503, "Otomasyon motoru (port 5001) çalışmıyor.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/projects/{project_id}/automation/stream/{run_id}")
async def automation_stream(project_id: str, run_id: str, user: CurrentUser):
    """
    Engine'in SSE stream'ini /api/run/<run_id>/stream den okuyup tarayıcıya aktarır.
    """
    stream_url = f"{ENGINE_BASE_URL}/api/run/{run_id}/stream"

    async def event_generator():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", stream_url, headers=_IKEY) as r:
                    async for line in r.aiter_lines():
                        if line:
                            yield f"{line}\n\n"
        except httpx.ConnectError:
            yield f"data: {json.dumps({'type':'error','text':'Otomasyon motoru ulaşılamıyor (port 5001).'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type':'error','text':str(e)})}\n\n"
        finally:
            yield f"data: {json.dumps({'type':'done','returncode':-1})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


# ═══════════════════════════════════════════════════════════════════════
# Global Search
# ═══════════════════════════════════════════════════════════════════════

@router.get("/search")
def global_search(q: str = Query("", min_length=1), db: DB = ..., user: CurrentUser = ...):
    """Projeler ve senaryolar üzerinde arama."""
    results = []

    projects = list(db.scalars(
        select(TspmProject).where(TspmProject.name.ilike(f"%{q}%")).limit(5)
    ))
    for p in projects:
        results.append({"type": "project", "id": p.id, "label": p.name, "href": f"/p/{p.id}"})

    scenarios = list(db.scalars(
        select(TspmScenario).where(TspmScenario.title.ilike(f"%{q}%")).limit(10)
    ))
    for s in scenarios:
        results.append({"type": "scenario", "id": s.id, "label": s.title, "href": f"/p/{s.project_id}/scenarios/{s.id}"})

    return {"results": results}


# ═══════════════════════════════════════════════════════════════════════
# Rapor Üretimi
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/executions/{run_id}/report")
def get_execution_report(project_id: str, run_id: str, format: str = "html", db: DB = ..., user: CurrentUser = ...):
    """Bir test koşusu için HTML veya JSON raporu üretir ve indirilir."""
    from fastapi.responses import HTMLResponse, StreamingResponse
    import io, json as _json
    from app.domains.tspm.models import TspmExecution, TspmExecutionResult, TspmScenario

    ex = db.get(TspmExecution, run_id)
    if ex is None or ex.project_id != project_id:
        raise HTTPException(404, "Koşu bulunamadı")

    project = db.get(TspmProject, project_id)
    results = list(db.scalars(
        select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run_id)
    ))
    scenarios = {s.id: s for s in db.scalars(select(TspmScenario).where(TspmScenario.project_id == project_id))}

    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")
    skipped = sum(1 for r in results if r.status not in ("passed", "failed"))
    total = len(results)
    rate = round(passed / total * 100, 1) if total > 0 else 0

    if format == "json":
        data = {
            "execution": {"id": ex.id, "name": ex.name, "status": ex.status, "created_at": ex.created_at.isoformat()},
            "summary": {"total": total, "passed": passed, "failed": failed, "skipped": skipped, "pass_rate": rate},
            "results": [
                {"scenario": scenarios.get(r.scenario_id, {}).title if r.scenario_id in scenarios else r.scenario_id,
                 "status": r.status, "note": r.note or ""}
                for r in results
            ],
        }
        return StreamingResponse(
            io.BytesIO(_json.dumps(data, ensure_ascii=False, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="rapor-{run_id[:8]}.json"'},
        )

    # HTML raporu
    rows_html = "".join(
        f"<tr><td>{scenarios[r.scenario_id].title if r.scenario_id in scenarios else r.scenario_id}</td>"
        f"<td class=\"{'pass' if r.status=='passed' else 'fail' if r.status=='failed' else 'skip'}\">{r.status}</td>"
        f"<td>{r.note or ''}</td></tr>"
        for r in results
    )
    html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<title>Test Raporu — {ex.name}</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem;color:#111}}
h1{{color:#1d4ed8}}table{{width:100%;border-collapse:collapse;margin-top:1rem}}
th,td{{padding:.6rem .8rem;border:1px solid #e5e7eb;text-align:left}}
th{{background:#f9fafb;font-weight:600}}
.pass{{color:#16a34a}}.fail{{color:#dc2626}}.skip{{color:#d97706}}
.summary{{display:flex;gap:2rem;margin:1rem 0;padding:1rem;background:#f0f9ff;border-radius:.5rem}}
.stat{{text-align:center}}.stat-value{{font-size:1.5rem;font-weight:700}}
</style></head><body>
<h1>Test Koşu Raporu</h1>
<p><strong>Proje:</strong> {project.name if project else project_id} &nbsp;|&nbsp;
<strong>Koşu:</strong> {ex.name} &nbsp;|&nbsp;
<strong>Tarih:</strong> {ex.created_at.strftime("%d.%m.%Y %H:%M")}</p>
<div class="summary">
<div class="stat"><div class="stat-value">{total}</div><div>Toplam</div></div>
<div class="stat"><div class="stat-value" style="color:#16a34a">{passed}</div><div>Geçti</div></div>
<div class="stat"><div class="stat-value" style="color:#dc2626">{failed}</div><div>Başarısız</div></div>
<div class="stat"><div class="stat-value">{skipped}</div><div>Atlandı</div></div>
<div class="stat"><div class="stat-value">{rate}%</div><div>Başarı</div></div>
</div>
<table><thead><tr><th>Senaryo</th><th>Durum</th><th>Not</th></tr></thead>
<tbody>{rows_html}</tbody></table>
</body></html>"""
    return StreamingResponse(
        io.BytesIO(html.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="rapor-{run_id[:8]}.html"'},
    )


@router.get("/projects/{project_id}/report/summary")
def get_project_summary_report(project_id: str, format: str = "html", days: int = 30, db: DB = ..., user: CurrentUser = ...):
    """Proje için özet HTML veya JSON raporu üretir (son N gün)."""
    from fastapi.responses import StreamingResponse
    from datetime import datetime, timezone, timedelta
    import io, json as _json
    from app.domains.tspm.models import TspmExecution

    _get_project(db, project_id, user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    execs = list(db.scalars(
        select(TspmExecution)
        .where(TspmExecution.project_id == project_id, TspmExecution.created_at >= since)
        .order_by(TspmExecution.created_at.desc())
    ))
    project = db.get(TspmProject, project_id)

    summary = {
        "project": project.name if project else project_id,
        "period_days": days,
        "total_executions": len(execs),
        "passed": sum(1 for e in execs if e.status == "passed"),
        "failed": sum(1 for e in execs if e.status == "failed"),
        "executions": [{"id": e.id, "name": e.name, "status": e.status, "date": e.created_at.isoformat()} for e in execs[:20]],
    }

    if format == "json":
        return StreamingResponse(
            io.BytesIO(_json.dumps(summary, ensure_ascii=False, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=\"ozet-rapor.json\""},
        )

    rows = "".join(
        f"<tr><td>{e['name']}</td><td class=\"{'pass' if e['status']=='passed' else 'fail'}\">{e['status']}</td><td>{e['date'][:10]}</td></tr>"
        for e in summary["executions"]
    )
    html = f"""<!DOCTYPE html><html lang="tr"><head><meta charset="UTF-8">
<title>Özet Rapor — {summary['project']}</title>
<style>body{{font-family:system-ui,sans-serif;margin:2rem}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:.5rem .8rem;border:1px solid #e5e7eb;text-align:left}}th{{background:#f9fafb}}
.pass{{color:#16a34a}}.fail{{color:#dc2626}}</style></head>
<body><h1>Özet Rapor: {summary['project']}</h1>
<p>Son {days} gün · {summary['total_executions']} koşu · {summary['passed']} başarılı · {summary['failed']} başarısız</p>
<table><thead><tr><th>Koşu</th><th>Durum</th><th>Tarih</th></tr></thead><tbody>{rows}</tbody></table>
</body></html>"""
    return StreamingResponse(
        io.BytesIO(html.encode("utf-8")),
        media_type="text/html",
        headers={"Content-Disposition": "attachment; filename=\"ozet-rapor.html\""},
    )


# ═══════════════════════════════════════════════════════════════════════
# n8n Workflow Yönetimi
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/workflows")
def list_workflows(project_id: str, db: DB, user: CurrentUser):
    """Projeye ait workflow kayitlarini listeler."""
    _get_project(db, project_id, user)
    rows = list(db.scalars(
        select(TspmN8nWorkflow).where(TspmN8nWorkflow.project_id == project_id)
        .order_by(TspmN8nWorkflow.created_at.desc())
    ))
    return [
        {
            "id": w.id, "name": w.name, "description": w.description,
            "n8n_workflow_id": w.n8n_workflow_id, "trigger_on": w.trigger_on,
            "is_active": w.is_active, "webhook_path": w.webhook_path,
            "last_triggered_at": w.last_triggered_at.isoformat() if w.last_triggered_at else None,
            "created_at": w.created_at.isoformat(),
        }
        for w in rows
    ]


@router.post("/projects/{project_id}/workflows", status_code=201)
def create_workflow(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Yeni workflow baglantisi olusturur."""
    _get_project(db, project_id, user)
    w = TspmN8nWorkflow(
        project_id=project_id,
        n8n_workflow_id=body.get("n8n_workflow_id", ""),
        name=body.get("name", "Yeni Workflow"),
        description=body.get("description", ""),
        trigger_on=body.get("trigger_on", "manual"),
        webhook_path=body.get("webhook_path"),
        is_active=body.get("is_active", True),
    )
    db.add(w)
    db.commit()
    db.refresh(w)
    return {"id": w.id, "name": w.name, "is_active": w.is_active, "created_at": w.created_at.isoformat()}


@router.put("/projects/{project_id}/workflows/{workflow_id}")
def update_workflow(project_id: str, workflow_id: str, body: dict, db: DB, user: CurrentUser):
    """Workflow bilgilerini gunceller."""
    _get_project(db, project_id, user)
    w = db.get(TspmN8nWorkflow, workflow_id)
    if not w or w.project_id != project_id:
        raise HTTPException(404, "Workflow bulunamadı")
    for field in ("name", "description", "trigger_on", "webhook_path", "is_active"):
        if field in body:
            setattr(w, field, body[field])
    db.commit()
    return {"id": w.id, "name": w.name, "is_active": w.is_active}


@router.delete("/projects/{project_id}/workflows/{workflow_id}", status_code=204)
def delete_workflow(project_id: str, workflow_id: str, db: DB, user: CurrentUser):
    """Workflow kaydini siler."""
    _get_project(db, project_id, user)
    w = db.get(TspmN8nWorkflow, workflow_id)
    if not w or w.project_id != project_id:
        raise HTTPException(404, "Workflow bulunamadı")
    db.delete(w)
    db.commit()


@router.post("/projects/{project_id}/workflows/{workflow_id}/trigger")
def trigger_workflow(project_id: str, workflow_id: str, body: dict, db: DB, user: CurrentUser):
    """Workflow calismasini tetikler."""
    from app.config import get_settings
    _get_project(db, project_id, user)
    w = db.get(TspmN8nWorkflow, workflow_id)
    if not w or w.project_id != project_id:
        raise HTTPException(404, "Workflow bulunamadı")

    settings = get_settings()
    execution = TspmN8nExecution(workflow_link_id=w.id, status="running", input_data=body)
    db.add(execution)

    try:
        target_url = w.webhook_path or f"{settings.n8n_base_url}/api/v1/workflows/{w.n8n_workflow_id}/execute"
        headers = {"X-N8N-API-KEY": settings.n8n_api_key} if settings.n8n_api_key else {}
        resp = httpx.post(target_url, json=body, headers=headers, timeout=30.0)
        n8n_data = resp.json() if resp.status_code < 300 else {}
        execution.status = "success"
        execution.output_data = n8n_data
        execution.n8n_execution_id = str(n8n_data.get("executionId", ""))
    except Exception as e:
        execution.status = "error"
        execution.error = str(e)

    from datetime import datetime, timezone
    execution.finished_at = datetime.now(timezone.utc)
    w.last_triggered_at = execution.finished_at
    db.commit()
    return {"status": execution.status, "execution_id": execution.id}


@router.get("/projects/{project_id}/workflows/{workflow_id}/executions")
def list_workflow_executions(project_id: str, workflow_id: str, db: DB, user: CurrentUser):
    """Workflow calisma gecmisini listeler."""
    _get_project(db, project_id, user)
    rows = list(db.scalars(
        select(TspmN8nExecution).where(TspmN8nExecution.workflow_link_id == workflow_id)
        .order_by(TspmN8nExecution.started_at.desc()).limit(50)
    ))
    return [
        {
            "id": e.id, "status": e.status, "error": e.error,
            "started_at": e.started_at.isoformat(),
            "finished_at": e.finished_at.isoformat() if e.finished_at else None,
        }
        for e in rows
    ]


# ═══════════════════════════════════════════════════════════════════════
# Locator Yönetimi (Engine proxy)
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/locators")
def list_locators(project_id: str, db: DB, user: CurrentUser):
    """Engine'deki locator'ları listeler ve project_id ile filtreler."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.get(f"{ENGINE_BASE_URL}/api/locators", headers=_IKEY, timeout=10.0)
        data = resp.json() if resp.status_code == 200 else []
        # Engine locator'larını proje ile etiketle
        return [dict(l, project_id=project_id) for l in (data if isinstance(data, list) else data.get("locators", []))]
    except Exception:
        return []


@router.post("/projects/{project_id}/locators", status_code=201)
def create_locator(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Yeni locator ekler."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(f"{ENGINE_BASE_URL}/api/locators", json=body, headers=_IKEY, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/projects/{project_id}/locators/{locator_id}", status_code=204)
def delete_locator(project_id: str, locator_id: str, db: DB, user: CurrentUser):
    """Locator siler."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.delete(f"{ENGINE_BASE_URL}/api/locators/{locator_id}", headers=_IKEY, timeout=10.0)
        if resp.status_code not in (200, 204, 404):
            raise HTTPException(500, "Engine silme hatası")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/projects/{project_id}/locators/health-check")
def locator_health_check(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Seçili locator'lar için sağlık kontrolü çalıştırır."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(f"{ENGINE_BASE_URL}/api/locators/health", json=body, headers=_IKEY, timeout=60.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/projects/{project_id}/locators/discover")
def locator_discover(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Verilen URL'den locator'ları otomatik keşfeder."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(f"{ENGINE_BASE_URL}/api/discover", json=body, headers=_IKEY, timeout=120.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════
# Görsel Regresyon (Engine proxy)
# ═══════════════════════════════════════════════════════════════════════

@router.get("/projects/{project_id}/visual/baselines")
def list_visual_baselines(project_id: str, db: DB, user: CurrentUser):
    """Projeye ait baseline listesini döndürür."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.get(f"{ENGINE_BASE_URL}/api/visual/baselines", headers=_IKEY, timeout=10.0)
        data = resp.json() if resp.status_code == 200 else []
        items = data if isinstance(data, list) else data.get("baselines", [])
        return [dict(b, project_id=project_id) for b in items]
    except Exception:
        return []


@router.post("/projects/{project_id}/visual/baselines", status_code=201)
async def upload_visual_baseline(project_id: str, request: Request, db: DB, user: CurrentUser):
    """Baseline screenshot yükler (multipart forward)."""
    _get_project(db, project_id, user)
    try:
        body = await request.body()
        headers = {k: v for k, v in request.headers.items() if k.lower() not in ("host", "content-length")}
        headers["X-Internal-Key"] = _ENGINE_KEY
        resp = httpx.post(f"{ENGINE_BASE_URL}/api/visual/upload-baseline", content=body, headers=headers, timeout=30.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/projects/{project_id}/visual/compare")
def visual_compare(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Mevcut sayfayı baseline ile karşılaştırır."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.post(f"{ENGINE_BASE_URL}/api/visual/compare", json=body, headers=_IKEY, timeout=60.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/projects/{project_id}/visual/baselines/{baseline_id}", status_code=204)
def delete_visual_baseline(project_id: str, baseline_id: str, db: DB, user: CurrentUser):
    """Baseline siler."""
    _get_project(db, project_id, user)
    try:
        resp = httpx.delete(f"{ENGINE_BASE_URL}/api/visual/baselines/{baseline_id}", headers=_IKEY, timeout=10.0)
        if resp.status_code not in (200, 204, 404):
            raise HTTPException(500, "Engine silme hatası")
    except Exception as e:
        raise HTTPException(500, str(e))


# ═══════════════════════════════════════════════════════════════════════
# Faz 3 — AI Test Case Generation & Bulk Review
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/test-cases/generate",
    response_model=GenerateTestCasesResponse,
    tags=["faz3-test-cases"],
)
def generate_test_cases(
    project_id: str,
    body: GenerateTestCasesRequest,
    db: DB,
    user: CurrentUser,
):
    """AI Gateway üzerinden toplu test case üretir, DB'ye kaydeder."""
    _get_project(db, project_id, user)
    try:
        return tc_svc.generate_test_cases_for_project(db, project_id, body)
    except RuntimeError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e))
    except Exception as e:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(e))


@router.get(
    "/projects/{project_id}/test-cases/batches",
    response_model=list[AiBatchOut],
    tags=["faz3-test-cases"],
)
def list_batches(project_id: str, db: DB, user: CurrentUser):
    """Projeye ait tüm AI üretim batch'lerini listeler."""
    _get_project(db, project_id, user)
    return tc_svc.list_batches(db, project_id)


@router.get(
    "/projects/{project_id}/test-cases/batches/{batch_id}",
    response_model=AiBatchDetailOut,
    tags=["faz3-test-cases"],
)
def get_batch(project_id: str, batch_id: str, db: DB, user: CurrentUser):
    """Batch detayı + içerdiği test case'ler."""
    _get_project(db, project_id, user)
    batch = tc_svc.get_batch(db, batch_id, project_id)
    if not batch:
        raise HTTPException(404, "Batch bulunamadı")
    test_cases = tc_svc.list_test_cases(db, project_id, batch_id=batch_id)
    return AiBatchDetailOut(
        batch=AiBatchOut.model_validate(batch),
        test_cases=[TestCaseOut.model_validate(tc) for tc in test_cases],
    )


@router.delete(
    "/projects/{project_id}/test-cases/batches/{batch_id}",
    status_code=204,
    tags=["faz3-test-cases"],
)
def delete_batch(project_id: str, batch_id: str, db: DB, user: CurrentUser):
    """Batch ve içindeki tüm test case'leri siler."""
    _get_project(db, project_id, user)
    batch = tc_svc.get_batch(db, batch_id, project_id)
    if not batch:
        raise HTTPException(404, "Batch bulunamadı")
    tc_svc.delete_batch(db, batch)


@router.get(
    "/projects/{project_id}/test-cases",
    response_model=list[TestCaseOut],
    tags=["faz3-test-cases"],
)
def list_test_cases(
    project_id: str,
    db: DB,
    user: CurrentUser,
    batch_id: Optional[str] = Query(None),
    review_status: Optional[str] = Query(None),
):
    """Test case listesi; batch_id ve/veya review_status ile filtrele."""
    _get_project(db, project_id, user)
    return [
        TestCaseOut.model_validate(tc)
        for tc in tc_svc.list_test_cases(db, project_id, batch_id=batch_id, review_status=review_status)
    ]


@router.get(
    "/projects/{project_id}/test-cases/{tc_id}",
    response_model=TestCaseOut,
    tags=["faz3-test-cases"],
)
def get_test_case(project_id: str, tc_id: str, db: DB, user: CurrentUser):
    """Tek test case detayı."""
    _get_project(db, project_id, user)
    tc = tc_svc.get_test_case(db, tc_id, project_id)
    if not tc:
        raise HTTPException(404, "Test case bulunamadı")
    return TestCaseOut.model_validate(tc)


@router.put(
    "/projects/{project_id}/test-cases/{tc_id}",
    response_model=TestCaseOut,
    tags=["faz3-test-cases"],
)
def update_test_case(
    project_id: str,
    tc_id: str,
    body: TestCaseUpdate,
    db: DB,
    user: CurrentUser,
):
    """Test case alanlarını günceller (edit)."""
    _get_project(db, project_id, user)
    tc = tc_svc.get_test_case(db, tc_id, project_id)
    if not tc:
        raise HTTPException(404, "Test case bulunamadı")
    updated = tc_svc.update_test_case(db, tc, body)
    return TestCaseOut.model_validate(updated)


@router.post(
    "/projects/{project_id}/test-cases/{tc_id}/review",
    response_model=TestCaseOut,
    tags=["faz3-test-cases"],
)
def review_test_case(
    project_id: str,
    tc_id: str,
    body: TestCaseReviewAction,
    db: DB,
    user: CurrentUser,
):
    """Tek test case onayla / reddet / düzenle-ve-onayla."""
    _get_project(db, project_id, user)
    tc = tc_svc.get_test_case(db, tc_id, project_id)
    if not tc:
        raise HTTPException(404, "Test case bulunamadı")
    updated = tc_svc.review_test_case(db, tc, body)
    return TestCaseOut.model_validate(updated)


@router.post(
    "/projects/{project_id}/test-cases/bulk-review",
    tags=["faz3-test-cases"],
)
def bulk_review_test_cases(
    project_id: str,
    body: BulkReviewRequest,
    db: DB,
    user: CurrentUser,
):
    """Toplu onayla / reddet. Seçilen ID'leri işler, sayıları döner."""
    _get_project(db, project_id, user)
    if body.action not in ("approve", "reject"):
        raise HTTPException(400, "action 'approve' veya 'reject' olmalı")
    return tc_svc.bulk_review(db, project_id, body)


@router.delete(
    "/projects/{project_id}/test-cases/{tc_id}",
    status_code=204,
    tags=["faz3-test-cases"],
)
def delete_test_case(project_id: str, tc_id: str, db: DB, user: CurrentUser):
    """Test case siler."""
    _get_project(db, project_id, user)
    tc = tc_svc.get_test_case(db, tc_id, project_id)
    if not tc:
        raise HTTPException(404, "Test case bulunamadı")
    tc_svc.delete_test_case(db, tc)


# ═══════════════════════════════════════════════════════════════════════
# Faz 5 — Automation Code Generation (Gherkin + Java + Playwright)
# ═══════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/automation/generate",
    response_model=GenerateAutomationResponse,
    status_code=200,
    tags=["faz5-automation"],
)
def generate_automation_code(
    project_id: str,
    body: GenerateAutomationRequest,
    db: DB,
    user: CurrentUser,
):
    """
    Onaylı test case'lerden Gherkin + Java NexusQA + Playwright TS kodu üretir.

    Kaynak önceliği:
      1. body.test_case_ids liste verilmişse → bunları kullan
      2. body.batch_id verilmişse → o batch'in approved test case'lerini kullan
      3. İkisi de yoksa → projenin tüm approved test case'leri
    """
    _get_project(db, project_id, user)

    # Resolve which test cases to use
    if body.test_case_ids:
        raw_cases = db.query(TspmTestCase).filter(
            TspmTestCase.project_id == project_id,
            TspmTestCase.id.in_(body.test_case_ids),
        ).all()
    elif body.batch_id:
        raw_cases = db.query(TspmTestCase).filter(
            TspmTestCase.project_id == project_id,
            TspmTestCase.batch_id == body.batch_id,
            TspmTestCase.review_status == "approved",
        ).all()
    else:
        raw_cases = db.query(TspmTestCase).filter(
            TspmTestCase.project_id == project_id,
            TspmTestCase.review_status == "approved",
        ).limit(20).all()

    if not raw_cases:
        raise HTTPException(400, "Kullanılabilir onaylı test case bulunamadı")

    # Convert to dicts for the service
    tc_dicts = [
        {
            "id": tc.id,
            "title": tc.title,
            "description": tc.description or "",
            "module_name": tc.module_name,
            "test_type": tc.test_type,
            "priority": tc.priority,
            "risk_level": tc.risk_level,
            "preconditions": tc.preconditions or [],
            "steps": tc.steps or [],
            "expected_result": tc.expected_result or "",
            "tags": tc.tags or [],
        }
        for tc in raw_cases
    ]

    try:
        result = auto_gen.generate_full_automation_package(
            test_cases=tc_dicts,
            feature_name=body.feature_name,
            include_java=body.include_java,
            include_playwright=body.include_playwright,
            project_id=project_id,
        )
    except RuntimeError as e:
        raise HTTPException(503, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))

    # Map to response model
    gherkin = None
    if result.get("gherkin"):
        g = result["gherkin"]
        gherkin = GherkinResult(
            gherkin=g["gherkin"],
            feature_name=g["feature_name"],
            scenario_count=g["scenario_count"],
            filename=g["filename"],
        )

    java = None
    if result.get("java"):
        j = result["java"]
        java = JavaResult(
            java_code=j["java_code"],
            class_name=j["class_name"],
            filename=j["filename"],
            method_count=j["method_count"],
        )

    playwright = None
    if result.get("playwright"):
        p = result["playwright"]
        playwright = PlaywrightResult(
            ts_code=p["ts_code"],
            filename=p["filename"],
            test_count=p["test_count"],
        )

    tc_count = len(raw_cases)
    errors = result.get("errors", [])
    artifacts: list[AutomationArtifactOut] = []
    try:
        artifacts = _persist_generated_automation_artifacts(
            db=db,
            project_id=project_id,
            feature_name=body.feature_name,
            batch_id=body.batch_id,
            test_case_count=tc_count,
            result=result,
        )
    except Exception as e:
        db.rollback()
        errors.append(f"Artifacts: {e}")

    msg_parts = [f"{tc_count} test case'den"]
    if gherkin:
        msg_parts.append(f"{gherkin.scenario_count} Gherkin senaryo")
    if java:
        msg_parts.append(f"{java.method_count} Java step")
    if playwright:
        msg_parts.append(f"{playwright.test_count} Playwright test")
    if artifacts:
        msg_parts.append(f"{len(artifacts)} artifact")
    message = " + ".join(msg_parts) + " üretildi."

    return GenerateAutomationResponse(
        feature_name=body.feature_name,
        test_case_count=tc_count,
        gherkin=gherkin,
        java=java,
        playwright=playwright,
        artifacts=artifacts,
        errors=errors,
        message=message,
    )


@router.get(
    "/projects/{project_id}/automation/artifacts/{artifact_id}/download",
    tags=["faz5-automation"],
)
def download_automation_artifact(
    project_id: str,
    artifact_id: str,
    db: DB,
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
    token: Optional[str] = Query(None),
):
    """Uretilen otomasyon artifact dosyasini indirir."""
    resolved_user = user or _resolve_query_token_user(db, token)
    if resolved_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kimlik doğrulama gerekli")

    _get_project(db, project_id, resolved_user)
    artifact = db.scalar(
        select(TspmAutomationArtifact).where(
            TspmAutomationArtifact.id == artifact_id,
            TspmAutomationArtifact.project_id == project_id,
        )
    )
    if artifact is None:
        raise HTTPException(404, "Artifact bulunamadı")

    return FileResponse(
        artifact.storage_path,
        media_type=artifact.mime_type,
        filename=artifact.filename,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FAZ 6: AI Debug Loop + Allure Reporting
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/executions/{execution_id}/debug",
    response_model=DebugAnalysisResponse,
    status_code=200,
    summary="Faz 6: AI Debug Loop — başarısız testleri analiz et + Allure JSON üret",
)
def run_ai_debug_loop(
    project_id: str,
    execution_id: str,
    body: RunDebugRequest,
    db: DB,
    user: CurrentUser,
):
    """
    Bir execution'ın başarısız testlerini AI ile analiz et.
    - Varsa body.results kullan, yoksa DB'den oku
    - AI Gateway ile kök neden analizi + fix önerileri üret
    - Allure-uyumlu JSON çıktısı oluştur
    """
    # 1. Resolve execution results
    if body.results:
        results = body.results
    else:
        # Read from DB
        exec_obj = db.scalar(
            select(TspmExecution).where(
                TspmExecution.id == execution_id,
                TspmExecution.project_id == project_id,
            )
        )
        if exec_obj is None:
            raise HTTPException(404, f"Execution {execution_id} bulunamadı")

        db_results = list(db.scalars(
            select(TspmExecutionResult).where(TspmExecutionResult.execution_id == execution_id)
        ))

        results = []
        for er in db_results:
            sc = db.scalar(select(TspmScenario).where(TspmScenario.id == er.scenario_id))
            results.append({
                "test_id": er.id,
                "scenario_id": er.scenario_id,
                "title": sc.title if sc else "Unknown",
                "module": sc.tags[0] if sc and sc.tags else "default",
                "status": er.status,
                "severity": "medium",
                "error_message": er.note or "",
                "error_type": "",
                "steps": sc.steps if sc else [],
                "tags": sc.tags or [] if sc else [],
            })

    # 2. Run debug loop
    try:
        loop_result = debug_svc.run_debug_loop(
            execution_id=execution_id,
            project_id=project_id,
            results=results,
            generate_allure=body.generate_allure,
        )
    except Exception as e:
        raise HTTPException(500, str(e))

    da = loop_result["debug_analysis"]
    analyses = [
        DebugAnalysisItem(**a) for a in da.get("analyses", [])
    ]

    return DebugAnalysisResponse(
        execution_id=execution_id,
        project_id=project_id,
        analyses=analyses,
        overall_health=da.get("overall_health", "unknown"),
        key_patterns=da.get("key_patterns", []),
        recommended_actions=da.get("recommended_actions", []),
        ai_provider=da.get("ai_provider", "unknown"),
        fallback_used=da.get("fallback_used", False),
        summary=loop_result["summary"],
        generated_at=loop_result["generated_at"],
        allure_results=loop_result.get("allure_results", []),
    )


@router.get(
    "/projects/{project_id}/executions/{execution_id}/allure",
    response_model=AllureExportResponse,
    summary="Faz 6: Execution için Allure export verisi",
)
def export_allure(
    project_id: str,
    execution_id: str,
    db: DB,
    user: CurrentUser,
):
    """
    Bir execution'ın Allure-uyumlu JSON export verilerini döndür.
    Frontend bu veriyi .zip olarak indirip allure-results/ klasörüne koyabilir.
    """
    exec_obj = db.scalar(
        select(TspmExecution).where(
            TspmExecution.id == execution_id,
            TspmExecution.project_id == project_id,
        )
    )
    if exec_obj is None:
        raise HTTPException(404, f"Execution {execution_id} bulunamadı")

    project = db.scalar(select(TspmProject).where(TspmProject.id == project_id))
    project_name = project.name if project else project_id

    db_results = list(db.scalars(
        select(TspmExecutionResult).where(TspmExecutionResult.execution_id == execution_id)
    ))

    results = []
    for er in db_results:
        sc = db.scalar(select(TspmScenario).where(TspmScenario.id == er.scenario_id))
        results.append({
            "test_id": er.id,
            "scenario_id": er.scenario_id,
            "title": sc.title if sc else "Unknown",
            "module": sc.tags[0] if sc and sc.tags else "default",
            "status": er.status,
            "severity": "medium",
            "error_message": er.note or "",
            "tags": sc.tags or [] if sc else [],
            "steps": sc.steps if sc else [],
        })

    allure_results = debug_svc.build_allure_results(execution_id, results)
    environment = debug_svc.build_allure_environment(
        project_name=project_name,
        base_url="",
    )
    executor = debug_svc.build_allure_executor(
        execution_id=execution_id,
        execution_name=exec_obj.name or f"Execution {execution_id[:8]}",
        project_id=project_id,
    )

    return AllureExportResponse(
        execution_id=execution_id,
        file_count=len(allure_results),
        environment_properties=environment,
        executor_json=executor,
        allure_results=allure_results,
    )


# ══════════════════════════════════════════════════════════════════════════════
# FAZ 7: AI Chat Assistant
# ══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/chat",
    response_model=ChatResponse,
    status_code=200,
    summary="Faz 7: Nexus QA AI Chat Asistanı",
)
def nexus_chat(
    project_id: str,
    body: ChatRequest,
    db: DB,
    user: CurrentUser,
):
    """
    Proje bağlamında çalışan AI chat asistanı.
    - Kullanıcı mesajına intent tespiti yapar
    - AI Gateway üzerinden yanıt üretir
    - Konuşma geçmişini destekler
    - Fallback: kural tabanlı canned responses
    """
    # Enrich context from DB if not provided
    project_context = body.project_context or {}
    if not project_context.get("project_name"):
        project = db.scalar(select(TspmProject).where(TspmProject.id == project_id))
        if project:
            project_context["project_name"] = project.name
            # Count scenarios
            sc_count = db.scalar(
                select(func.count(TspmScenario.id)).where(TspmScenario.project_id == project_id)
            )
            project_context["scenario_count"] = sc_count or 0
            # Latest pass rate
            latest_metrics = db.scalar(
                select(TspmExecutionMetrics)
                .where(TspmExecutionMetrics.project_id == project_id)
                .order_by(TspmExecutionMetrics.executed_at.desc())
            )
            if latest_metrics:
                project_context["last_pass_rate"] = latest_metrics.pass_rate

    # Convert ChatMessage list to dicts for the service
    history_dicts = [{"role": m.role, "content": m.content} for m in body.history]
    retrieval_context = build_project_ai_context(db, project_id, body.message)

    try:
        result = chat_svc.chat_with_ai(
            user_message=body.message,
            project_id=project_id,
            project_context=project_context,
            conversation_history=history_dicts,
            session_id=body.session_id,
            retrieval_context=retrieval_context,
        )
    except Exception as e:
        raise HTTPException(500, str(e))

    return ChatResponse(
        response=result["response"],
        intent=result.get("intent", "general"),
        ai_provider=result.get("ai_provider", "unknown"),
        fallback_used=result.get("fallback_used", False),
        session_id=result.get("session_id", ""),
        timestamp=result.get("timestamp"),
    )


@router.get(
    "/projects/{project_id}/chat/quick-actions",
    response_model=list[QuickAction],
    summary="Faz 7: Chat hızlı eylem listesi",
)
def get_chat_quick_actions(
    project_id: str,
    user: CurrentUser,
):
    """AI Chat sayfasında gösterilecek hızlı eylem listesi."""
    return [QuickAction(**a) for a in chat_svc.QUICK_ACTIONS]


# ══════════════════════════════════════════════════════════════════════════════
# FAZ 8: Real Test Execution Engine
# ══════════════════════════════════════════════════════════════════════════════

from app.domains.tspm.schemas import (
    RunExecutionRequest, RunExecutionResponse,
    ExecutionMetricsOut,
)


@router.post(
    "/projects/{project_id}/executions/{execution_id}/run",
    response_model=RunExecutionResponse,
    status_code=202,
    summary="Faz 8: Gerçek test koşumunu başlat (async, SSE stream ile)",
)
def start_execution_run(
    project_id: str,
    execution_id: str,
    body: RunExecutionRequest,
    db: DB,
    user: CurrentUser,
):
    """
    Bir execution'ı gerçek Playwright headless modunda koştur.
    - Engine (port 5001) üzerinden pytest/playwright runner çalışır
    - Engine yoksa simülasyon modu devreye girer
    - SSE stream URL döner → frontend canlı olayları dinler
    """
    exec_obj = db.scalar(
        select(TspmExecution).where(
            TspmExecution.id == execution_id,
            TspmExecution.project_id == project_id,
        )
    )
    if exec_obj is None:
        raise HTTPException(404, f"Execution {execution_id} bulunamadı")

    if exec_obj.status == "running":
        raise HTTPException(409, "Bu execution zaten çalışıyor")

    # Arka planda runner'ı başlat
    run_id = runner_svc.launch_execution_run(
        execution_id=execution_id,
        project_id=project_id,
        browser=body.browser,
        tags=body.tags,
        base_url=body.base_url,
    )

    stream_url = f"/api/v1/tspm/projects/{project_id}/executions/{execution_id}/stream/{run_id}"

    return RunExecutionResponse(
        execution_id=execution_id,
        run_id=run_id,
        status="started",
        stream_url=stream_url,
    )


@router.get(
    "/projects/{project_id}/executions/{execution_id}/stream/{run_id}",
    summary="Faz 8: SSE canlı test akışı",
    response_class=StreamingResponse,
)
def stream_execution(
    project_id: str,
    execution_id: str,
    run_id: str,
    db: DB,
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
    token: Optional[str] = Query(None),
):
    """
    SSE (Server-Sent Events) stream — test çıktısını canlı akıt.
    EventSource ile bağlanın:
      new EventSource('/api/v1/tspm/projects/{pid}/executions/{eid}/stream/{rid}')
    """
    resolved_user = user or _resolve_query_token_user(db, token)
    if resolved_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kimlik doğrulama gerekli")

    _get_project(db, project_id, resolved_user)  # auth guard

    return StreamingResponse(
        runner_svc.get_run_stream(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get(
    "/projects/{project_id}/executions/{execution_id}/metrics",
    response_model=ExecutionMetricsOut,
    summary="Faz 8: Execution metriklerini getir",
)
def get_execution_metrics(
    project_id: str,
    execution_id: str,
    db: DB,
    user: CurrentUser,
):
    """Tamamlanmış bir execution'ın pass/fail/skip metriklerini döndürür."""
    _get_project(db, project_id, user)
    execution = db.scalar(
        select(TspmExecution).where(
            TspmExecution.id == execution_id,
            TspmExecution.project_id == project_id,
        )
    )
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşum bulunamadı")

    metrics = db.scalar(
        select(TspmExecutionMetrics).where(
            TspmExecutionMetrics.execution_id == execution_id,
            TspmExecutionMetrics.project_id == project_id,
        )
    )
    if metrics is None:
        # Anlık hesapla
        results = list(db.scalars(
            select(TspmExecutionResult).where(
                TspmExecutionResult.execution_id == execution_id
            )
        ))
        total = len(results)
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status in ("skipped", "not_run"))
        return ExecutionMetricsOut(
            execution_id=execution_id,
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            pass_rate=(passed / total * 100) if total > 0 else 0.0,
        )

    return ExecutionMetricsOut(
        execution_id=execution_id,
        total=metrics.total,
        passed=metrics.passed,
        failed=metrics.failed,
        skipped=metrics.skipped,
        pass_rate=metrics.pass_rate,
        duration_seconds=metrics.duration_seconds,
        executed_at=metrics.executed_at,
    )


@router.get(
    "/projects/{project_id}/executions/{execution_id}/run-status/{run_id}",
    summary="Faz 8: Aktif run durumu",
)
def get_run_status(
    project_id: str,
    execution_id: str,
    run_id: str,
    db: DB,
    user: CurrentUser,
):
    """SSE stream'inin hâlâ aktif olup olmadığını sorgula."""
    _get_project(db, project_id, user)
    execution = db.scalar(
        select(TspmExecution).where(
            TspmExecution.id == execution_id,
            TspmExecution.project_id == project_id,
        )
    )
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşum bulunamadı")
    return runner_svc.get_run_status(run_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Visium Farm — Mobil Koşum Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/mobile-run",
    response_model=MobileRunOut,
    summary="Visium Farm: Paralel mobil cihaz koşumu başlat",
    status_code=202,
)
def start_mobile_run(
    project_id: str,
    body: MobileRunCreate,
    db: DB,
    user: CurrentUser,
):
    """
    Seçili cihazlarda paralel Playwright mobil emülasyon testi başlatır.
    Her cihaz için TspmExecution kaydı oluşturulur.
    SSE stream_url'i ile canlı izlenebilir.
    """
    _get_project(db, project_id, user)

    result = runner_svc.launch_mobile_run(
        project_id=project_id,
        device_names=body.device_names,
        scenario_ids=body.scenario_ids or None,
        browser=body.browser,
        tags=body.tags,
        base_url=body.base_url,
        app_upload_id=body.app_upload_id,
    )

    return MobileRunOut(**result)


@router.get(
    "/projects/{project_id}/mobile-run/{run_id}/stream",
    summary="Visium Farm: SSE canlı mobil test akışı",
    response_class=StreamingResponse,
)
def stream_mobile_run(
    project_id: str,
    run_id: str,
    db: DB,
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
    token: Optional[str] = Query(None),
):
    """
    Paralel mobil koşum SSE stream.
    Her olay device_name alanı taşır.
    EventSource ile bağlanın: ...?token=<jwt>
    """
    resolved_user = user or _resolve_query_token_user(db, token)
    if resolved_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kimlik doğrulama gerekli")

    _get_project(db, project_id, resolved_user)

    return StreamingResponse(
        runner_svc.get_mobile_run_stream(run_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
