"""TSPM router — projects, scenarios, executions, flows, regression, approvals, imports,
requirements, versions, schedules, test-data, integrations, api-testing, members,
faz3: ai test case generation + bulk review."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import ipaddress
import re
import socket
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Annotated, Optional

from pydantic import BaseModel as _PydanticBase
from urllib.parse import urlparse

import httpx
import jwt
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
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
    ProjectUpdate,
    ProjectMemberCreate,
    ProjectMemberOut,
    ProjectOut,
    RecentProjectSummary,
    RegressionSetCreate,
    RegressionSetDetailOut,
    RegressionSetOut,
    RegressionSuggestRequest,
    RegressionSuggestResponse,
    RequirementCreate,
    RequirementOut,
    RequirementUpdate,
    ExecutionStatusUpdate,
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
    # Geçersiz UUID formatinda 500 (DataError) yerine 404 don — bilgi sizintisini onler.
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
    provenance = _resolve_provenance(result)

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
            target=_resolve_artifact_target(artifact_type),
            provenance=provenance,
            validation_status=_validate_generated_artifact(artifact_type, content),
            generated_by=_resolve_generated_by(payload, result),
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
                target=artifact.target,
                provenance=artifact.provenance,
                validation_status=artifact.validation_status,
                generated_by=artifact.generated_by,
                filename=artifact.filename,
                download_url=f"/api/v1/tspm/projects/{project_id}/automation/artifacts/{artifact.id}/download",
                size_bytes=artifact.size_bytes,
                created_at=artifact.created_at,
            )
        )

    db.commit()
    return persisted


def _resolve_artifact_target(artifact_type: str) -> str:
    if artifact_type == "playwright":
        return "playwright"
    if artifact_type == "java":
        return "maviyaka"
    return "shared"


def _resolve_provenance(result: dict) -> str:
    if bool(result.get("stub")):
        return "stub"
    if bool(result.get("fallback")):
        return "fallback"
    if bool(result.get("simulated")) or bool(result.get("mock_mode")):
        return "simulated"
    return "real"


def _resolve_generated_by(payload: dict, result: dict) -> str:
    provider = payload.get("generated_by") or result.get("generated_by") or result.get("ai_provider")
    return str(provider or "ai_gateway")


def _validate_generated_artifact(artifact_type: str, content: str) -> str:
    text = content.strip()
    if not text:
        return "failed"

    if artifact_type == "gherkin":
        has_feature = re.search(r"^\s*(Feature|Özellik)\s*:", text, re.MULTILINE)
        has_scenario = re.search(r"^\s*(Scenario|Senaryo)\s*:", text, re.MULTILINE)
        return "validated" if has_feature and has_scenario else "failed"

    if artifact_type == "java":
        has_class = re.search(r"\bclass\s+\w+", text)
        has_steps = re.search(r"@(?:Given|When|Then|And)\s*\(", text)
        return "validated" if has_class and has_steps else "failed"

    if artifact_type == "playwright":
        has_import = "@playwright/test" in text
        has_tests = re.search(r"\btest\s*\(", text)
        return "validated" if has_import and has_tests else "failed"

    return "pending"


def _extract_postman_items(items: list[dict], folder_stack: list[str] | None = None) -> list[tuple[list[str], dict]]:
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
def list_projects(
    db: DB,
    user: CurrentUser,
    include_archived: bool = Query(True, description="Arşivli projeleri de listeye dahil et."),
    sort: str = Query(
        "created_at",
        pattern="^(created_at|last_opened_at|name)$",
        description="Sıralama anahtarı; ana sayfa 'last_opened_at' kullanır.",
    ),
):
    # Admin kullanıcılar tüm projeleri görebilir
    user_perms = {rp.permission for role in user.roles for rp in role.permissions}
    if Permission.ADMIN_FULL in user_perms:
        stmt = select(TspmProject)
    else:
        stmt = (
            select(TspmProject)
            .join(TspmProjectMember, TspmProjectMember.project_id == TspmProject.id)
            .where(TspmProjectMember.user_id == user.id)
        )

    if not include_archived:
        stmt = stmt.where(TspmProject.archived == False)  # noqa: E712

    if sort == "last_opened_at":
        # NULLS LAST — hiç açılmamış projeler listenin sonunda kalsın.
        stmt = stmt.order_by(TspmProject.last_opened_at.desc().nullslast(), TspmProject.created_at.desc())
    elif sort == "name":
        stmt = stmt.order_by(TspmProject.name.asc())
    else:
        stmt = stmt.order_by(TspmProject.created_at.desc())

    return list(db.scalars(stmt))


@router.post("/projects/{project_id}/touch", response_model=ProjectOut)
def touch_project(project_id: str, db: DB, user: CurrentUser):
    """Ana sayfa 'Son Açılan Proje' kartı için: son açılış zamanını işaretler.

    Frontend dashboard layout'u URL'den projectId çıktığında idempotent olarak
    bu ucu çağırır. İsteğin kendisi izin gerektirmez — sadece üyelik.
    """
    project = _get_project(db, project_id, user)
    project.last_opened_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    return project


@router.get(
    "/projects/recent",
    response_model=Optional[RecentProjectSummary],
    summary="Ana sayfa 'Son Açılan Proje' kartı için zengin özet",
)
def get_recent_project(db: DB, user: CurrentUser):
    """En son açılmış projeyi + son koşum özetini tek çağrıda döner.

    Sıralama önceliği:
      1. ``last_opened_at`` DESC (NULL en altta)
      2. ``created_at`` DESC

    Arşivli projeler atlanır. Kullanıcı hiç projeye üye değilse ``None``.
    """
    user_perms = {rp.permission for role in user.roles for rp in role.permissions}
    base = select(TspmProject).where(TspmProject.archived == False)  # noqa: E712
    if Permission.ADMIN_FULL not in user_perms:
        base = base.join(
            TspmProjectMember, TspmProjectMember.project_id == TspmProject.id
        ).where(TspmProjectMember.user_id == user.id)

    project = db.scalar(
        base.order_by(
            TspmProject.last_opened_at.desc().nullslast(),
            TspmProject.created_at.desc(),
        )
    )
    if project is None:
        return None

    # Son koşum özeti — tek query, minimum alan.
    last_exec = db.scalar(
        select(TspmExecution)
        .where(TspmExecution.project_id == project.id)
        .order_by(TspmExecution.created_at.desc())
    )
    if last_exec is None:
        return RecentProjectSummary(project=project)

    results = list(db.scalars(
        select(TspmExecutionResult).where(TspmExecutionResult.execution_id == last_exec.id)
    ))
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")

    return RecentProjectSummary(
        project=project,
        last_run_id=last_exec.id,
        last_run_status=last_exec.status,
        last_run_created_at=last_exec.created_at,
        last_run_passed=passed,
        last_run_failed=failed,
        last_run_total=len(results),
        last_run_simulated=bool(getattr(last_exec, "simulated", False)),
    )


@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=201,
    responses={
        201: {
            "content": {
                "application/json": {
                    "example": {
                        "id": "proj_01h2x3y4z5",
                        "name": "Örnek Proje",
                        "description": "Yeni oluşturulan proje",
                        "archived": False,
                        "base_url": "",
                        "primary_product_id": "default",
                        "product_tags": [],
                        "default_entry_key": None,
                        "last_opened_at": None,
                    }
                }
            }
        }
    },
)
def create_project(
    body: ProjectCreate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.PROJECT_CREATE))],
):
    """Yeni proje olusturur."""
    from app.domains.billing.gating import enforce_capacity
    enforce_capacity(db, user.tenant_id, "project_count")
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
    project.primary_product_id = body.primary_product_id
    project.product_tags = body.product_tags
    project.default_entry_key = body.resolved_default_entry_key()
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
    """Platform genelinde özet istatistikler."""
    # Admin tüm projeleri görür; diğerleri yalnızca üyesi oldukları projeleri
    user_perms = {rp.permission for role in user.roles for rp in role.permissions}
    is_admin = Permission.ADMIN_FULL in user_perms
    if is_admin:
        accessible_project_ids = None  # None = tüm projeler
    else:
        accessible_project_ids = list(db.scalars(
            select(TspmProjectMember.project_id).where(TspmProjectMember.user_id == user.id)
        ))

    def _project_filter(col):
        """Eğer admin değilse project_id IN (...) filtresi ekler."""
        if accessible_project_ids is None:
            return []
        return [col.in_(accessible_project_ids)]

    total_projects = db.scalar(
        select(func.count()).select_from(TspmProject)
        .where(*_project_filter(TspmProject.id))
    ) or 0
    total_scenarios = db.scalar(
        select(func.count()).select_from(TspmScenario)
        .where(*_project_filter(TspmScenario.project_id))
    ) or 0
    active_execs = db.scalar(
        select(func.count()).where(
            TspmExecution.status == "running",
            *_project_filter(TspmExecution.project_id),
        )
    ) or 0
    pending_approvals = db.scalar(
        select(func.count()).where(
            TspmApproval.status == "pending",
            *_project_filter(TspmApproval.project_id),
        )
    ) or 0

    # ── Overall pass rate — tek sorgu ───────────────────────────────────
    all_metrics = list(db.scalars(
        select(TspmExecutionMetrics)
        .where(*_project_filter(TspmExecutionMetrics.project_id))
        .order_by(TspmExecutionMetrics.executed_at.desc())
        .limit(100)
    ))
    overall_rate = round(sum(m.pass_rate for m in all_metrics) / len(all_metrics), 1) if all_metrics else 0.0

    day_names = ["Pzt", "Sal", "Çar", "Per", "Cum", "Cmt", "Paz"]
    now = datetime.now(timezone.utc)

    # ── Haftalık trend — 7 ayrı sorgu YERİNE tek sorgu ──────────────────
    week_start = (now - timedelta(days=6)).replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_metrics = list(db.scalars(
        select(TspmExecutionMetrics)
        .where(
            TspmExecutionMetrics.executed_at >= week_start,
            *_project_filter(TspmExecutionMetrics.project_id),
        )
    ))
    # Python'da gün bazında toplama
    day_buckets: dict[int, tuple[int, int]] = {d: (0, 0) for d in range(7)}
    for m in weekly_metrics:
        ts = m.executed_at.replace(tzinfo=timezone.utc) if m.executed_at.tzinfo is None else m.executed_at
        days_ago = (now.date() - ts.date()).days
        if 0 <= days_ago <= 6:
            slot = 6 - days_ago
            r, p = day_buckets[slot]
            day_buckets[slot] = (r + m.total, p + m.passed)
    weekly: list[WeeklyTrendPoint] = []
    for i in range(7):
        day = now - timedelta(days=6 - i)
        runs, passed_w = day_buckets[i]
        weekly.append(WeeklyTrendPoint(day=day_names[day.weekday()], runs=runs, passed=passed_w))

    # ── Top 5 proje — 3 toplu sorgu (N+1'in önüne geç) ──────────────────
    top_projects_stmt = (
        select(TspmProject)
        .where(*_project_filter(TspmProject.id))
        .order_by(TspmProject.created_at.desc())
        .limit(5)
    )
    top_projects = list(db.scalars(top_projects_stmt))
    top_project_ids = [p.id for p in top_projects]

    # Senaryo sayıları — tek GROUP BY sorgusu
    sc_rows = db.execute(
        select(TspmScenario.project_id, func.count().label("cnt"))
        .where(TspmScenario.project_id.in_(top_project_ids))
        .group_by(TspmScenario.project_id)
    ).all()
    sc_by_project: dict[str, int] = {row.project_id: row.cnt for row in sc_rows}

    # Son çalışma zamanı — proje başına MAX(created_at) tek sorgu
    latest_exec_subq = (
        select(
            TspmExecution.project_id,
            func.max(TspmExecution.created_at).label("max_ts"),
        )
        .where(TspmExecution.project_id.in_(top_project_ids))
        .group_by(TspmExecution.project_id)
        .subquery()
    )
    latest_execs = list(db.scalars(
        select(TspmExecution).join(
            latest_exec_subq,
            (TspmExecution.project_id == latest_exec_subq.c.project_id)
            & (TspmExecution.created_at == latest_exec_subq.c.max_ts),
        )
    ))
    latest_exec_by_project: dict[str, TspmExecution] = {e.project_id: e for e in latest_execs}

    # Execution result istatistikleri — tek GROUP BY sorgusu
    exec_ids = [e.id for e in latest_execs]
    if exec_ids:
        from sqlalchemy import case as sa_case
        result_stats_rows = db.execute(
            select(
                TspmExecutionResult.execution_id,
                func.count().label("total"),
                func.sum(sa_case((TspmExecutionResult.status == "passed", 1), else_=0)).label("passed"),
            )
            .where(TspmExecutionResult.execution_id.in_(exec_ids))
            .group_by(TspmExecutionResult.execution_id)
        ).all()
        result_stats: dict[str, tuple[int, int]] = {
            row.execution_id: (row.total, row.passed) for row in result_stats_rows
        }
    else:
        result_stats = {}

    def _time_ago(dt: datetime) -> str:
        diff = now - (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt)
        if diff.days > 0:
            return f"{diff.days} gün önce"
        if diff.seconds > 3600:
            return f"{diff.seconds // 3600} saat önce"
        return f"{diff.seconds // 60} dk önce"

    projects_rows: list[GlobalDashboardProjectRow] = []
    for p in top_projects:
        sc_count = sc_by_project.get(p.id, 0)
        last_exec = latest_exec_by_project.get(p.id)
        pr = None
        last_run_str = None
        p_status = "active"
        if last_exec:
            total_r, passed_r = result_stats.get(last_exec.id, (0, 0))
            pr = round(passed_r / total_r * 100, 1) if total_r > 0 else None
            if pr is not None:
                p_status = "critical" if pr < 70 else ("warning" if pr < 85 else "active")
            last_run_str = _time_ago(last_exec.created_at)
        projects_rows.append(GlobalDashboardProjectRow(
            id=p.id, name=p.name, scenario_count=sc_count,
            last_run=last_run_str, pass_rate=pr, status=p_status,
        ))

    # ── Audit olayları — kullanıcı adlarını tek sorguda yükle ────────────
    audit_events = list(db.scalars(
        select(AuditEvent).order_by(AuditEvent.ts.desc()).limit(10)
    ))
    actor_ids = list({evt.actor_user_id for evt in audit_events if evt.actor_user_id})
    actor_map: dict[str, str] = {}
    if actor_ids:
        actor_rows = list(db.scalars(select(User).where(User.id.in_(actor_ids))))
        actor_map = {u.id: (u.full_name or u.email) for u in actor_rows}

    activities: list[GlobalDashboardActivity] = []
    for evt in audit_events:
        actor_name = actor_map.get(evt.actor_user_id, "Sistem") if evt.actor_user_id else "Sistem"
        activities.append(GlobalDashboardActivity(
            actor=actor_name, action=evt.action, time=_time_ago(evt.ts),
            resource_type=evt.resource_type, resource_id=evt.resource_id,
        ))

    return GlobalDashboardOut(
        total_projects=total_projects,
        total_scenarios=total_scenarios,
        active_executions=active_execs,
        overall_pass_rate=overall_rate,
        pending_approvals=pending_approvals,
        weekly_trend=weekly,
        projects=projects_rows,
        activities=activities,
    )


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
    from app.domains.billing.gating import enforce_capacity
    _get_project(db, project_id, user)
    enforce_capacity(db, user.tenant_id, "scenario_count")
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


# ═══════════════════════════════════════════════════════════════════════
# LLM-as-Judge kalite skoru + semantik benzerlik (scenario_quality_llm_0001)
# ═══════════════════════════════════════════════════════════════════════


def _refresh_scenario_quality(db: Session, scenario: TspmScenario) -> dict[str, Any]:
    """Senaryo için skor + embedding'i üretir ve kaydeder.

    Hata durumlarında senaryoyu hiç yazmadan geri döner; çağrıyı yapanın
    commit hattı kesilmez. Döndürdüğü dict; API cevabına dönüştürülür.
    """
    from app.domains.ai.scenario_quality import (
        score_scenario_with_llm,
        embed_scenario,
        now_utc,
    )

    result = score_scenario_with_llm(scenario.title, scenario.description, scenario.steps)
    scenario.quality_score = int(result.get("score", 0))
    scenario.quality_issues = result.get("issues", [])
    scenario.quality_summary = result.get("summary", "")
    scenario.quality_scored_at = now_utc()

    # Embedding — Ollama yoksa None kalır
    try:
        emb = embed_scenario(scenario.title, scenario.description, scenario.steps)
    except Exception:
        emb = None
    if emb:
        scenario.title_embedding = emb
    db.add(scenario)
    return result


@router.post("/projects/{project_id}/scenarios/{scenario_id}/score")
def score_scenario_endpoint(
    project_id: str, scenario_id: str, db: DB, user: CurrentUser,
):
    """Tek bir senaryoyu LLM-as-Judge ile yeniden skorla ve embedding üret."""
    s = db.get(TspmScenario, scenario_id)
    if s is None or s.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Senaryo bulunamadı")
    result = _refresh_scenario_quality(db, s)
    db.commit()
    db.refresh(s)
    return {
        "scenario_id": s.id,
        "quality_score": s.quality_score,
        "quality_issues": s.quality_issues or [],
        "quality_summary": s.quality_summary or "",
        "quality_scored_at": s.quality_scored_at.isoformat() if s.quality_scored_at else None,
        "embedding_generated": bool(s.title_embedding),
        "source": result.get("source", "unknown"),
        "sub_scores": result.get("sub_scores", {}),
    }


@router.get("/projects/{project_id}/scenarios/{scenario_id}/similar")
def find_similar_scenarios_endpoint(
    project_id: str, scenario_id: str, db: DB, user: CurrentUser,
    top_k: int = Query(5, ge=1, le=20),
    min_similarity: float = Query(0.75, ge=0.0, le=1.0),
):
    """Aynı proje içinde, hedef senaryoya en yakın N senaryoyu döndürür."""
    from app.domains.ai.scenario_quality import find_similar_scenarios, embed_scenario

    target = db.get(TspmScenario, scenario_id)
    if target is None or target.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Senaryo bulunamadı")
    _get_project(db, project_id, user)

    target_emb = target.title_embedding
    if not target_emb:
        # embedding yoksa uçup ver
        try:
            target_emb = embed_scenario(target.title, target.description, target.steps)
        except Exception:
            target_emb = None
        if target_emb:
            target.title_embedding = target_emb
            db.add(target)
            db.commit()

    if not target_emb:
        return {"similar": [], "reason": "embedding_unavailable"}

    # Aynı projenin tüm diğer senaryoları
    stmt = (
        select(TspmScenario)
        .where(TspmScenario.project_id == project_id)
        .where(TspmScenario.id != scenario_id)
        .limit(500)
    )
    candidates = [
        (s.id, s.title, s.title_embedding)
        for s in db.scalars(stmt)
        if s.title_embedding  # sadece embed edilmişler
    ]
    similar = find_similar_scenarios(
        target_emb, candidates, top_k=top_k, min_similarity=min_similarity,
    )
    return {"similar": similar, "candidate_count": len(candidates)}


@router.post("/projects/{project_id}/wizard/score-all")
def score_all_scenarios(
    project_id: str, db: DB, user: CurrentUser,
    body: dict | None = None,
):
    """Projenin tüm (veya body.scenario_ids ile belirtilen) senaryolarını
    toplu skorla + embed. Step 4'te saveAllScenarios sonrası async olarak
    UI tarafından tetiklenir.

    Body (opsiyonel)::

        {"scenario_ids": ["..."] | null, "force": false}
    """
    from app.domains.ai.scenario_quality import find_similar_scenarios

    _get_project(db, project_id, user)
    body = body or {}
    ids = body.get("scenario_ids") if isinstance(body, dict) else None
    force = bool((body or {}).get("force", False))

    stmt = select(TspmScenario).where(TspmScenario.project_id == project_id)
    if ids and isinstance(ids, list):
        stmt = stmt.where(TspmScenario.id.in_(ids))
    stmt = stmt.limit(500)
    scenarios = list(db.scalars(stmt))

    scored = 0
    skipped = 0
    sources: dict[str, int] = {}
    for s in scenarios:
        if not force and s.quality_score is not None and s.title_embedding:
            skipped += 1
            continue
        try:
            result = _refresh_scenario_quality(db, s)
            sources[result.get("source", "unknown")] = sources.get(result.get("source", "unknown"), 0) + 1
            scored += 1
        except Exception as exc:  # noqa: BLE001 — tek senaryo hatası batch'i çökertmesin
            logger.warning("Senaryo %s skorlanamadı: %s", s.id, exc)
    db.commit()

    # Her skorlanan senaryo için duplicate hint de hazırla (aynı liste üzerinde)
    duplicates: dict[str, list[dict[str, Any]]] = {}
    emb_map = [(s.id, s.title, s.title_embedding) for s in scenarios if s.title_embedding]
    for s in scenarios:
        if not s.title_embedding:
            continue
        others = [(cid, t, e) for cid, t, e in emb_map if cid != s.id]
        sim = find_similar_scenarios(
            s.title_embedding, others, top_k=3, min_similarity=0.85,
        )
        if sim:
            duplicates[s.id] = sim

    # Skor özeti
    scores = [s.quality_score for s in scenarios if s.quality_score is not None]
    avg = int(round(sum(scores) / len(scores))) if scores else 0

    return {
        "total": len(scenarios),
        "scored": scored,
        "skipped_existing": skipped,
        "avg_score": avg,
        "sources": sources,
        "scenarios": [
            {
                "id": s.id,
                "title": s.title,
                "quality_score": s.quality_score,
                "quality_summary": s.quality_summary,
                "quality_issues": s.quality_issues or [],
                "has_embedding": bool(s.title_embedding),
                "duplicates": duplicates.get(s.id, []),
            }
            for s in scenarios
        ],
    }


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


@router.delete("/projects/{project_id}/scenarios/{scenario_id}", status_code=204)
def delete_scenario(
    project_id: str, scenario_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.SCENARIO_UPDATE))],
):
    """Test senaryosunu siler."""
    _get_project(db, project_id, user)
    scenario_svc.delete_scenario(db, project_id, scenario_id)


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
    from app.domains.billing.gating import enforce_capacity
    _get_project(db, project_id, user)
    enforce_capacity(db, user.tenant_id, "run_count_month")
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
    # Üyelik doğrulaması: execution bulunmadan önce proje erişimi şart.
    _get_project(db, project_id, user)
    ex = db.get(TspmExecution, run_id)
    if ex is None or ex.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")
    results = list(
        db.scalars(select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run_id))
    )
    result_out = []
    for r in results:
        sc = db.get(TspmScenario, r.scenario_id)
        result_out.append(ExecutionResultOut(
            id=r.id, scenario_id=r.scenario_id,
            scenario_title=sc.title if sc else "", status=r.status, note=r.note,
        ))
    return ExecutionDetailOut(
        id=ex.id, name=ex.name, status=ex.status,
        created_at=ex.created_at, results=result_out,
        platform=ex.platform,
        device_name=ex.device_name,
        app_upload_id=ex.app_upload_id,
        simulated=bool(getattr(ex, "simulated", False)),
    )


@router.patch("/projects/{project_id}/executions/{run_id}/results/{result_id}")
def update_result_status(
    project_id: str, run_id: str, result_id: str, body: ResultStatusUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_UPDATE))],
):
    # Üyelik + hedef execution'ın bu projeye ait olduğundan emin ol.
    _get_project(db, project_id, user)
    ex = db.get(TspmExecution, run_id)
    if ex is None or ex.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")
    r = db.get(TspmExecutionResult, result_id)
    if r is None or r.execution_id != run_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sonuç bulunamadı")
    r.status = body.status
    db.commit()
    return {"ok": True}


@router.patch(
    "/projects/{project_id}/executions/{run_id}",
    response_model=ExecutionOut,
    summary="Koşum durumunu manuel güncelle (tamamla / iptal et)",
)
def update_execution_status(
    project_id: str, run_id: str, body: ExecutionStatusUpdate, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_UPDATE))],
):
    """UI'daki 'Tamamla' / 'İptal' aksiyonu — yalnızca whitelist durum geçişlerini kabul eder.

    Not: Bu uç yalnızca DB kaydını mühürler; in-flight engine/runner thread'ini
    durdurmaz. Engine tarafı cancel desteği eklenene kadar runner arka planda
    kendi hayatını yaşamaya devam edebilir.
    """
    _get_project(db, project_id, user)
    ex = db.get(TspmExecution, run_id)
    if ex is None or ex.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")

    ex.status = body.status
    db.commit()
    db.refresh(ex)

    # Aggregate counts (ExecutionOut şeması bunları bekler).
    results = list(db.scalars(
        select(TspmExecutionResult).where(TspmExecutionResult.execution_id == run_id)
    ))
    passed = sum(1 for r in results if r.status == "passed")
    failed = sum(1 for r in results if r.status == "failed")

    return ExecutionOut(
        id=ex.id,
        name=ex.name,
        status=ex.status,
        created_at=ex.created_at,
        scenario_total=len(results),
        passed_count=passed,
        failed_count=failed,
        platform=ex.platform,
        device_name=ex.device_name,
        app_upload_id=ex.app_upload_id,
        simulated=bool(getattr(ex, "simulated", False)),
    )


@router.delete(
    "/projects/{project_id}/executions/{run_id}",
    status_code=204,
    summary="Koşumu ve sonuç kayıtlarını sil",
)
def delete_execution(
    project_id: str, run_id: str, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_UPDATE))],
):
    """Koşumu siler. Ilgili TspmExecutionResult satırları da cascade ile temizlenir."""
    _get_project(db, project_id, user)
    ex = db.get(TspmExecution, run_id)
    if ex is None or ex.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Koşu bulunamadı")

    if ex.status == "running":
        raise HTTPException(409, "Çalışan koşum silinemez; önce tamamlayın veya iptal edin.")

    # İlişkili sonuçları temizle (cascade tanımlı değilse manuel).
    db.execute(
        TspmExecutionResult.__table__.delete().where(
            TspmExecutionResult.execution_id == run_id
        )
    )
    db.delete(ex)
    db.commit()
    return Response(status_code=204)


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


class _ProjectStats(_PydanticBase):
    total_scenarios: int
    total_test_cases: int
    automation_coverage: float
    last_run: Optional[str] = None


@router.get("/projects/{project_id}/stats", response_model=_ProjectStats)
def get_project_stats(project_id: str, db: DB, user: CurrentUser):
    """Proje özet istatistiklerini getirir."""
    _get_project(db, project_id, user)
    total_scenarios = db.scalar(
        select(func.count()).select_from(TspmScenario)
        .where(TspmScenario.project_id == project_id)
    ) or 0
    total_test_cases = db.scalar(
        select(func.count()).select_from(TspmTestCase)
        .where(TspmTestCase.project_id == project_id)
    ) or 0
    active = db.scalar(
        select(func.count()).select_from(TspmScenario)
        .where(
            TspmScenario.project_id == project_id,
            TspmScenario.status != "draft",
        )
    ) or 0
    coverage = round(active / total_scenarios * 100, 1) if total_scenarios else 0.0
    last_execution_at = db.scalar(
        select(func.max(TspmExecution.created_at))
        .where(TspmExecution.project_id == project_id)
    )
    return _ProjectStats(
        total_scenarios=total_scenarios,
        total_test_cases=total_test_cases,
        automation_coverage=coverage,
        last_run=last_execution_at.isoformat() if last_execution_at else None,
    )


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


class _AnomalyIssue(str, Enum):
    timeout = "timeout"
    slow = "slow"
    flapping = "flapping"
    error = "error"


class _AnomalyEntry(_PydanticBase):
    testId: str
    issues: list[_AnomalyIssue]


class _AnomalyReport(_PydanticBase):
    total_tested: int
    anomaly_count: int
    avg_duration_ms: float
    anomalies: list[_AnomalyEntry]


@router.post("/projects/{project_id}/flaky-anomaly", response_model=_AnomalyReport)
def detect_flaky_anomalies(project_id: str, db: DB, user: CurrentUser):
    """Flaky testleri anomali türlerine göre sınıflandırır."""
    _get_project(db, project_id, user)
    flaky = execution_svc.get_flaky_tests_for_project(db, project_id)

    anomalies: list[_AnomalyEntry] = []
    total_duration_ms = 0.0

    for test in flaky:
        issues: list[_AnomalyIssue] = []
        results = [r.lower() for r in test.last_results]

        if test.flip_count >= 5:
            issues.append(_AnomalyIssue.flapping)
        elif test.flip_count >= 2:
            pass

        if any("timeout" in r for r in results):
            issues.append(_AnomalyIssue.timeout)
        if any("error" in r or "fail" in r for r in results):
            if _AnomalyIssue.timeout not in issues:
                issues.append(_AnomalyIssue.error)
        if test.flip_count >= 2 and _AnomalyIssue.flapping not in issues:
            issues.append(_AnomalyIssue.flapping)

        if issues:
            anomalies.append(_AnomalyEntry(testId=test.scenario_id, issues=issues))
        total_duration_ms += test.flip_count * 250.0

    return _AnomalyReport(
        total_tested=len(flaky),
        anomaly_count=len(anomalies),
        avg_duration_ms=round(total_duration_ms / max(len(flaky), 1), 1),
        anomalies=anomalies,
    )


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
    # Resolve title: explicit > draft_payload.title > source_text[:100]
    title = (
        body.title
        or (body.draft_payload or {}).get("title")
        or body.source_text[:100]
        or "Onay"
    )
    approval = TspmApproval(
        project_id=project_id,
        title=title,
        status="pending",
        source_text=body.source_text or None,
        draft_payload=body.draft_payload or None,
        source_batch_id=body.source_batch_id,
        source_test_case_id=body.source_test_case_id,
    )
    db.add(approval)
    db.commit()
    db.refresh(approval)
    return approval


@router.post("/projects/{project_id}/approvals/{approval_id}/decide")
def decide_approval(
    project_id: str, approval_id: str, body: DecideRequest, db: DB,
    user: Annotated[User, Depends(require_permission(Permission.APPROVAL_DECIDE))],
):
    a = db.get(TspmApproval, approval_id)
    if a is None or a.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Onay bulunamadı")
    a.status = body.decision
    a.decided_at = utcnow()
    a.decision_note = body.notes or None
    a.decision_trace = {
        "decision": body.decision,
        "note": body.notes or None,
        "source_batch_id": a.source_batch_id,
        "source_test_case_id": a.source_test_case_id,
        "scenario_id": a.scenario_id,
        "decided_at": a.decided_at.isoformat() if a.decided_at else None,
    }

    # Auto-create scenario from draft_payload when approved
    if body.decision == "approved" and a.draft_payload and a.scenario_id is None:
        dp = a.draft_payload
        sc = TspmScenario(
            project_id=project_id,
            title=dp.get("title", a.title),
            description=dp.get("description", ""),
            steps=dp.get("steps", []),
            tags=[],
        )
        db.add(sc)
        db.flush()
        a.scenario_id = sc.id
        a.decision_trace = {
            **(a.decision_trace or {}),
            "scenario_id": sc.id,
            "scenario_title": sc.title,
        }

    db.commit()
    return {"ok": True, "scenario_id": a.scenario_id}


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
          "name": "kullanıcılar",
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
            {"name": "kullanici_id", "type": "foreign_key", "references": "kullanıcılar.id"},
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
    """Entegrasyon kaynak sistemi ile eşzamanlamayı tetikler.

    Şu an için hiçbir provider için gerçek bir sync akışı yok (Jira, Slack,
    webhook, n8n hepsi CRUD + test-notification seviyesinde kalıyor). Bu
    endpoint'i çağıran istemcinin bu durumu fark edebilmesi için cevap
    `stub=true` bayrağı ile işaretlenir ve `last_sync_at` güncellenmez; aksi
    halde UI "sync başarılı" gösterir ama hiçbir şey eşzamanlanmamıştır
    (sessiz kullanıcı aldatması).
    """
    intg = db.get(TspmIntegration, integration_id)
    if intg is None or intg.project_id != project_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entegrasyon bulunamadı")
    # NOT: `last_sync_at` gerçek bir eşzamanlama olmadığı için bilerek
    # güncellenmez; implementasyon eklendiğinde burada set edilmelidir.
    return SyncResultOut(
        synced_count=0,
        stub=True,
        provider=intg.provider,
        message=(
            f"Sync henüz {intg.provider!r} provider'ı için uygulanmadı. "
            "Bu yanıt bir yer tutucudur (stub=true). Gerçek eşzamanlama "
            "provider-özel akış eklendiğinde etkinleşecektir."
        ),
    )


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

ENGINE_BASE_URL = (os.environ.get("ENGINE_BASE_URL") or settings.engine_base_url).rstrip("/")
_ENGINE_KEY = os.environ.get("ENGINE_INTERNAL_KEY") or settings.engine_internal_key
_IKEY = {"X-Internal-Key": _ENGINE_KEY}


@router.post("/projects/{project_id}/wizard/analyze")
def wizard_analyze(project_id: str, body: dict, db: DB, user: CurrentUser):
    """
    Analiz dokümanından AI ile manuel test senaryoları + BDD üretir.
    Nexus QA: Önce AI Gateway (vLLM→Groq→Gemini→Ollama) denenir,
    başarısız olursa eski engine/backend AI yolu kullanılır.
    """
    import json as _json
    from concurrent.futures import ThreadPoolExecutor, as_completed

    _get_project(db, project_id, user)
    text = body.get("text", "")
    extra = body.get("extra_instructions", "")
    if not text.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Analiz metni gereklidir")

    # Metin uzunluğunu sınırla — daha kısa = daha hızlı
    text_for_analysis = text[:5000]
    text_for_cases = text[:3000]

    results: dict = {"manual_tests": [], "bdd_scenarios": [], "ai_provider": None}

    # ── 1) Nexus QA AI Gateway (birincil yol) ──────────────────────────────
    try:
        from app.domains.ai.gateway_client import gateway_analyze_document, gateway_complete

        # Her iki AI çağrısını paralelde çalıştır — toplam süreyi yarıya indirir
        def _call_analyze():
            return gateway_analyze_document(
                doc_text=text_for_analysis,
                extra_instructions=extra,
                project_id=project_id,
            )

        def _call_cases():
            return gateway_complete(
                task_type="generate_test_cases",
                user_message=f"Doküman:\n{text_for_cases}\n\nEk talimatlar: {extra}",
                temperature=0.4,
                max_tokens=1500,
                project_id=project_id,
            )

        analysis = None
        manual_raw = None
        with ThreadPoolExecutor(max_workers=2) as pool:
            fut_analyze = pool.submit(_call_analyze)
            fut_cases = pool.submit(_call_cases)
            analysis = fut_analyze.result()
            manual_raw = fut_cases.result()

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

        # DSL snap pass — Gateway'den gelen ham adımları kanonikleştir
        try:
            from app.domains.tspm.bdd_generator import _snap_scenario_steps
            bdd_from_gateway = _snap_scenario_steps(bdd_from_gateway)
        except Exception as _snap_err:
            import logging
            logging.getLogger(__name__).debug(
                "Gateway BDD snap atlandı: %s", _snap_err
            )

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
            results["manual_tests"] = [
                {
                    "title": tc.get("title", "Test Case"),
                    "steps": [
                        {"action": step, "expected": f"{step} başarılı"}
                        for step in (tc.get("steps", []) if isinstance(tc.get("steps", []), list) else [])
                    ] or [{"action": tc.get("description", "Adım"), "expected": tc.get("expected_result", "Başarılı")}],
                }
                for tc in manual_tests_raw[:15]
            ]
        except _json.JSONDecodeError:
            results["manual_tests"] = []

        # DSL snap pass — Gateway'ın ürettiği ham step'leri kataloğun kanonik
        # alias'larına eşle (katalog yoksa no-op). _snap_scenario_steps her
        # senaryoya dsl_coverage ve opsiyonel "needs-dsl" tag'i ekler.
        try:
            from app.domains.tspm.bdd_generator import _snap_scenario_steps
            bdd_from_gateway = _snap_scenario_steps(bdd_from_gateway)
        except Exception as snap_err:  # noqa: BLE001
            logging.getLogger(__name__).debug(
                "Gateway BDD DSL snap atlandı: %s", snap_err
            )

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


@router.post("/projects/{project_id}/wizard/analyze-multimodal")
def wizard_analyze_multimodal(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Görsel destekli analiz — text + mockup/screenshot kombine.

    Body şeması:
      {
        "text": "Analiz dokümanı metni veya kısa açıklama",
        "extra_instructions": "Opsiyonel ek talimat",
        "images": [
          "data:image/png;base64,iVBORw0KGgo...",  // veya doğrudan http(s) URL
          ...
        ]
      }

    Vision-capable model (GPT-4o, Claude 3+, Gemini 1.5+) kullanır.
    Görsel yoksa otomatik olarak metin-only analyze'a düşer.
    """
    _get_project(db, project_id, user)
    text = body.get("text", "")
    extra = body.get("extra_instructions", "")
    images = body.get("images") or []

    if not isinstance(images, list):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "images bir liste olmalıdır")
    if not text.strip() and not images:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "En az text veya bir görsel gereklidir")

    # Toplam görsel boyutunu sınırla (DoS koruması) — toplam 20MB
    total_size = sum(len(img) if isinstance(img, str) else 0 for img in images)
    if total_size > 20 * 1024 * 1024:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            "Toplam görsel boyutu 20MB'ı aşıyor",
        )

    from app.domains.ai.gateway_client import (
        gateway_analyze_document_multimodal,
        gateway_complete,
    )

    text_for_analysis = (text or "")[:5000]

    try:
        analysis = gateway_analyze_document_multimodal(
            doc_text=text_for_analysis,
            images=images,
            extra_instructions=extra,
            project_id=project_id,
        )
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            f"AI multimodal analiz başarısız: {exc}",
        )

    # Manuel test case'leri tekrar üret (multimodal analiz çıktısı + orijinal text birlikte)
    manual_tests: list = []
    try:
        modules_summary = ""
        for m in analysis.get("modules", []) or []:
            modules_summary += f"- {m.get('name', '?')}: {m.get('description', '')}\n"
        if modules_summary:
            cases_raw = gateway_complete(
                task_type="generate_test_cases",
                user_message=(
                    f"Aşağıdaki modüller için test case'leri üret:\n{modules_summary}\n\n"
                    f"Orijinal doküman bağlamı:\n{text_for_analysis[:1500]}"
                ),
                temperature=0.4,
                max_tokens=2500,
                project_id=project_id,
            )
            import json as _json
            try:
                parsed_cases = _json.loads(cases_raw)
                if isinstance(parsed_cases, dict):
                    manual_tests = parsed_cases.get("test_cases", []) or []
                elif isinstance(parsed_cases, list):
                    manual_tests = parsed_cases
            except Exception:
                pass
    except Exception:
        pass

    return {
        "analysis": analysis,
        "manual_tests": manual_tests,
        "bdd_scenarios": [],
        "ai_provider": "multimodal-gateway",
        "image_count": len(images),
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
    """Engine erişilemezse temel Gherkin + Playwright şablonu üretir.

    DİKKAT: Bu fonksiyonun döndürdüğü TS içerikleri gerçek otomasyon
    değildir; `// TODO: Adımları otomasyona çevirin` placeholder'ları
    barındırır. Bu nedenle sonuç dict'i `simulated: true` ve `fallback`
    bayraklarıyla zenginleştirilir — UI/CI tüketicileri bu koşumun
    gerçek engine çıktısı olmadığını ayırt edebilir.
    """
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

    return {
        "feature_files": feature_files,
        "test_files": test_files,
        "simulated": True,
        "fallback": True,
        "notice": (
            "Engine erişilemediği için otomasyon şablon olarak üretildi. "
            "Üretilen test dosyaları '// TODO' satırları içerir ve gerçek "
            "doğrulama yapmaz. Engine'i ayağa kaldırıp yeniden deneyin."
        ),
    }


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


# ── Locator matching helpers ────────────────────────────────────────────────

_MAVIYAKA_ACTION_VERBS = {
    "click":  ("When", "I click on"),
    "input":  ("When", "I enter"),
    "clear":  ("When", "I clear the input"),
    "see":    ("Then", "I see the element"),
    "verify": ("Then", "I verify element"),
    "wait":   ("When", "I wait for element"),
    "open":   ("Given", "I open the application url"),
}

# Türkçe/İngilizce fiil → MaviYaka action mapping
_ACTION_KEYWORD_MAP: list[tuple[tuple[str, ...], str]] = [
    (("open", "aç", "git", "navig", "url", "sayfa"), "open"),
    (("click", "tikla", "tıkla", "bas", "press", "select", "seç", "sec"), "click"),
    (("enter", "gir", "yaz", "write", "type", "doldur", "fill"), "input"),
    (("clear", "temizle", "sil"), "clear"),
    (("see", "gör", "gor", "verify", "doğrula", "dogrula", "check", "kontrol", "exist", "appear", "display", "görün", "gorun"), "see"),
    (("wait", "bekle"), "wait"),
]


# ═══════════════════════════════════════════════════════════════════════
# XPath yardımcıları — normalize, lint, kalite skoru
# ═══════════════════════════════════════════════════════════════════════

# Türkçe → ASCII translate() çifti (büyük/küçük + diakritik güvenli karşılaştırma için)
_TR_UPPER = "ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ"
_TR_LOWER = "abcçdefgğhıijklmnoöprsştuüvyz"


def _normalize_xpath(x: str) -> str:
    """XPath string'ini kanonik + sağlam bir biçime sokar.

    - Baştaki '/html[/body]' prefix'ini atar (iframe/shadow güvenliği adına)
    - Whitespace'i sadeleştirir
    - Çift tırnakları tek tırnağa çevirir (iç değerde tırnak yoksa)
    - Literal `text()='X'` → `normalize-space()='X'`
    - Türkçe metin karşılaştırmalarını otomatik `translate()` ile sarar
    """
    if not isinstance(x, str):
        return ""
    v = x.strip()
    if not v:
        return ""

    # `/html/body/...` veya `/html/...` absolute prefix → relative yap
    v = re.sub(r"^/html(/body)?(?=/)", "", v, flags=re.IGNORECASE)

    # Fazla boşlukları sadele
    v = re.sub(r"\s+", " ", v)

    # text()='X' → normalize-space()='X' (sadece literal eşitlik formu)
    v = re.sub(r"\btext\(\)\s*=\s*", "normalize-space()=", v)

    # Türkçe karakter içeren literal string karşılaştırmalarını translate() ile kaplasın.
    # Örn.  normalize-space()='Giriş Yap'
    #   →  translate(normalize-space(.),'ABCÇ...','abcç...')='giriş yap'
    def _wrap_tr(match: re.Match) -> str:
        lhs = match.group(1)  # normalize-space() | normalize-space(.) | .
        literal = match.group(2)
        if not any(ch in literal for ch in "çğıöşüÇĞİÖŞÜ"):
            return match.group(0)
        low = literal.lower().translate(str.maketrans(_TR_UPPER, _TR_LOWER))
        return (
            f"translate({lhs},'{_TR_UPPER}','{_TR_LOWER}')='{low}'"
        )

    v = re.sub(
        r"(normalize-space\([^)]*\)|\.)\s*=\s*'([^']+)'",
        _wrap_tr,
        v,
    )

    return v


def _validate_xpath_syntax(x: str) -> tuple[bool, str]:
    """Kaba syntax kontrolü. (True, '') → geçerli görünüyor.

    lxml eklemeden token ve parantez dengesine bakar. Tam doğrulama değildir
    ama LLM çıktısındaki en yaygın kırılmaları yakalar.
    """
    if not isinstance(x, str) or not x.strip():
        return False, "empty"
    s = x.strip()
    # Başlangıç: '/' veya '.' veya fonksiyon çağrısı / axis
    if not re.match(r"^(/|\.|\(|id\(|key\(|xpath\s*=)", s):
        # id=, css= gibi pseudo formlar dış sistem biçimidir → xpath değil
        return False, "not-xpath"
    # Parantez dengesi
    if s.count("(") != s.count(")"):
        return False, "paren-imbalance"
    if s.count("[") != s.count("]"):
        return False, "bracket-imbalance"
    # Tırnak dengesi (cift + tek)
    if s.count("'") % 2 != 0:
        return False, "quote-imbalance"
    if s.count('"') % 2 != 0:
        return False, "double-quote-imbalance"
    # Sezgisel: '//' sonrası boş kalan kullanımlar
    if re.search(r"//\s*(\[|$)", s):
        return False, "empty-step"
    return True, ""


def _score_xpath(x: str) -> dict:
    """XPath için 0-100 stabilite skoru + issue listesi döner.

    Şema:
        {
          "score": int (0-100),
          "grade": "good" | "warn" | "bad" | "invalid",
          "issues": [str, ...],
          "strengths": [str, ...],
        }
    """
    issues: list[str] = []
    strengths: list[str] = []

    if not isinstance(x, str) or not x.strip():
        return {"score": 0, "grade": "invalid", "issues": ["empty"], "strengths": []}

    # xpath= / css= / id= gibi pseudo biçimler → saf xpath değil
    if re.match(r"^(css|id|name)\s*=", x.strip(), flags=re.IGNORECASE):
        return {
            "score": 30,
            "grade": "warn",
            "issues": ["pseudo-selector (saf XPath değil)"],
            "strengths": [],
        }

    ok, why = _validate_xpath_syntax(x)
    if not ok:
        return {"score": 0, "grade": "invalid", "issues": [f"syntax: {why}"], "strengths": []}

    score = 70  # taban
    s = x.strip()

    # + güçlü sinyaller
    if re.search(r"@data-(testid|test|qa|cy)\s*=", s):
        score += 20
        strengths.append("data-testid")
    if re.search(r"@aria-label\s*=", s):
        score += 10
        strengths.append("aria-label")
    if re.search(r"@id\s*=", s) and not re.search(r"@id\s*=\s*['\"][\w-]{1,2}['\"]", s):
        score += 8
        strengths.append("@id")
    if "normalize-space" in s:
        score += 5
        strengths.append("normalize-space")
    if "translate(" in s:
        score += 5
        strengths.append("i18n translate()")
    if re.search(r"@role\s*=", s):
        score += 3
        strengths.append("@role")

    # − kırılgan sinyaller
    if re.match(r"^/html(/|$)", s, flags=re.IGNORECASE):
        score -= 35
        issues.append("absolute /html path")
    depth = s.count("/")
    if depth >= 8:
        score -= 15
        issues.append(f"derin path ({depth} seviye)")
    elif depth >= 6:
        score -= 8
        issues.append(f"orta derin path ({depth} seviye)")

    # numerik index kullanımı (örn. div[3])
    if re.search(r"\[\s*\d+\s*\]", s):
        score -= 12
        issues.append("numeric index ([n])")

    # dinamik class (css-1ab2cd, MuiButton-root-abc123 gibi)
    if re.search(r"@class\s*=\s*['\"][^'\"]*[a-z]+-[a-z0-9]{5,}", s):
        score -= 12
        issues.append("dinamik class adı")
    # contains(@class,'x') → tek karakterli / anlamsız token
    for m in re.finditer(r"contains\(\s*@class\s*,\s*['\"]([^'\"]+)['\"]\s*\)", s):
        token = m.group(1).strip()
        if len(token) < 3:
            score -= 10
            issues.append(f"contains(@class,'{token}') — çok kısa token")
        elif re.search(r"[a-z]+-[a-z0-9]{5,}", token):
            score -= 10
            issues.append(f"contains(@class,'{token}') — dinamik class")

    # last() / position() gibi desenler → kırılgan
    if "last()" in s or "position()" in s:
        score -= 6
        issues.append("position/last() kullanımı")

    # Türkçe karakterli literal + translate yoksa → kırılabilir
    if (
        any(ch in s for ch in "çğıöşüÇĞİÖŞÜ")
        and "translate(" not in s
    ):
        score -= 8
        issues.append("TR karakter var ama translate() yok")

    score = max(0, min(100, score))
    if score >= 80:
        grade = "good"
    elif score >= 50:
        grade = "warn"
    else:
        grade = "bad"
    return {"score": score, "grade": grade, "issues": issues, "strengths": strengths}


def _best_xpath_for_locator(loc: dict) -> str:
    """Bir locator objesinden en kararlı XPath değerini çıkarır.

    Öncelik sırası (en stabilden kırılgana):
        1. data-testid / data-test / data-qa / data-cy
        2. Primary xpath (varsa)
        3. Alternatives içindeki ilk xpath
        4. @id (anlamlı)
        5. @aria-label
        6. @name
        7. CSS → XPath türetmesi
        8. Ham pseudo-selector (css=…)

    Sonuç `_normalize_xpath` ile kanonik hâle getirilir.
    """
    loc_type = (loc.get("type") or "").lower()
    loc_val = str(loc.get("value") or "").strip()
    alts = loc.get("alternatives") or []
    extras = loc.get("extras") or {}

    # 1) data-testid / data-test / data-qa / data-cy
    for tkey in ("testid", "data-testid", "data-test", "data-qa", "data-cy"):
        tid = extras.get(tkey) if isinstance(extras, dict) else None
        if not tid:
            tid = loc.get(tkey) if isinstance(loc, dict) else None
        if tid and isinstance(tid, str) and tid.strip():
            attr = "data-testid" if "testid" in tkey or tkey == "data-testid" else tkey
            return _normalize_xpath(f"//*[@{attr}='{tid.strip()}']")

    # 2) Primary zaten xpath
    if loc_type == "xpath" and loc_val:
        return _normalize_xpath(loc_val)

    # 3) Alternatives içinde xpath ara
    for alt in alts:
        if not isinstance(alt, dict):
            continue
        if (alt.get("type") or "").lower() == "xpath" and alt.get("value"):
            return _normalize_xpath(str(alt["value"]))

    # 4) Primary type'a göre XPath üret
    if loc_type == "id" and loc_val:
        return _normalize_xpath(f"//*[@id='{loc_val}']")
    if loc_type == "name" and loc_val:
        return _normalize_xpath(f"//*[@name='{loc_val}']")

    # 5) aria-label ipucu
    aria = (loc.get("aria_label") or (extras.get("aria-label") if isinstance(extras, dict) else None))
    if aria and isinstance(aria, str) and aria.strip():
        return _normalize_xpath(f"//*[@aria-label='{aria.strip()}']")

    # 6) CSS → XPath
    if loc_type == "css" and loc_val:
        if loc_val.startswith("#"):
            return _normalize_xpath(f"//*[@id='{loc_val[1:]}']")
        if loc_val.startswith("."):
            return _normalize_xpath(
                f"//*[contains(concat(' ', normalize-space(@class), ' '), ' {loc_val[1:]} ')]"
            )
        # Genel fallback: css tipini göster (pseudo-selector)
        return f"css={loc_val}"

    return f"{loc_type}={loc_val}" if loc_val else ""


def _detect_action_from_step(keyword: str, text: str) -> str:
    """Step metninden MaviYaka action türünü çıkarır (click/input/see/...)."""
    norm = f"{keyword} {text}".lower()
    for keys, action in _ACTION_KEYWORD_MAP:
        if any(k in norm for k in keys):
            return action
    # Fallback: Gherkin keyword'a göre
    kw_norm = (keyword or "").lower().strip()
    if kw_norm in ("then", "o zaman"):
        return "see"
    return "click"


def _score_locator_for_step(step_text: str, loc: dict) -> float:
    """Step metni ↔ locator arası benzerlik skoru (0..1).

    Kelime örtüşmesine + key/text/tag eşleşmesine bakar.
    """
    if not step_text:
        return 0.0
    step_norm = re.sub(r"[^0-9a-zçğıöşüA-ZÇĞİÖŞÜ ]+", " ", str(step_text)).lower()
    step_words = {w for w in step_norm.split() if len(w) > 1}
    if not step_words:
        return 0.0

    # Locator key'ini kelimelere böl (CamelCase → ayrı)
    key = str(loc.get("key") or "")
    key_parts = re.findall(r"[A-ZÇĞİÖŞÜ][^A-ZÇĞİÖŞÜ]*|[a-zçğıöşü0-9]+", key)
    key_words = {p.lower() for p in key_parts if len(p) > 1}

    text_hint = str(loc.get("text") or "").lower()
    text_words = {w for w in re.findall(r"\w+", text_hint) if len(w) > 1}

    tag = str(loc.get("tag") or "").lower()
    overlap = len((key_words | text_words) & step_words)
    denom = max(len(step_words), 1)
    base = overlap / denom

    # Tag bonusu: step tıklama içeriyorsa button/link locator bonus
    if tag in {"button", "a", "input", "select", "textarea"}:
        if any(k in step_norm for k in ("tıkla", "click", "bas", "press", "seç")) and tag in {"button", "a"}:
            base += 0.15
        if any(k in step_norm for k in ("gir", "yaz", "enter", "type", "doldur")) and tag in {"input", "textarea"}:
            base += 0.15
    return min(base, 1.0)


def _rule_based_match(step_text: str, locators: list[dict]) -> dict | None:
    """LLM yoksa en iyi locator'ı kural bazlı seçer. Sıfır skor -> None."""
    if not locators:
        return None
    scored = [(_score_locator_for_step(step_text, l), l) for l in locators]
    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_loc = scored[0]
    if best_score <= 0.0:
        return None
    return {
        "locator_key": best_loc.get("key"),
        "xpath": _best_xpath_for_locator(best_loc),
        "locator_type": best_loc.get("type"),
        "locator_value": best_loc.get("value"),
        "score": round(best_score, 3),
        "source": "rule",
    }


# Türkçe → ASCII çevirisi; adım metninden PascalCase locator key türetme için.
_TR_ASCII_MAP = {
    "ç": "c", "ğ": "g", "ı": "i", "ö": "o", "ş": "s", "ü": "u",
    "Ç": "C", "Ğ": "G", "İ": "I", "Ö": "O", "Ş": "S", "Ü": "U",
}
_DERIVE_STOPWORDS = {
    "olur", "olan", "icin", "bir", "bu", "ve", "veya", "ile", "sonra", "once",
    "kadar", "daha", "gibi", "ama", "fakat", "the", "and", "for", "into", "with",
    "on", "at", "an", "is", "are", "was", "were", "been", "be",
    "kullanici", "user",  # fiil değil, genel özne — key'i daraltır
}


def _derive_locator_key_from_step(text: str, fallback: str = "Element") -> str:
    """Adım metninden makul bir PascalCase locator key üretir.

    Katalogda eşleşme bulunmadığı halde LLM/rule-based iyi bir XPath önerdiğinde
    sözdizimi tutarlı bir key ataması için kullanılır ("orphan XPath" durumu).
    """
    if not text:
        return fallback
    ascii_s = "".join(_TR_ASCII_MAP.get(c, c) for c in str(text))
    # Tırnaklı literal değerleri (input değerleri) çıkar — key bunlardan etkilenmesin.
    cleaned = re.sub(r'"[^"]*"', " ", ascii_s)
    cleaned = re.sub(r"[^a-zA-Z0-9 ]+", " ", cleaned)
    parts: list[str] = []
    for w in cleaned.split():
        if len(w) < 3:
            continue
        if w.lower() in _DERIVE_STOPWORDS:
            continue
        parts.append(w[:1].upper() + w[1:].lower())
        if len(parts) >= 3:
            break
    return "".join(parts) or fallback


_ACTIONS_NEEDING_LOCATOR = {"click", "input", "clear", "wait", "verify", "see"}


def _build_maviyaka_line(
    action: str,
    locator_key: str | None,
    value: str | None,
    url: str,
    xpath: str | None = None,
    xpath_quality: dict | None = None,
) -> str:
    """Tek bir MaviYaka adım satırı üretir.

    xpath verilmişse adımın üstüne Gherkin yorum satırı olarak gömer
    (runner tarafından yok sayılır, IDE'de görünür kalır).
    locator_key yoksa ve aksiyon locator gerektiriyorsa "Element" yerine
    TODO yorumu üretip kullanıcıyı Step 7 eşleştirmeye yönlendirir.
    """
    needs_loc = action in _ACTIONS_NEEDING_LOCATOR
    comment_lines: list[str] = []
    if xpath:
        grade = (xpath_quality or {}).get("grade") if isinstance(xpath_quality, dict) else None
        score = (xpath_quality or {}).get("score") if isinstance(xpath_quality, dict) else None
        tag = f" · {grade}" if grade else ""
        tag += f" ({score}/100)" if isinstance(score, (int, float)) else ""
        comment_lines.append(f"    # xpath={xpath}{tag}")
    if needs_loc and not locator_key:
        comment_lines.append(
            "    # TODO: locator eşleşmedi — Step 7'deki 'AI öner' ile bu adıma locator ata"
        )

    lk = locator_key or "Element"
    if action == "open":
        step = f'    Given I open the application url "{url}"'
    elif action == "click":
        step = f'    When I click on "{lk}"'
    elif action == "input":
        val = value or "+-value"
        step = f'    When I enter "{val}" into the input "{lk}"'
    elif action == "clear":
        step = f'    When I clear the input "{lk}"'
    elif action == "wait":
        step = f'    When I wait for element "{lk}" to be clickable'
    elif action == "verify":
        val = value or ""
        step = f'    Then I verify element "{lk}" text is "{val}"'
    else:
        step = f'    Then I see the element "{lk}"'

    if comment_lines:
        return "\n".join(comment_lines + [step])
    return step


def _extract_value_hint(step_text: str) -> str | None:
    """Step metninden input değer ipucu çıkarır.

    '"example@mail"' gibi tırnak içindeki değeri ya da
    'şifre: xyz' gibi ':' sonrasını yakalar.
    """
    if not step_text:
        return None
    m = re.search(r"[\"'“”‘’]([^\"'“”‘’]{1,80})[\"'“”‘’]", step_text)
    if m:
        return m.group(1).strip()
    m = re.search(r"[:=]\s*([^\n\r,;]{1,80})$", step_text)
    if m:
        return m.group(1).strip().strip("\"'")
    return None


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
                    "content": parsed.get("content", _rule_based_feature(title, sc["steps"], url, locators)),
                })
                test_data_map.update(parsed.get("data_json", {}))
            except Exception:
                # Fallback: rule-based MaviYaka feature — gerçek locator key'lerini kullanır
                features_out.append({
                    "title": title,
                    "content": _rule_based_feature(title, sc["steps"], url, locators),
                })

        return {"features": features_out, "test_data": test_data_map}

    except Exception as e:
        # Fallback without AI — yine de rule-based'i dene
        features_out = []
        for sc in scenarios:
            title = sc["title"]
            features_out.append({
                "title": title,
                "content": _rule_based_feature(title, sc["steps"], url, locators),
            })
        return {"features": features_out, "test_data": {}}


def _rule_based_feature(title: str, steps: list[dict], url: str, locators: list[dict]) -> str:
    """LLM olmadan gerçek locator key'leri ile MaviYaka feature üretir.

    Her adım için locator kataloğundaki en kararlı XPath Gherkin yorumu olarak
    satırın üstüne gömülür (IDE'de adım ↔ XPath eşleşmesi bir bakışta görünür).
    """
    lines: list[str] = [f"Feature: {title}", "", f"  Scenario: {title}"]
    lines.append(_build_maviyaka_line("open", None, None, url))

    locator_by_key: dict[str, dict] = {
        str(l.get("key")): l for l in (locators or []) if isinstance(l, dict) and l.get("key")
    }

    step_list = steps or []
    for s in step_list:
        if not isinstance(s, dict):
            continue
        keyword = s.get("keyword", "")
        text = s.get("text") or s.get("action") or ""
        if not text.strip():
            continue
        match = _rule_based_match(text, locators)
        action = _detect_action_from_step(keyword, text)
        value = _extract_value_hint(text)
        locator_key = match["locator_key"] if match else None
        xpath_val = ""
        if locator_key and locator_key in locator_by_key:
            xpath_val = _best_xpath_for_locator(locator_by_key[locator_key])
        xpath_quality = _score_xpath(xpath_val) if xpath_val else None
        lines.append(
            _build_maviyaka_line(
                action, locator_key, value, url,
                xpath=xpath_val or None, xpath_quality=xpath_quality,
            )
        )
    return "\n".join(lines) + "\n"


# ═══════════════════════════════════════════════════════════════════════
# Match Manual Scenarios — Step ↔ Locator ↔ XPath eşleştirme (LLM)
# ═══════════════════════════════════════════════════════════════════════

@router.post("/projects/{project_id}/wizard/match-manual-scenarios")
def wizard_match_manual_scenarios(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Mevcut manuel senaryoların her adımını, verilen locator kataloğundaki
    en uygun key + XPath ile LLM üzerinden eşler. Sonuç: feature dosyaları +
    ayrıntılı mapping raporu (hangi step hangi locator'a + XPath'e bağlandı).

    Body:
        scenario_ids: [str]
        url: str
        domain: str
        environment: str
        locators: [{key, type, value, alternatives: [{type, value}], tag?, text?}]
    """
    _get_project(db, project_id, user)

    scenario_ids: list[str] = body.get("scenario_ids", [])
    url: str = body.get("url", "")
    domain: str = body.get("domain", "web")
    environment: str = body.get("environment", "test")
    locators: list[dict] = body.get("locators", [])

    if not scenario_ids:
        raise HTTPException(400, "scenario_ids zorunlu")
    if not locators:
        raise HTTPException(400, "locators zorunlu (önce lokator yükle/tara)")

    rows = db.scalars(
        select(TspmScenario).where(
            TspmScenario.id.in_(scenario_ids),
            TspmScenario.project_id == project_id,
        )
    ).all()
    scenarios = [{"id": r.id, "title": r.title, "steps": r.steps or []} for r in rows]
    if not scenarios:
        raise HTTPException(400, "Senaryo bulunamadı")

    # LLM için kompakt locator kataloğu (XPath dahil)
    compact_catalog: list[dict] = []
    for loc in locators:
        if not isinstance(loc, dict):
            continue
        compact_catalog.append({
            "key": loc.get("key"),
            "type": loc.get("type"),
            "value": loc.get("value"),
            "xpath": _best_xpath_for_locator(loc),
            "tag": loc.get("tag"),
            "text": loc.get("text"),
        })

    catalog_json_str = _json_compact(compact_catalog[:80])

    features_out: list[dict] = []
    mapping_report: list[dict] = []
    test_data_map: dict[str, str] = {}

    try:
        from app.domains.ai.service import call_llm
        import json as _json

        for sc in scenarios:
            title = sc["title"]
            steps = sc["steps"] or []
            step_brief = [
                {
                    "idx": i,
                    "keyword": s.get("keyword", "") if isinstance(s, dict) else "",
                    "text": (s.get("text") or s.get("action") or "") if isinstance(s, dict) else str(s),
                }
                for i, s in enumerate(steps)
            ]

            prompt = (
                "Aşağıdaki manuel test adımlarını MaviYaka Cucumber adım tanımlarına "
                "dönüştür ve HER adımı verilen locator kataloğundaki en uygun key ile eşle.\n\n"
                f"{MAVIYAKA_STEP_DEFS}\n"
                f"Hedef URL: {url}\n"
                f"Domain: {domain} | Environment: {environment}\n\n"
                "LOCATOR KATALOGU (JSON, her satırda key + type=value + xpath):\n"
                f"{catalog_json_str}\n\n"
                f"TEST SENARYOSU: {title}\n"
                "ADIMLAR (JSON):\n"
                f"{_json_compact(step_brief)}\n\n"
                "KURALLAR:\n"
                "1) Her adım için KATALOG'dan tam olarak bir key seç (yoksa null). UYDURMA.\n"
                "2) action alanı sadece: open, click, input, clear, see, verify, wait olmalı.\n"
                "3) Input adımları için kullanıcı değerini data_value alanına yaz; sabit yerine "
                "@dataKey referansı üretebilirsin (data_json nesnesine de ekle).\n"
                "4) XPath alanı için KATALOG'daki aynı key'in xpath değerini KOPYALA.\n"
                "5) Katalogta olmayan bir XPath yazma; ama yazman gerekiyorsa şu stabilite "
                "kurallarına UY:\n"
                "   a) ASLA `/html` veya `/html/body` ile başlatma (absolute path yasak).\n"
                "   b) Numerik index (`div[3]`) veya `position()/last()` kullanma.\n"
                "   c) Dinamik class (`css-1ab2cd`, `MuiButton-root-xyz123`) kullanma.\n"
                "   d) Öncelik sırası: @data-testid > @id (anlamlı) > @aria-label > @name > "
                "normalize-space() metin eşitliği.\n"
                "   e) Türkçe literal metin karşılaştırmasını `translate(normalize-space(.),"
                "'ABCÇ...ZĞÜ','abcç...zğü')='...'` ile sar.\n"
                "   f) Parantez/köşeli parantez/tırnakları DENGELİ tut.\n"
                "6) Satır başında sadece JSON döndür. Başka metin, açıklama YOK.\n\n"
                'JSON ŞABLONU:\n'
                '{\n'
                '  "mappings": [\n'
                '    {"idx": 0, "original": "kullanıcı Giriş Yap\'a tıklar",\n'
                '     "action": "click", "locator_key": "GirisButon",\n'
                '     "xpath": "//button[@id=\'btnLogin\']", "data_value": null}\n'
                '  ],\n'
                '  "data_json": {"kullaniciAdi": "demo"}\n'
                '}'
            )

            raw = ""
            parsed: dict | None = None
            try:
                raw = call_llm(
                    "Sen MaviYaka test otomasyon uzmanısın. Her adımı locator "
                    "kataloğundaki mevcut bir key ile eşlersin. Yalnızca JSON üret.",
                    prompt,
                    json_mode=True,
                    _trace_agent="maviyaka_match",
                )
                parsed = _json.loads(raw) if isinstance(raw, str) else raw
                if not isinstance(parsed, dict):
                    parsed = None
            except Exception:
                parsed = None

            llm_mappings = (parsed or {}).get("mappings") if isinstance(parsed, dict) else None
            data_json_from_llm = (parsed or {}).get("data_json") if isinstance(parsed, dict) else None
            if isinstance(data_json_from_llm, dict):
                test_data_map.update({str(k): str(v) for k, v in data_json_from_llm.items()})

            # Key seti (doğrulama için)
            known_keys = {str(l.get("key")) for l in locators if l.get("key")}
            xpath_index: dict[str, str] = {
                str(l.get("key")): _best_xpath_for_locator(l)
                for l in locators if l.get("key")
            }

            # LLM mapping → normalize + doğrulama
            scenario_mapping: list[dict] = []
            feature_lines: list[str] = [f"Feature: {title}", "", f"  Scenario: {title}"]

            # Kullanıcının ilk içerikli adımı zaten "open" aksiyonuna düşüyorsa
            # otomatik Given open satırını atla (duplicate navigasyon olmasın).
            first_is_open = False
            for s0 in steps:
                if not isinstance(s0, dict):
                    continue
                t0 = str(s0.get("text") or s0.get("action") or "").strip()
                if not t0:
                    continue
                if _detect_action_from_step(s0.get("keyword", ""), t0) == "open":
                    first_is_open = True
                break

            if not first_is_open:
                feature_lines.append(_build_maviyaka_line("open", None, None, url))
                scenario_mapping.append({
                    "idx": -1,
                    "original": f"(auto) open {url}",
                    "action": "open",
                    "locator_key": None,
                    "xpath": None,
                    "xpath_quality": None,
                    "data_value": None,
                    "source": "auto",
                })

            for i, s in enumerate(steps):
                if not isinstance(s, dict):
                    continue
                raw_text = s.get("text") or s.get("action") or ""
                if not str(raw_text).strip():
                    continue
                keyword = s.get("keyword", "")

                llm_hit: dict | None = None
                if isinstance(llm_mappings, list):
                    for m in llm_mappings:
                        if not isinstance(m, dict):
                            continue
                        if m.get("idx") == i:
                            llm_hit = m
                            break

                locator_key: str | None = None
                action: str = _detect_action_from_step(keyword, raw_text)
                data_value: str | None = _extract_value_hint(raw_text)
                source = "rule"
                score: float | None = None

                if llm_hit:
                    candidate_key = llm_hit.get("locator_key")
                    if candidate_key and str(candidate_key) in known_keys:
                        locator_key = str(candidate_key)
                        source = "llm"
                    llm_action = llm_hit.get("action")
                    if llm_action in {"open", "click", "input", "clear", "see", "verify", "wait"}:
                        action = llm_action
                    if llm_hit.get("data_value"):
                        data_value = str(llm_hit["data_value"])

                # LLM key vermediyse / geçersizse rule-based ile bul
                if not locator_key:
                    rule = _rule_based_match(raw_text, locators)
                    if rule:
                        locator_key = rule["locator_key"]
                        score = rule["score"]
                        source = "rule"

                # LLM bazen katalogda olmayan xpath üretiyor — düzeltme sırası:
                # 1) Katalogdan gelen xpath öncelikli (stabil, ispatlanmış),
                # 2) LLM xpath'i normalize edilir + lint'lenir,
                # 3) Yoksa None kalır.
                xpath_val = xpath_index.get(locator_key or "", "")
                if not xpath_val and llm_hit and llm_hit.get("xpath"):
                    norm = _normalize_xpath(str(llm_hit["xpath"]))
                    ok, _ = _validate_xpath_syntax(norm)
                    xpath_val = norm if ok else ""

                # Orphan XPath: iyi bir XPath var ama katalogda karşılığı yok →
                # adım metninden sentetik bir locator_key türet ve "derived" olarak
                # işaretle. Böylece feature satırında "Element" kalmaz.
                if (
                    xpath_val
                    and not locator_key
                    and action in _ACTIONS_NEEDING_LOCATOR
                ):
                    derived_key = _derive_locator_key_from_step(raw_text)
                    # Aynı isimde katalogda locator varsa çakışma olmasın diye suffix ekle.
                    if derived_key in known_keys:
                        derived_key = f"{derived_key}Derived"
                    locator_key = derived_key
                    source = "derived"

                xpath_quality = _score_xpath(xpath_val) if xpath_val else None

                scenario_mapping.append({
                    "idx": i,
                    "original": raw_text,
                    "action": action,
                    "locator_key": locator_key,
                    "xpath": xpath_val or None,
                    "xpath_quality": xpath_quality,
                    "data_value": data_value,
                    "source": source,
                    "score": score,
                })
                feature_lines.append(
                    _build_maviyaka_line(
                        action, locator_key, data_value, url,
                        xpath=xpath_val or None, xpath_quality=xpath_quality,
                    )
                )

            feature_content = "\n".join(feature_lines) + "\n"
            features_out.append({"title": title, "content": feature_content})
            mapping_report.append({
                "scenario_id": sc["id"],
                "scenario_title": title,
                "steps": scenario_mapping,
                "llm_used": bool(llm_mappings),
            })

    except Exception as e:
        # Son çare: sadece rule-based
        for sc in scenarios:
            title = sc["title"]
            steps = sc["steps"] or []
            scenario_mapping = []
            feature_lines = [f"Feature: {title}", "", f"  Scenario: {title}", _build_maviyaka_line("open", None, None, url)]
            scenario_mapping.append({"idx": -1, "original": f"(auto) open {url}", "action": "open", "locator_key": None, "xpath": None, "xpath_quality": None, "data_value": None, "source": "auto"})
            for i, s in enumerate(steps):
                if not isinstance(s, dict):
                    continue
                raw_text = s.get("text") or s.get("action") or ""
                if not str(raw_text).strip():
                    continue
                keyword = s.get("keyword", "")
                rule = _rule_based_match(raw_text, locators)
                locator_key = rule["locator_key"] if rule else None
                action = _detect_action_from_step(keyword, raw_text)
                data_value = _extract_value_hint(raw_text)
                xpath_val = _best_xpath_for_locator(next((l for l in locators if l.get("key") == locator_key), {})) if locator_key else None
                xpath_quality = _score_xpath(xpath_val) if xpath_val else None
                scenario_mapping.append({
                    "idx": i, "original": raw_text, "action": action,
                    "locator_key": locator_key, "xpath": xpath_val or None,
                    "xpath_quality": xpath_quality,
                    "data_value": data_value, "source": "rule",
                    "score": rule["score"] if rule else None,
                })
                feature_lines.append(
                    _build_maviyaka_line(
                        action, locator_key, data_value, url,
                        xpath=xpath_val or None, xpath_quality=xpath_quality,
                    )
                )
            features_out.append({"title": title, "content": "\n".join(feature_lines) + "\n"})
            mapping_report.append({
                "scenario_id": sc["id"], "scenario_title": title,
                "steps": scenario_mapping, "llm_used": False,
                "error": str(e)[:200],
            })

    return {
        "features": features_out,
        "mappings": mapping_report,
        "test_data": test_data_map,
        "catalog_size": len(locators),
    }


def _json_compact(obj: Any) -> str:
    """Kompakt JSON dump (LLM prompt'u için)."""
    import json as _json
    try:
        return _json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    except Exception:
        return str(obj)


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
            timeout=25.0,
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

            # Tüm olası locator alternatiflerini sırayla topla (yinelenenleri atla)
            alternatives: list[dict[str, str]] = []
            seen_vals: set[tuple[str, str]] = set()

            def _push_alt(t: str | None, v: str | None) -> None:
                if not t or not v:
                    return
                key_pair = (t, v)
                if key_pair in seen_vals:
                    return
                seen_vals.add(key_pair)
                alternatives.append({"type": t, "value": v})

            if el_id:
                _push_alt("id", el_id)
            if testid:
                _push_alt("css", f'[data-testid="{testid}"]')
            if el_name:
                _push_alt("name", el_name)
            if css_sel:
                if css_sel.startswith("#"):
                    _push_alt("id", css_sel[1:])
                else:
                    _push_alt("css", css_sel)
            if xpath_sel:
                _push_alt("xpath", xpath_sel)
            # Metinden XPath fallback — id/name yoksa metin bazlı bir XPath üret
            if text and tag:
                safe_text = text.replace('"', "'")
                _push_alt(
                    "xpath",
                    f"//{tag}[normalize-space()='{safe_text}']"
                    if tag not in {"input", "textarea", "select"}
                    else f"//{tag}[@placeholder='{safe_text}' or @aria-label='{safe_text}']",
                )
            if legacy_sel:
                if legacy_sel.startswith("#"):
                    _push_alt("id", legacy_sel[1:])
                elif legacy_sel.startswith(".") or "[" in legacy_sel:
                    _push_alt("css", legacy_sel)
                else:
                    _push_alt("xpath", legacy_sel)

            if not alternatives:
                continue

            # Birincil (en kararlı) lokator
            primary = alternatives[0]
            loc_type, loc_value = primary["type"], primary["value"]
            # Kalan alternatifleri xpath-öncelikli sırala
            rest = [a for a in alternatives[1:]]
            rest.sort(key=lambda a: 0 if a["type"] == "xpath" else 1)

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

            locators.append({
                "key": final_key,
                "type": loc_type,
                "value": loc_value,
                "alternatives": rest,
                "tag": tag,
                "text": text,
            })

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

Bu URL'ye ait web uygulaması için 14-18 UI elementini (giriş alanları, butonlar, linkler, menü ögeleri, başlıklar) tahmin ederek MaviYaka lokator listesi oluştur.
Her lokator için:
  - PascalCase Türkçe/İngilizce key (ör. GirisButon, KullaniciAdiInput)
  - Birincil type (id/name/css) ve value
  - alternatives: XPath dahil 1-3 alternatif selector

JSON formatı:
[
  {{"key": "GirisButon", "type": "id", "value": "btnLogin",
    "alternatives": [
      {{"type": "xpath", "value": "//button[normalize-space()='Giriş']"}},
      {{"type": "css", "value": "button[type='submit']"}}
    ]
  }}
]
Başka hiçbir şey yazma.""",
                json_mode=True,
            )
            locators = _json.loads(ai_raw) if isinstance(ai_raw, str) else ai_raw
            if isinstance(locators, list) and locators:
                # Alternatifi olmayanlara en azından xpath alternatifi garanti et
                for l in locators:
                    if not isinstance(l, dict):
                        continue
                    l.setdefault("alternatives", [])
                return {"locators": locators}
        except Exception:
            pass
        # Son fallback: genel web element örnekleri (xpath alternatifli ve genişletilmiş)
        domain_hint = url.lower()
        if any(k in domain_hint for k in ["login", "giriş", "auth"]):
            return {"locators": [
                {"key": "KullaniciAdiInput", "type": "name", "value": "username",
                 "alternatives": [
                     {"type": "xpath", "value": "//input[@name='username' or @id='username']"},
                     {"type": "css", "value": "input[name='username']"},
                 ]},
                {"key": "SifreInput", "type": "name", "value": "password",
                 "alternatives": [
                     {"type": "xpath", "value": "//input[@type='password']"},
                     {"type": "css", "value": "input[type='password']"},
                 ]},
                {"key": "BeniHatirlaCheckbox", "type": "css", "value": "input[type='checkbox']",
                 "alternatives": [
                     {"type": "xpath", "value": "//input[@type='checkbox']"},
                 ]},
                {"key": "GirisButon", "type": "css", "value": "button[type='submit']",
                 "alternatives": [
                     {"type": "xpath", "value": "//button[@type='submit']"},
                     {"type": "xpath", "value": "//button[contains(translate(., 'GİRİŞ', 'giriş'), 'giriş')]"},
                 ]},
                {"key": "SifremiUnuttumLink", "type": "xpath", "value": "//a[contains(., 'Şifremi') or contains(., 'Unuttum')]",
                 "alternatives": [{"type": "css", "value": "a[href*='forgot']"}]},
                {"key": "KayitOlLink", "type": "xpath", "value": "//a[contains(., 'Kayıt') or contains(., 'Register')]",
                 "alternatives": [{"type": "css", "value": "a[href*='register']"}]},
                {"key": "HataMessaji", "type": "css", "value": ".error-message",
                 "alternatives": [
                     {"type": "xpath", "value": "//*[contains(@class, 'error')]"},
                     {"type": "css", "value": "[role='alert']"},
                 ]},
                {"key": "BasariliMesaji", "type": "css", "value": ".success-message",
                 "alternatives": [{"type": "xpath", "value": "//*[contains(@class, 'success')]"}]},
            ]}
        return {"locators": [
            {"key": "AnaBaslik", "type": "css", "value": "h1",
             "alternatives": [{"type": "xpath", "value": "//h1"}]},
            {"key": "NavMenu", "type": "css", "value": "nav",
             "alternatives": [{"type": "xpath", "value": "//nav"}, {"type": "css", "value": "header nav"}]},
            {"key": "LogoLink", "type": "css", "value": "header a[href='/']",
             "alternatives": [{"type": "xpath", "value": "//header//a[@href='/']"}, {"type": "css", "value": ".logo"}]},
            {"key": "AramaInput", "type": "css", "value": "input[type='search']",
             "alternatives": [
                 {"type": "xpath", "value": "//input[@type='search' or @name='q' or @placeholder[contains(., 'ara')]]"},
                 {"type": "name", "value": "q"},
             ]},
            {"key": "AramaButon", "type": "css", "value": "button[type='submit']",
             "alternatives": [{"type": "xpath", "value": "//button[contains(., 'Ara') or @aria-label='Ara']"}]},
            {"key": "FormInput", "type": "css", "value": "input[type='text']",
             "alternatives": [{"type": "xpath", "value": "//input[@type='text']"}]},
            {"key": "EmailInput", "type": "css", "value": "input[type='email']",
             "alternatives": [
                 {"type": "xpath", "value": "//input[@type='email' or @name='email']"},
                 {"type": "name", "value": "email"},
             ]},
            {"key": "TelefonInput", "type": "css", "value": "input[type='tel']",
             "alternatives": [{"type": "xpath", "value": "//input[@type='tel' or contains(@name,'phone')]"}]},
            {"key": "GonderButon", "type": "css", "value": "button[type='submit']",
             "alternatives": [
                 {"type": "xpath", "value": "//button[@type='submit']"},
                 {"type": "xpath", "value": "//button[contains(., 'Gönder') or contains(., 'Submit')]"},
             ]},
            {"key": "IptalButon", "type": "xpath", "value": "//button[contains(., 'İptal') or contains(., 'Cancel')]",
             "alternatives": [{"type": "css", "value": "button.cancel"}]},
            {"key": "KapatButon", "type": "xpath", "value": "//button[@aria-label='Kapat' or @aria-label='Close']",
             "alternatives": [{"type": "css", "value": "button.close"}]},
            {"key": "MenuAcButon", "type": "css", "value": "button[aria-label='Menu']",
             "alternatives": [{"type": "xpath", "value": "//button[@aria-label='Menu' or contains(@class,'menu-toggle')]"}]},
            {"key": "KullaniciMenusu", "type": "css", "value": "[aria-label='User menu']",
             "alternatives": [{"type": "xpath", "value": "//*[@data-testid='user-menu' or @aria-label='User menu']"}]},
            {"key": "FooterLinkleri", "type": "css", "value": "footer a",
             "alternatives": [{"type": "xpath", "value": "//footer//a"}]},
        ]}


@router.post("/projects/{project_id}/wizard/match-locators")
def wizard_match_locators(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Kayıtlı senaryo adımlarını crawl'lı lokator listesiyle eşleştirir.

    İstek gövdesi::

        {
          "scenario_ids": ["..."] | null,   # null → projenin tüm senaryoları
          "locators": [ {key, type, value, alternatives?: [...]} ]
        }

    Dönüş::

        {
          "matches": [
            {
              "scenario_id": "...",
              "scenario_title": "...",
              "step_index": 0,
              "step_text": "...",
              "element_phrase": "Kullanıcı adı alanı",
              "suggested_key": "KullaniciAdiInput",
              "suggested_locator": {"type": "name", "value": "username"},
              "confidence": 0.88,
              "reason": "..."
            }
          ],
          "unmatched_keys": ["..."],
          "scenario_count": 3
        }
    """
    _get_project(db, project_id, user)
    scenario_ids = body.get("scenario_ids") or None
    locators_raw = body.get("locators") or []
    if not isinstance(locators_raw, list) or not locators_raw:
        raise HTTPException(400, "locators listesi zorunlu")

    # Senaryoları DB'den çek
    stmt = select(TspmScenario).where(TspmScenario.project_id == project_id)
    if scenario_ids and isinstance(scenario_ids, list):
        stmt = stmt.where(TspmScenario.id.in_(scenario_ids))
    stmt = stmt.order_by(TspmScenario.created_at.desc()).limit(50)
    scenarios = list(db.scalars(stmt))
    if not scenarios:
        return {
            "matches": [],
            "unmatched_keys": [l.get("key", "") for l in locators_raw if isinstance(l, dict)],
            "scenario_count": 0,
            "llm_status": {"available": False, "match_count": 0, "error": None},
            "stats": {"steps_considered": 0, "skipped_url_only": 0},
        }

    # AI input hazırlığı — adımları kompakt bir liste olarak ver
    # Locator gerektirmeyen "open" tarzı adımları (URL'ye git, sayfa aç...) filtrele;
    # aksi halde "www, google, com" gibi generic URL token'ları yanlış eşleşme üretir.
    import re as _re_open  # noqa: PLC0415 — yerel kullanım
    _URL_OR_OPEN_HINTS = _re_open.compile(
        r"(https?://|www\.[a-z0-9.-]+|\b(?:adres|url|link|sayfa|page|site)\s*(?:ine|\b)\s*(?:gir|git|\u00e7\u0131k|a\u00e7))",
        _re_open.IGNORECASE,
    )

    def _step_needs_locator(text: str) -> bool:
        # Aksiyon metninde UI element ifadesi yok, sadece URL/navigasyon varsa skip
        if _URL_OR_OPEN_HINTS.search(text):
            # UI element kelimeleri varsa yine de dahil et (örn: "google.com'a gir ve arama kutusuna yaz")
            ui_hints = _re_open.search(
                r"\b(buton|button|tu\u015f|alan|kutu|input|link|menu|men\u00fc|ba\u015fl\u0131k|title|checkbox|radio|ba\u011flant\u0131|label)\b",
                text,
                _re_open.IGNORECASE,
            )
            if not ui_hints:
                return False
        return True

    steps_payload: list[dict] = []
    skipped_url_only = 0
    for sc in scenarios:
        for i, st in enumerate(sc.steps or []):
            if not isinstance(st, dict):
                continue
            text = (st.get("text") or st.get("action") or "").strip()
            if not text:
                continue
            if not _step_needs_locator(text):
                skipped_url_only += 1
                continue
            steps_payload.append({
                "scenario_id": sc.id,
                "scenario_title": sc.title,
                "step_index": i,
                "step_text": text[:400],
            })

    # Lokator listesini sadeleştir
    locators_compact = []
    for l in locators_raw:
        if not isinstance(l, dict):
            continue
        locators_compact.append({
            "key": l.get("key", ""),
            "type": l.get("type", ""),
            "value": l.get("value", ""),
        })

    matches: list[dict] = []
    used_keys: set[str] = set()
    llm_status: dict = {"available": False, "match_count": 0, "error": None}

    # 1) AI ile semantik eşleştirme dene
    try:
        from app.domains.ai.service import call_llm
        import json as _json
        system = (
            "Sen bir QA otomasyon asistanısın. Kullanıcı manuel test adımlarından "
            "UI element referanslarını çıkarır ve bunları Selenium/Playwright lokator "
            "listesindeki en uygun key ile eşleştirirsin. Yalnızca JSON döndür."
        )
        user_prompt = {
            "locators": locators_compact[:40],
            "steps": steps_payload[:60],  # prompt boyutunu küçült → hız artışı
            "instructions": (
                "Her adım için içindeki interaktif element ifadelerini (buton, alan, link vb.) "
                "bul ve locators listesinden en uygun 'key'i seç. Emin değilsen 'confidence'ı düşür. "
                "Adımda element yoksa atla."
            ),
            "schema": {
                "matches": [
                    {
                        "scenario_id": "string",
                        "scenario_title": "string",
                        "step_index": "int",
                        "step_text": "string",
                        "element_phrase": "string — adımda geçen element ifadesi",
                        "suggested_key": "string — locators listesindeki key",
                        "confidence": "0.0-1.0 arası float",
                        "reason": "string — kısa gerekçe",
                    }
                ]
            },
        }
        raw = call_llm(
            system,
            "Girdi JSON:\n" + _json.dumps(user_prompt, ensure_ascii=False, indent=2) +
            "\n\nYalnızca şu formatta JSON döndür:\n"
            '{"matches": [{"scenario_id":"...", "scenario_title":"...", "step_index":0, '
            '"step_text":"...", "element_phrase":"...", "suggested_key":"...", '
            '"confidence":0.9, "reason":"..."}]}',
            json_mode=True,
        )
        parsed = _json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(parsed, dict):
            ai_matches = parsed.get("matches", [])
            if isinstance(ai_matches, list):
                # Lokator key -> (type,value) map
                loc_map = {l["key"]: l for l in locators_compact if l.get("key")}
                seen_triples: set[tuple[str, int, str]] = set()
                for m in ai_matches:
                    if not isinstance(m, dict):
                        continue
                    k = m.get("suggested_key")
                    if not k or k not in loc_map:
                        continue
                    # Aynı (scenario, step, key) üçlüsünü ikinci kez üretme
                    triple = (str(m.get("scenario_id", "")), int(m.get("step_index", 0)), k)
                    if triple in seen_triples:
                        continue
                    seen_triples.add(triple)
                    loc = loc_map[k]
                    ltype = loc.get("type", "")
                    lvalue = loc.get("value", "")
                    xq = _score_xpath(lvalue) if ltype == "xpath" and lvalue else None
                    matches.append({
                        "scenario_id": m.get("scenario_id", ""),
                        "scenario_title": m.get("scenario_title", ""),
                        "step_index": int(m.get("step_index", 0)),
                        "step_text": m.get("step_text", ""),
                        "element_phrase": m.get("element_phrase", ""),
                        "suggested_key": k,
                        "suggested_locator": {"type": ltype, "value": lvalue},
                        "xpath_quality": xq,
                        "confidence": float(m.get("confidence", 0.5) or 0.5),
                        "reason": m.get("reason", ""),
                        "source": "llm",
                    })
                    used_keys.add(k)
                llm_status["available"] = True
                llm_status["match_count"] = len(matches)
    except Exception as exc:  # noqa: BLE001 — AI erişilemezse heuristic'e düşeriz
        llm_status["error"] = f"{type(exc).__name__}: {exc}"
        logger.warning(
            "wizard_match_locators: LLM eşleştirme başarısız, heuristic'e düşülüyor (%s)",
            llm_status["error"],
        )

    # 2) Heuristic fallback — AI hiç eşleşme üretmediyse basit anahtar kelime ile dene
    if not matches:
        import re as _re

        # Ultra-jenerik token'lar — eşleşme sayılırsa bile skora katkısı düşük olsun
        _GENERIC_TOKENS = {
            "www", "com", "net", "org", "http", "https",
            "page", "site", "app", "web",
            "google", "facebook", "twitter", "linkedin",  # platform adları — çok geneldir
        }

        # Türkçe-İngilizce eş anlamlılar — PascalCase split ile birlikte kullanılır
        _SYN = {
            "input": {"alan", "alani", "alanına", "kutusu", "kutu", "textbox", "field"},
            "button": {"buton", "butona", "buttonu", "buttonuna", "tuş", "tus", "tik", "tıkla"},
            "link": {"link", "bağlantı", "baglanti"},
            "sifre": {"sifre", "şifre", "password", "parola"},
            "kullanici": {"kullanici", "kullanıcı", "username", "user"},
            "giris": {"giris", "giriş", "login", "giriş"},
            "arama": {"arama", "ara", "search", "aramaya"},
            "ana": {"ana", "main", "anasayfa"},
            "baslik": {"baslik", "başlık", "title", "heading"},
            "gonder": {"gonder", "gönder", "submit", "send"},
            "iptal": {"iptal", "cancel"},
            "kapat": {"kapat", "kapatma", "close"},
            "menu": {"menu", "menü"},
            "email": {"email", "eposta", "e-posta", "mail"},
            "telefon": {"telefon", "phone", "tel"},
            "hata": {"hata", "error"},
            "basarili": {"basarili", "başarılı", "success", "basari"},
        }

        def _norm(s: str) -> str:
            return (
                s.lower()
                .replace("ı", "i").replace("İ", "i")
                .replace("ş", "s").replace("Ş", "s")
                .replace("ğ", "g").replace("Ğ", "g")
                .replace("ü", "u").replace("Ü", "u")
                .replace("ö", "o").replace("Ö", "o")
                .replace("ç", "c").replace("Ç", "c")
            )

        def _step_words(s: str) -> set[str]:
            base = set(_re.findall(r"[a-zçğıöşüA-ZÇĞİÖŞÜ]{3,}", s.lower()))
            return {_norm(w) for w in base}

        def _key_tokens(key: str) -> set[str]:
            # PascalCase → kelimelere böl: "KullaniciAdiInput" -> ["Kullanici", "Adi", "Input"]
            parts = _re.findall(r"[A-Z][a-z]+|[a-z]+", key)
            out: set[str] = set()
            for p in parts:
                pn = _norm(p)
                if len(pn) < 3:
                    continue
                out.add(pn)
                # eş anlamlıları ekle
                for canon, syns in _SYN.items():
                    if pn == canon or pn in syns:
                        out.add(canon)
                        out.update(syns)
            return out

        def _weighted_overlap(key_words: set[str], step_words: set[str]) -> tuple[float, int, list[str]]:
            """Kesişen token sayısı yerine generic-token cezalı ağırlıklı skor.

            - generic kelime (google, www, com...) = 0.4 puan
            - normal kelime = 1.0 puan
            Dönüş: (weighted_score, raw_match_count, matched_tokens)
            """
            matched = sorted(key_words & step_words)
            if not matched:
                return 0.0, 0, []
            score = 0.0
            for tok in matched:
                score += 0.4 if tok in _GENERIC_TOKENS else 1.0
            return score, len(matched), matched

        step_tokens = [(sp, _step_words(sp["step_text"])) for sp in steps_payload]
        for loc in locators_compact:
            key_words = _key_tokens(loc["key"])
            if not key_words:
                continue
            best = None
            best_weighted = 0.0
            best_raw = 0
            best_matched: list[str] = []
            for sp, tokens in step_tokens:
                weighted, raw, matched = _weighted_overlap(key_words, tokens)
                if weighted > best_weighted:
                    best_weighted = weighted
                    best_raw = raw
                    best_matched = matched
                    best = sp
            if best and best_weighted > 0:
                # confidence = 0.35 + 0.12 * ağırlıklı_skor, tavan 0.78
                # Sadece generic eşleşme → en fazla 0.35 + 0.12*0.4 ≈ 0.40 (çok düşük, kullanıcıya "AI kapalı, zayıf eşleşme" sinyali)
                # Anlamlı tek kelime → 0.35 + 0.12 = 0.47
                # İki anlamlı kelime → 0.59, üç → 0.71
                conf = min(0.35 + 0.12 * best_weighted, 0.78)
                matched_preview = ", ".join(best_matched[:4])
                xq = _score_xpath(loc["value"]) if loc["type"] == "xpath" and loc["value"] else None
                matches.append({
                    "scenario_id": best["scenario_id"],
                    "scenario_title": best["scenario_title"],
                    "step_index": best["step_index"],
                    "step_text": best["step_text"],
                    "element_phrase": best["step_text"][:80],
                    "suggested_key": loc["key"],
                    "suggested_locator": {"type": loc["type"], "value": loc["value"]},
                    "xpath_quality": xq,
                    "confidence": round(conf, 3),
                    "reason": f"Anahtar kelime eşleşmesi ({best_raw}): {matched_preview}",
                    "source": "heuristic",
                })
                used_keys.add(loc["key"])

    unmatched = [l["key"] for l in locators_compact if l["key"] and l["key"] not in used_keys]
    return {
        "matches": matches,
        "unmatched_keys": unmatched,
        "scenario_count": len(scenarios),
        "llm_status": llm_status,
        "stats": {
            "steps_considered": len(steps_payload),
            "skipped_url_only": skipped_url_only,
        },
    }


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


@router.post("/projects/{project_id}/monkey-testing/probe")
def monkey_testing_probe(project_id: str, body: dict, db: DB, user: CurrentUser):
    """Hedef URL'i (ve opsiyonel login URL'ini) hızlıca probe eder.
    Kullanıcı 'Başlat' demeden önce hedefin erişilebilir ve makul olduğunu
    görebilsin diye full Playwright run yerine httpx HEAD/GET kullanır.
    """
    _get_project(db, project_id, user)

    def _probe(url: str) -> dict:
        url = (url or "").strip()
        if not url:
            return {"ok": False, "skipped": True, "reason": "URL boş"}
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        try:
            t0 = datetime.now()
            with httpx.Client(
                follow_redirects=True,
                timeout=8.0,
                headers={"User-Agent": "Mozilla/5.0 NeurexQA/Probe"},
            ) as client:
                resp = client.get(url)
            elapsed = int((datetime.now() - t0).total_seconds() * 1000)
            content_type = resp.headers.get("content-type", "")
            return {
                "ok": resp.status_code < 400,
                "status": resp.status_code,
                "final_url": str(resp.url),
                "elapsed_ms": elapsed,
                "content_type": content_type,
                "body_size": len(resp.content),
                "redirected": str(resp.url) != url,
            }
        except httpx.ConnectTimeout:
            return {"ok": False, "error": "timeout", "reason": "Site 8 saniye içinde yanıt vermedi"}
        except httpx.ConnectError as exc:
            return {"ok": False, "error": "connect", "reason": f"Bağlantı kurulamadı: {str(exc)[:120]}"}
        except httpx.HTTPError as exc:
            return {"ok": False, "error": "http", "reason": f"HTTP hatası: {str(exc)[:120]}"}
        except Exception as exc:
            return {"ok": False, "error": "unknown", "reason": str(exc)[:200]}

    target_url = body.get("url", "")
    login_url = body.get("login_url", "")
    return {
        "target": _probe(target_url),
        "login":  _probe(login_url) if login_url else {"ok": True, "skipped": True, "reason": "Login URL belirtilmedi"},
    }


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
            headers={"Content-Disposition": "attachment; filename=\"özet-rapor.json\""},
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
        headers={"Content-Disposition": "attachment; filename=\"özet-rapor.html\""},
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
    user: Annotated[User, Depends(require_permission(Permission.EXECUTION_CREATE))],
):
    """
    Bir execution'ı gerçek Playwright headless modunda koştur.
    - Engine (port 5001) üzerinden pytest/playwright runner çalışır
    - Engine yoksa simülasyon modu devreye girer
    - SSE stream URL döner → frontend canlı olayları dinler
    """
    # Güvenlik kapısı: kullanıcı projeye üye mi? (admin.* ile bypass)
    _get_project(db, project_id, user)

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
        mode=body.mode,
    )

    stream_url = f"/api/v1/tspm/projects/{project_id}/executions/{execution_id}/stream/{run_id}"

    return RunExecutionResponse(
        execution_id=execution_id,
        run_id=run_id,
        status="started",
        stream_url=stream_url,
        mode=body.mode,
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


# ═══════════════════════════════════════════════════════════════════════════════
# Monkey Testing — SSE Proxy Endpoints
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/monkey-testing/run/stream",
    summary="Monkey Testing: SSE gerçek zamanlı akış",
)
async def monkey_run_stream(
    project_id: str,
    request: Request,
    db: DB,
    user: Annotated[Optional[User], Depends(get_optional_user)] = None,
    token: Optional[str] = Query(None),
):
    """
    Engine'deki /api/monkey-testing/run/stream SSE endpoint'ini proxy'ler.
    Frontend'den POST body olarak { url, max_actions, credentials, config, record_video } alır.
    """
    resolved_user = user or _resolve_query_token_user(db, token)
    if resolved_user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Kimlik doğrulama gerekli")

    _get_project(db, project_id, resolved_user)

    body = await request.json()

    async def _stream():
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream(
                    "POST",
                    f"{ENGINE_BASE_URL}/api/monkey-testing/run/stream",
                    json=body,
                    headers={"X-Internal-Key": _ENGINE_KEY, "Content-Type": "application/json"},
                ) as resp:
                    async for chunk in resp.aiter_bytes(chunk_size=4096):
                        yield chunk
        except httpx.ConnectError:
            import json as _json
            err = _json.dumps({"error": "Engine bağlantı hatası. Port 5001'i kontrol edin."})
            yield f"event: fail\ndata: {err}\n\n".encode()

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post(
    "/projects/{project_id}/monkey-testing/run",
    summary="Monkey Testing: Senkron tek sonuç",
)
async def monkey_run_sync(
    project_id: str,
    request: Request,
    db: DB,
    user: CurrentUser,
):
    _get_project(db, project_id, user)
    body = await request.json()
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            resp = await client.post(
                f"{ENGINE_BASE_URL}/api/monkey-testing/run",
                json=body,
                headers=_IKEY,
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="application/json")
    except httpx.ConnectError:
        raise HTTPException(503, "Engine bağlantı hatası. Port 5001'i kontrol edin.")


@router.get(
    "/projects/{project_id}/monkey-testing/video/{run_id}",
    summary="Monkey Testing: Video serve",
)
async def monkey_video(
    project_id: str,
    run_id: str,
    db: DB,
    user: CurrentUser,
):
    _get_project(db, project_id, user)
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{ENGINE_BASE_URL}/api/monkey-testing/video/{run_id}",
                headers=_IKEY,
            )
            return Response(content=resp.content, status_code=resp.status_code, media_type="video/webm")
    except httpx.ConnectError:
        raise HTTPException(503, "Engine bağlantı hatası.")


# ═══════════════════════════════════════════════════════════════════════════════
# LLM Agent — ReAct-style browser ajanı (SSE streaming)
# ═══════════════════════════════════════════════════════════════════════════════

@router.post(
    "/projects/{project_id}/llm-agent/run/stream",
    summary="LLM Agent: Gelişmiş ReAct tabanlı tarayıcı ajanı (SSE akışı)",
)
async def llm_agent_run_stream(
    project_id: str,
    request: Request,
    db: DB,
    user: CurrentUser,
):
    """
    Gelişmiş ReAct döngüsü — 5 aşamalı derin plan ve hipotez takibi.

    Faz 1: Tarayıcı oturumu + DOM keşfi
    Faz 2: Sayfa kavrama (streaming)
    Faz 3: Risk analizi + hipotez üretimi (streaming)
    Faz 4: Hipotez bazlı adaptif ReAct döngüsü (streaming)
    Faz 5: Executive özet (streaming)

    SSE olayları:
      agent_start, agent_discovery,
      agent_comprehension_token, agent_comprehension,
      agent_plan_token, agent_plan,
      agent_hypothesis_start, agent_thinking (token), agent_action,
      agent_screenshot, agent_navigate,
      agent_observation (token), agent_finding, agent_hypothesis_result,
      agent_summarizing, agent_summary_token, agent_summary,
      agent_error, agent_done
    """
    import json as _json
    import re as _re

    _get_project(db, project_id, user)

    body = await request.json()
    target_url: str = (body.get("url") or "").strip()
    max_steps: int = min(int(body.get("max_steps", 10)), 20)
    credentials = body.get("credentials")
    test_focus: str = (body.get("test_focus") or "").strip()
    # dry_run=True → FAZ 1-3 çalışır (browser aç, DOM keşfet, hipotez üret),
    # FAZ 4 (aksiyon yürütme) ve FAZ 5 (özet) ATLANIR. Browser kapatılır.
    # Kullanıcı hipotez planını önizler, tam çalıştırma yapmadan maliyet/süre sıfır.
    dry_run: bool = bool(body.get("dry_run", False))
    # Önceki çalışma session_id'si — engine'e iletilirse browser context yeniden kullanılır.
    reuse_session_id: str | None = (body.get("reuse_session_id") or None)

    if not target_url:
        async def _err():
            yield f"event: agent_error\ndata: {_json.dumps({'error': 'URL gereklidir'})}\n\n"
        return StreamingResponse(_err(), media_type="text/event-stream")

    if not target_url.startswith(("http://", "https://")):
        target_url = "https://" + target_url

    # ── Gateway streaming config ──────────────────────────────────────────────
    _GW_BASE = (
        os.environ.get("AI_GATEWAY_BASE_URL") or settings.ai_gateway_base_url
    ).rstrip("/")
    _GW_KEY = os.environ.get("GATEWAY_INTERNAL_KEY") or settings.gateway_internal_key
    _GW_HEADERS = {"Content-Type": "application/json", "X-Internal-Key": _GW_KEY}

    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def _gw_payload(
        system_msg: str,
        user_msg: str,
        max_tok: int = 900,
        temp: float = 0.5,
        task_type: str = "chat",
    ) -> dict:
        return {
            "task_type": task_type,
            "messages": [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            "temperature": temp,
            "max_tokens": max_tok,
        }

    def _parse_json_block(text: str) -> dict | list | None:
        """JSON bloğu bul ve parse et."""
        fence = _re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, _re.DOTALL)
        raw = fence.group(1) if fence else text
        for start_c, end_c in [("{", "}"), ("[", "]")]:
            s = raw.find(start_c)
            e = raw.rfind(end_c)
            if s != -1 and e > s:
                try:
                    return _json.loads(raw[s:e + 1])
                except Exception:
                    pass
        return None

    def _gw_complete_json(
        gw_complete_fn,
        *,
        task_type: str,
        system_message: str,
        user_message: str,
        temperature: float = 0.3,
        max_tokens: int = 400,
        retries: int = 1,
        default: dict | list | None = None,
    ):
        """`_gw_complete` çağır ve JSON parse et; başarısızsa kısaltılmış
        prompt ile yeniden dene. Hâlâ başarısızsa `default` döndür.

        Bu sarmalayıcı LLM bazen `{...} açıklama metni` veya kod fence'leri
        eklediğinde pipeline'ın crash etmesini engeller.
        """
        attempts = []
        for attempt in range(retries + 1):
            try:
                raw = gw_complete_fn(
                    task_type=task_type,
                    system_message=system_message,
                    user_message=user_message,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            except Exception as exc:  # noqa: BLE001
                attempts.append(f"call_err: {exc}")
                continue
            parsed = _parse_json_block(raw)
            if parsed is not None:
                return parsed
            attempts.append(f"parse_fail: {raw[:80]!r}")
            # Retry: agresif olarak "sadece JSON" iste
            user_message = (
                "ÖNCEKİ CEVAP GEÇERSİZ JSON İÇERİYORDU. "
                "Lütfen SADECE geçerli JSON döndür, başka hiçbir metin/açıklama/markdown ekleme.\n"
                f"İstek: {user_message[:300]}"
            )
            temperature = max(0.1, temperature - 0.2)
        logger.warning("_gw_complete_json tüm denemeler başarısız: %s", attempts)
        return default if default is not None else {}

    def _format_dom_context(dom: dict) -> str:
        """DOM verisini LLM için okunabilir metin formatına çevir."""
        lines = [
            f"Sayfa Tipi: {dom.get('page_type', 'bilinmiyor')}",
            f"URL: {dom.get('url', '')}",
            f"Başlık: {dom.get('title', '')}",
        ]
        if dom.get("headings"):
            lines.append("Başlıklar: " + " | ".join(
                h.get("text", "") for h in dom["headings"][:5]
            ))
        if dom.get("buttons"):
            btns = [b.get("text", b.get("selector", "")) for b in dom["buttons"][:8] if b.get("text")]
            if btns:
                lines.append("Butonlar: " + ", ".join(btns))
        if dom.get("inputs"):
            inps = []
            for inp in dom["inputs"][:6]:
                desc = inp.get("label") or inp.get("placeholder") or inp.get("name") or inp.get("type", "")
                if desc:
                    inps.append(f"{inp.get('type', 'input')}[{desc}]")
            if inps:
                lines.append("Girdi alanları: " + ", ".join(inps))
        if dom.get("nav_links"):
            navs = [n.get("text", "") for n in dom["nav_links"][:6] if n.get("text")]
            if navs:
                lines.append("Navigasyon: " + " | ".join(navs))
        if dom.get("alerts"):
            alerts = [a.get("text", "")[:80] for a in dom["alerts"][:3]]
            if alerts:
                lines.append("Uyarı/Hata mesajları: " + " | ".join(alerts))
        if dom.get("text_excerpt"):
            lines.append("Sayfa içeriği (özet): " + dom["text_excerpt"][:500])
        # Hard cap: LLM token bütçesini korumak için (Ollama 8k context window)
        result = "\n".join(lines)
        return result if len(result) < 2500 else result[:2500] + "\n…(kırpıldı)"

    def _format_elements_for_action(dom: dict) -> str:
        """Aksiyon seçimi için element listesi üret."""
        lines = []
        if dom.get("buttons"):
            for b in dom["buttons"][:10]:
                lines.append(f'  BUTON: text="{b.get("text","")[:60]}" selector="{b.get("selector","")[:80]}"')
        if dom.get("inputs"):
            for i in dom["inputs"][:10]:
                label = i.get("label") or i.get("placeholder") or i.get("name") or ""
                lines.append(f'  INPUT: type={i.get("type","")} label="{label[:60]}" selector="{i.get("selector","")[:80]}"')
        if dom.get("nav_links"):
            for n in dom["nav_links"][:6]:
                lines.append(f'  LINK: text="{n.get("text","")[:60]}" selector="{n.get("selector","")[:80]}"')
        result = "\n".join(lines) if lines else "  (element bulunamadı)"
        # Hard cap
        return result if len(result) < 1800 else result[:1800] + "\n  …(kırpıldı)"

    def _parse_hypotheses(text: str) -> list[dict]:
        """Hipotez listesini LLM çıktısından parse et."""
        parsed = _parse_json_block(text)
        if isinstance(parsed, list):
            # max_steps = Playwright aksiyon başına adım sayısı — hipotez sayısını
            # kısıtlamamalı. LLM 5 üretirse 5'i al; cap=10 (wave-2 dahil için).
            return [
                {
                    "id": h.get("id", f"H{i+1}"),
                    "claim": h.get("claim", h.get("description", "")),
                    "area": h.get("area", "genel"),
                    "priority": h.get("priority", "medium"),
                    "actions_hint": h.get("actions_hint", ""),
                }
                for i, h in enumerate(parsed[:10])
                if h.get("claim") or h.get("description")
            ]
        # Fallback: numbered list parse
        hyps = []
        for i, line in enumerate(_re.split(r"\n\d+[\.\)]\s+", text)[1:], 1):
            claim = line.strip().split("\n")[0].strip("*•-").strip()
            if claim and len(claim) > 10:
                hyps.append({"id": f"H{i}", "claim": claim, "area": "genel", "priority": "medium", "actions_hint": ""})
        if not hyps:
            # Son çare: çeşitlilik garantisi için sayfa tipine göre 3 default hipotez
            _DEFAULT_HYPS = [
                {"id": "H1", "claim": "Sayfanın temel işlevselliğini test et",
                 "area": "ux", "priority": "high", "actions_hint": "Sayfa elementleriyle etkileşim kur"},
                {"id": "H2", "claim": "Form/giriş alanları validasyon kurallarını uyguluyor",
                 "area": "form", "priority": "medium", "actions_hint": "Boş ve geçersiz değerlerle submit dene"},
                {"id": "H3", "claim": "Navigasyon ve link akışları beklendiği gibi çalışıyor",
                 "area": "navigation", "priority": "medium", "actions_hint": "Görünür linklere tıklayıp URL'yi izle"},
            ]
            return _DEFAULT_HYPS  # 3 çeşit fallback her zaman döner
        return hyps[:10]  # numbered-list parse fallback; max_steps hipotez sayısını kısıtlamaz

    async def _generate():
        start_time = __import__("time").time()
        session_id: str | None = None
        findings: list = []
        hypotheses: list = []
        hyp_results: list = []
        history: list[str] = []

        try:
            # ══ FAZ 1: Browser oturumu + DOM keşfi ══════════════════════════
            # Playwright başlatma + ilk sayfa navigasyonu 40s'ye kadar sürebilir;
            # backend timeout engine worker timeout'undan (40s) daha büyük olmalı.
            _start_payload: dict = {"url": target_url, "credentials": credentials}
            if reuse_session_id:
                _start_payload["reuse_session_id"] = reuse_session_id
            async with httpx.AsyncClient(timeout=55) as client:
                start_resp = await client.post(
                    f"{ENGINE_BASE_URL}/api/llm-agent/start",
                    json=_start_payload,
                    headers=_IKEY,
                )
            if start_resp.status_code != 200:
                yield _sse("agent_error", {"error": f"Engine oturum başlatılamadı: {start_resp.text[:200]}"})
                return

            start_data = start_resp.json()
            session_id = start_data["session_id"]
            screenshot_b64 = start_data.get("screenshot_b64", "")
            page_info = start_data.get("page_info", {})
            current_url = page_info.get("url", target_url)

            yield _sse("agent_start", {
                "session_id": session_id,
                "url": current_url,
                "screenshot_b64": screenshot_b64,
                "page_info": page_info,
                "reused": bool(start_data.get("reused", False)),
            })

            # DOM derin analizi
            async with httpx.AsyncClient(timeout=15) as client:
                dom_resp = await client.get(
                    f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/dom",
                    headers=_IKEY,
                )
            dom = dom_resp.json() if dom_resp.status_code == 200 else {}
            dom_context = _format_dom_context(dom)

            # Tech stack + performance from DOM
            tech_stack = dom.get("tech_stack", [])
            perf_data = dom.get("perf", {})

            # Initial network + storage fetch
            initial_network = []
            storage_data = {}
            initial_console = []
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    net_resp = await client.get(
                        f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/network",
                        headers=_IKEY,
                    )
                if net_resp.status_code == 200:
                    initial_network = net_resp.json().get("calls", [])
            except Exception:
                pass
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    stor_resp = await client.get(
                        f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/storage",
                        headers=_IKEY,
                    )
                if stor_resp.status_code == 200:
                    storage_data = stor_resp.json()
            except Exception:
                pass
            try:
                async with httpx.AsyncClient(timeout=8) as client:
                    con_resp = await client.get(
                        f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/console",
                        headers=_IKEY,
                    )
                if con_resp.status_code == 200:
                    initial_console = con_resp.json().get("messages", [])
            except Exception:
                pass

            yield _sse("agent_discovery", {
                "page_type": dom.get("page_type", "generic"),
                "buttons_count": len(dom.get("buttons", [])),
                "inputs_count": len(dom.get("inputs", [])),
                "links_count": len(dom.get("nav_links", [])),
                "forms_count": len(dom.get("forms", [])),
                "alerts": dom.get("alerts", []),
                "headings": dom.get("headings", []),
                "url": current_url,
            })

            if tech_stack:
                yield _sse("agent_tech_detected", {
                    "tech_stack": tech_stack,
                    "perf": perf_data,
                    "sensitive_storage_keys": storage_data.get("sensitive_keys_found", []),
                    "cookie_count": len(storage_data.get("cookies", [])),
                    "initial_api_calls": len(initial_network),
                    "initial_console_errors": len([m for m in initial_console if m.get("type") == "error"]),
                })

            # ══ FAZ 2: Sayfa Kavrama (Streamed) ═════════════════════════════
            COMPREHENSION_SYS = (
                "Sen kıdemli bir güvenlik odaklı QA mühendisisin. "
                "Sana bir web sayfasının DOM yapısı, teknoloji yığını ve performans verisi veriliyor. "
                "SADECE şunları içeren 3-5 cümlelik kısa analiz yaz:\n"
                "1. Sayfanın temel amacı ve kullanıcı akışları\n"
                "2. Kritik güvenlik test noktaları (auth/form/api)\n"
                "3. Olası zayıf noktalar (input validasyon, session, erişim kontrolü)\n"
                "Türkçe yaz, teknik ve öz ol."
            )
            focus_clause = f" Test odağı: {test_focus}." if test_focus else ""
            # Format tech stack for prompt
            _tech_names = ", ".join(t.get("name","") for t in tech_stack) if tech_stack else "bilinmiyor"
            _perf_str = (
                f"Sayfa yüklenme: {perf_data.get('load_ms',0)}ms, "
                f"TTFB: {perf_data.get('ttfb_ms',0)}ms"
            ) if perf_data else ""
            _sensitive_str = (
                f"Hassas storage anahtarları: {storage_data.get('sensitive_keys_found', [])}"
            ) if storage_data.get("sensitive_keys_found") else ""
            _initial_errs = [m.get("text","")[:60] for m in initial_console if m.get("type")=="error"][:3]

            comprehension_prompt = (
                f"Web sayfası analizi:{focus_clause}\n\n"
                f"Teknoloji yığını: {_tech_names}\n"
                + (f"Performans: {_perf_str}\n" if _perf_str else "")
                + (f"{_sensitive_str}\n" if _sensitive_str else "")
                + (f"Başlangıç console hataları: {_initial_errs}\n" if _initial_errs else "")
                + f"\n{dom_context}\n\n"
                "Bu sayfanın amacını, teknoloji altyapısını ve kritik güvenlik/test noktalarını özetle."
            )

            comprehension_text = ""
            try:
                async with asyncio.timeout(90):  # kavrama max 90s
                    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=30, write=10, pool=5)) as client:
                        async with client.stream(
                            "POST", f"{_GW_BASE}/ai/stream",
                            json=_gw_payload(COMPREHENSION_SYS, comprehension_prompt, max_tok=400, temp=0.4, task_type="llm_agent_think"),
                            headers=_GW_HEADERS,
                        ) as resp:
                            async for line in resp.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                raw = line[6:]
                                if raw == "[DONE]":
                                    break
                                try:
                                    tok = _json.loads(raw).get("token", "")
                                    if tok:
                                        comprehension_text += tok
                                        yield _sse("agent_comprehension_token", {"token": tok})
                                except Exception:
                                    pass
            except (Exception, asyncio.TimeoutError) as _comp_exc:
                # Kavrama fazı başarısız — DOM özetini kullan, devam et
                logger.warning("LLM Agent kavrama fazı hatası/timeout: %s — DOM özeti kullanılıyor", _comp_exc)
                comprehension_text = f"[Kavrama LLM hatası: {_comp_exc}] DOM özeti: {dom_context[:300]}"

            yield _sse("agent_comprehension", {"text": comprehension_text, "dom_summary": dom_context[:300]})

            # ══ FAZ 3: Risk Analizi + Hipotez Üretimi (Streamed) ════════════
            HYPOTHESIS_SYS = (
                "Sen kıdemli bir güvenlik odaklı QA stratejisti ve penetrasyon test uzmanısın. "
                "Bir web sayfasının yapısı, teknoloji yığını ve amacı veriliyor. "
                "Test hipotezleri listesi üretirsin — hem fonksiyonel hem güvenlik odaklı. "
                "Her hipotez şu formatta JSON dizisi:\n"
                '[\n'
                '  {"id": "H1", "claim": "Login formu SQL injection\'a karşı savunmasız", '
                '"area": "security", "priority": "critical", '
                '"actions_hint": "username alanına \' OR 1=1-- gir, submit et, yanıtı gözlemle", '
                '"test_type": "security"},\n'
                '  {"id": "H2", "claim": "Boş form gönderimi düzgün valide ediliyor", '
                '"area": "form", "priority": "high", '
                '"actions_hint": "tüm alanları boş bırak, submit et", '
                '"test_type": "functional"},\n'
                '  ...\n'
                ']\n'
                "ZORUNLU KISITLAR:\n"
                "• TAM OLARAK 5 hipotez üret — daha az veya daha fazla KABUL EDİLMEZ.\n"
                "• Her hipotez FARKLI bir area'yı kapsamalı.\n"
                "• area DEĞERİ MUTLAKA bu setten biri olmalı (İngilizce, küçük harf):\n"
                "  auth | form | navigation | api | security | performance | accessibility | ux\n"
                "  (genel/generic/other GİBİ değerler KABUL EDİLMEZ — uygun olanı seç)\n"
                "• priority DEĞERİ MUTLAKA: critical | high | medium | low\n"
                "• test_type DEĞERİ MUTLAKA: security | functional | performance | accessibility | ux\n"
                "Güvenlik hipotezleri için: XSS, SQLi, CSRF, IDOR, auth bypass, open redirect, "
                "sensitive data exposure, broken access control testlerini düşün.\n"
                "SADECE JSON dizisi döndür. Açıklama, markdown, başlık YAZMA."
            )

            _sec_hints = []
            if dom.get("page_type") == "auth":
                _sec_hints = ["SQL injection login bypass", "brute force koruması", "şifre sıfırlama akışı", "oturum yönetimi"]
            elif dom.get("page_type") == "form":
                _sec_hints = ["XSS form injection", "CSRF koruması", "dosya yükleme güvenliği", "input validasyonu"]
            elif dom.get("page_type") == "list_table":
                _sec_hints = ["IDOR (başka kullanıcının verisi)", "veri filtreleme bypass", "toplu silme güvenliği"]
            elif dom.get("page_type") == "dashboard":
                _sec_hints = ["unauthorized access", "API endpoint güvenliği", "veri sızıntısı"]

            _network_ctx = ""
            if initial_network:
                _api_urls = list(set(c["url"].split("?")[0][-60:] for c in initial_network[:10]))
                _network_ctx = f"Tespit edilen API endpoint'leri: {_api_urls}\n"

            # Comprehension metnini kısalt: hipotez planı için 400 karakter yeterli,
            # fazlası max_tok bütçesini tüketir ve daha az hipotez üretilmesine yol açar.
            _compr_short = comprehension_text[:400] if comprehension_text else "(bilgi yok)"
            hyp_prompt = (
                f"Sayfa tipi: {dom.get('page_type', 'generic')} | Teknoloji: {_tech_names}\n"
                f"DOM özeti:\n{dom_context[:800]}\n"
                f"Sayfa kavraması: {_compr_short}\n"
                + (f"Test odağı: {test_focus}\n" if test_focus else "")
                + (_network_ctx if _network_ctx else "")
                + (f"Güvenlik ipuçları: {', '.join(_sec_hints)}\n" if _sec_hints else "")
                + "\nTAM OLARAK 5 adet test hipotezi üret. "
                "Her biri farklı bir area (auth/form/navigation/security/ux/api/performance) kapsamalı. "
                "SADECE JSON dizisi döndür, başka hiçbir şey yazma:\n"
                '[{"id":"H1","claim":"...","area":"security","priority":"high","actions_hint":"...","test_type":"security"},'
                '{"id":"H2","claim":"...","area":"form","priority":"medium","actions_hint":"...","test_type":"functional"},'
                "...5 adet...]"
            )

            hyp_raw = ""
            try:
                async with asyncio.timeout(150):  # hipotez planı max 150s (5 hipo × ~30s)
                    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=45, write=10, pool=5)) as client:
                        async with client.stream(
                            "POST", f"{_GW_BASE}/ai/stream",
                            # max_tok 800: 5 hipotez × ~140 token/hipotez = ~700 token + buffer
                            json=_gw_payload(HYPOTHESIS_SYS, hyp_prompt, max_tok=800, temp=0.3, task_type="llm_agent_plan"),
                            headers=_GW_HEADERS,
                        ) as resp:
                            async for line in resp.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                raw = line[6:]
                                if raw == "[DONE]":
                                    break
                                try:
                                    tok = _json.loads(raw).get("token", "")
                                    if tok:
                                        hyp_raw += tok
                                        yield _sse("agent_plan_token", {"token": tok})
                                except Exception:
                                    pass
            except (Exception, asyncio.TimeoutError) as _hyp_exc:
                # LLM çağrısı tamamen başarısız → fallback hipotezlerle devam et
                logger.warning("LLM Agent hipotez üretim hatası/timeout: %s — default hipotezler kullanılıyor", _hyp_exc)
                hyp_raw = ""  # _parse_hypotheses fallback'e düşecek

            hypotheses = _parse_hypotheses(hyp_raw)
            # Görünürlük: LLM kaç hipotez döndürdü, hangi alanlar? (stderr, flush=True
            # — uvicorn logger handler yapılandırması garanti değil)
            import sys as _sys
            print(
                f"[LLM_AGENT] Hypothesis plan: count={len(hypotheses)} "
                f"areas={[h.get('area') for h in hypotheses]}",
                file=_sys.stderr,
                flush=True,
            )
            yield _sse("agent_plan", {
                "plan": hyp_raw,
                "hypotheses": hypotheses,
                "url": current_url,
            })

            # ── Dry-run erken çıkış ──────────────────────────────────────────
            # dry_run=True ise FAZ 4-5 atlanır; browser kapatılır, sadece plan döner.
            if dry_run:
                # Tarayıcı oturumunu kapat (pool sağlıklı kalsın)
                try:
                    async with httpx.AsyncClient(timeout=10) as _dc:
                        await _dc.post(
                            f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/close",
                            headers=_IKEY,
                        )
                except Exception:
                    pass
                total_elapsed = round(__import__("time").time() - start_time, 1)
                yield _sse("agent_done", {
                    "dry_run": True,
                    "hypotheses": hypotheses,
                    "hypothesis_count": len(hypotheses),
                    "url": current_url,
                    "elapsed_sec": total_elapsed,
                    "message": (
                        f"Dry-run tamamlandı: {len(hypotheses)} hipotez üretildi, "
                        "browser aksiyonu çalıştırılmadı."
                    ),
                })
                return

            # ══ FAZ 4: Hipotez Bazlı Adaptif ReAct Döngüsü ═════════════════
            # Çapraz hipotez öğrenme: working memory
            working_memory: dict = {
                "page_type": dom.get("page_type", "generic"),
                "confirmed_selectors": {},   # desc -> selector (çalıştığı kanıtlanan)
                "failed_selectors":    [],   # başarısız selectorlar
                "learned_facts":       [],   # hipotezlerden öğrenilen gerçekler
                "tested_flows":        [],   # test edilen akışlar
            }
            tested_areas: set[str] = set()
            # Alan adı normalizer: LLM Türkçe/varyant isim üretebilir;
            # coverage hesabı için İngilizce canonical isimle eşleştir.
            _AREA_MAP = {
                "genel": "ux", "generic": "ux", "other": "ux",
                "ui": "ux", "kullanıcı deneyimi": "ux", "kullanıcı": "ux",
                "işlevsellik": "ux", "functionality": "ux",
                "güvenlik": "security", "security": "security", "secure": "security",
                "kimlik": "auth", "authentication": "auth", "login": "auth",
                "giriş": "auth", "auth": "auth", "authorization": "auth",
                "navigasyon": "navigation", "navigation": "navigation", "routing": "navigation",
                "form": "form", "forms": "form", "validasyon": "form", "validation": "form",
                "api": "api", "network": "api", "rest": "api",
                "performans": "performance", "performance": "performance", "speed": "performance",
                "erişilebilirlik": "accessibility", "accessibility": "accessibility", "a11y": "accessibility",
            }
            def _norm_area(area: str) -> str:
                return _AREA_MAP.get(area.lower().strip(), area.lower().strip())

            from app.domains.ai.gateway_client import gateway_complete as _gw_complete

            async def _agw_complete_json(**kwargs):
                """_gw_complete_json'ı thread pool'da çalıştır — event loop'u bloke etmez.

                Argümanlar doğrudan _gw_complete_json'a (kwargs) iletilir.
                Bu sayede sequence plan / classify / wave2 gibi senkron LLM çağrıları
                event loop'u bloklayıp SSE akışını kesmez.
                """
                return await asyncio.to_thread(
                    lambda: _gw_complete_json(_gw_complete, **kwargs)
                )

            async def _agw_complete(**kwargs):
                """gateway_complete'yi thread pool'da çalıştır (non-streaming, sync)."""
                return await asyncio.to_thread(lambda: _gw_complete(**kwargs))

            # Hipotez sayısı max_steps ile kısıtlanmamalı; max_steps = her hipotez için
            # browser aksiyon bütçesi. Hipotez döngüsü kendi listesi kadar koşar (max 10).
            for hyp_idx, hyp in enumerate(hypotheses[:10]):
                hyp_id = hyp["id"]
                _hyp_start_time = __import__("time").time()
                yield _sse("agent_hypothesis_start", {
                    "hypothesis": hyp,
                    "index": hyp_idx,
                    "total": len(hypotheses),
                    "working_memory_facts": working_memory["learned_facts"][-3:],
                })

                # Fresh DOM + accessibility snapshot
                async with httpx.AsyncClient(timeout=12) as client:
                    dom_snap_resp = await client.get(
                        f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/dom",
                        headers=_IKEY,
                    )
                current_dom = dom_snap_resp.json() if dom_snap_resp.status_code == 200 else dom
                elements_text = _format_elements_for_action(current_dom)
                # Prompt trimming: history/memory/selector kayıtları LLM context'inde yer kapliyor.
                # Her satır 200 karakterle, total bloğu 800 karakterle sınırla → Ollama daha hızlı.
                _hist_lines = [h[:200] for h in history[-4:]] if history else ["İlk adım."]
                history_text = "\n".join(_hist_lines)
                if len(history_text) > 800:
                    history_text = history_text[-800:]
                _facts = [f[:150] for f in working_memory["learned_facts"][-4:]]
                memory_text = (
                    "Öğrenilen gerçekler: " + "; ".join(_facts)
                    if _facts else "Henüz bilgi yok."
                )
                if len(memory_text) > 600:
                    memory_text = memory_text[:600] + "…"
                _sels = [(k[:40], v[:80]) for k, v in list(working_memory["confirmed_selectors"].items())[-4:]]
                confirmed_sels = (
                    ", ".join(f"{k}={v}" for k, v in _sels)
                    if _sels else "Yok"
                )
                if len(confirmed_sels) > 400:
                    confirmed_sels = confirmed_sels[:400] + "…"

                # ── 4a. Düşünme (Streamed) ───────────────────────────────────
                # Dinamik token bütçesi: kritik/yüksek öncelikli hipotezlerde
                # daha derin düşünce, düşüklerde minimum (hız tasarrufu).
                _PRIO_THINK_TOK = {"critical": 200, "high": 150, "medium": 120, "low": 90}
                think_max_tok = _PRIO_THINK_TOK.get(hyp.get("priority", "medium"), 130)
                # İlk hipotezde sayfa hakkında öğrenme avantajı için biraz daha fazla
                if hyp_idx == 0:
                    think_max_tok = int(think_max_tok * 1.3)

                # Skip think for low-priority NON-FIRST hypotheses → ~3-6s tasarruf/hipo
                # Düşünce fazı atlanırsa default bir 1 cümle gönderilir
                _skip_think = (
                    hyp_idx > 0
                    and hyp.get("priority", "medium") == "low"
                )

                THINK_SYS = (
                    "Sen kıdemli bir QA otomasyon uzmanısın. "
                    "Verilen hipotezi test etmek için net bir strateji belirle. "
                    "Çalışma belleğindeki önceki öğrenmelerden yararlan. "
                    "3-4 cümle, Türkçe, teknik ve özgün düşünceni göster."
                )
                think_prompt = (
                    f"Hipotez [{hyp_id}]: {hyp['claim']}\n"
                    f"Alan: {hyp['area']} | Öncelik: {hyp['priority']}\n"
                    f"İpucu: {hyp.get('actions_hint', '')}\n\n"
                    f"Mevcut URL: {current_url}\n"
                    f"Sayfa tipi: {current_dom.get('page_type', 'generic')}\n\n"
                    f"Çalışma Belleği:\n{memory_text}\n"
                    f"Onaylanmış selectorlar: {confirmed_sels}\n\n"
                    f"Test Geçmişi:\n{history_text}\n\n"
                    "Bu hipotezi nasıl test edersin? Önceki öğrenmelerden nasıl yararlanacaksın?"
                )

                thinking_text = ""
                if _skip_think:
                    # Skip — düşük öncelikli ileri hipotez; UI'a kısa bir not gönder
                    thinking_text = f"Düşük öncelikli hipotez: {hyp.get('actions_hint', 'standart aksiyon dizisi')[:80]}"
                    yield _sse("agent_thinking", {
                        "token": thinking_text,
                        "step": hyp_idx + 1,
                        "hypothesis_id": hyp_id,
                    })
                else:
                    try:
                        # Hard wall: toplam düşünce süresi max 45s; token başına 2s
                        _think_deadline = 45 + think_max_tok * 2
                        async with asyncio.timeout(_think_deadline):
                            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=30, write=10, pool=5)) as client:
                                async with client.stream(
                                    "POST", f"{_GW_BASE}/ai/stream",
                                    json=_gw_payload(THINK_SYS, think_prompt, max_tok=think_max_tok, temp=0.55, task_type="llm_agent_think"),
                                    headers=_GW_HEADERS,
                                ) as resp:
                                    async for line in resp.aiter_lines():
                                        if not line.startswith("data: "):
                                            continue
                                        raw = line[6:]
                                        if raw == "[DONE]":
                                            break
                                        try:
                                            tok = _json.loads(raw).get("token", "")
                                            if tok:
                                                thinking_text += tok
                                                yield _sse("agent_thinking", {
                                                    "token": tok,
                                                    "step": hyp_idx + 1,
                                                    "hypothesis_id": hyp_id,
                                                })
                                        except Exception:
                                            pass
                    except (Exception, asyncio.TimeoutError) as _think_exc:
                        logger.warning("LLM Agent düşünce hatası/timeout [%s]: %s — ipucu kullanılıyor", hyp_id, _think_exc)
                        if not thinking_text:  # zaman aşımı oldu ama hiç token gelmediyse
                            thinking_text = hyp.get("actions_hint", "Standart test akışı uygulanıyor.")[:120]
                        yield _sse("agent_thinking", {
                            "token": thinking_text or "(timeout)",
                            "step": hyp_idx + 1,
                            "hypothesis_id": hyp_id,
                        })

                # ── 4b. Aksiyon Dizisi Planla (Sync JSON, 2-5 adım) ─────────
                # Tech-stack'e göre selector öncelik ipuçları
                _tech_lower = {t.get("name","").lower() for t in tech_stack}
                _sel_hints = ""
                if any(t in _tech_lower for t in ("react", "next.js", "nextjs", "vue", "angular")):
                    _sel_hints = (
                        "Selector önceliği (bu uygulama SPA/React): "
                        "[data-testid='x'] > [aria-label='x'] > #id > .class > tag. "
                        "Selector'ı element listesinden seç, tahmin etme."
                    )
                elif any(t in _tech_lower for t in ("django", "rails", "laravel", "flask")):
                    _sel_hints = (
                        "Selector önceliği (MPA): "
                        "form#id > input[name='x'] > button[type=submit] > .class. "
                        "Form action URL'lerini kullan."
                    )
                elif dom.get("page_type") == "auth":
                    _sel_hints = (
                        "Login sayfası: input[type='email'], input[type='password'], "
                        "button[type='submit'] en güvenilir selector'lar."
                    )

                SEQUENCE_SYS = (
                    "Sen bir QA otomasyon ajanısın. "
                    "Bir test hipotezi için adım adım eylem dizisi planla. "
                    + (_sel_hints + "\n" if _sel_hints else "")
                    + "SADECE JSON döndür:\n"
                    '{\n'
                    '  "strategy": "kısa strateji açıklaması",\n'
                    '  "success_criteria": "hipotezin doğrulandığını gösteren koşul",\n'
                    '  "actions": [\n'
                    '    {\n'
                    '      "type": "click",\n'
                    '      "selector": "#submit-btn",\n'
                    '      "candidates": [".btn-primary", "button[type=submit]"],\n'
                    '      "value": "",\n'
                    '      "description": "Gönder butonuna tıkla",\n'
                    '      "critical": true\n'
                    '    }\n'
                    '  ]\n'
                    '}\n'
                    "Kullanılabilir type değerleri (SADECE BİRİNİ SEÇ):\n"
                    "  click → bir elemente tıkla\n"
                    "  fill → bir input'u doldur (value gerekli)\n"
                    "  navigate → URL'ye git (value = URL)\n"
                    "  scroll → sayfayı kaydır (value = piksel)\n"
                    "  fuzz_input → güvenlik testi payload gir (value: xss|sqli|long|special|empty)\n"
                    "  press_key → klavye tuşuna bas (value = Tab|Enter|Escape)\n"
                    "  wait_for_text → metni bekle (value = beklenen metin)\n"
                    "  assert_visible → element görünür mü kontrol et\n"
                    "  double_click → çift tıkla\n"
                    "  extract_links → sayfadaki linkleri listele\n"
                    "2-5 aksiyon planla. Her aksiyon için MUTLAKA 2-3 aday selector ver "
                    "(farklı attribute'lardan: id, class, aria-label, data-testid, type)."
                )
                seq_prompt = (
                    f"Hipotez [{hyp_id}]: {hyp['claim']}\n"
                    f"Strateji: {thinking_text[:200]}\n"
                    f"URL: {current_url} | Sayfa: {current_dom.get('page_type','generic')}\n"
                    f"DOM elementleri:\n{elements_text}\n\n"
                    f"Çalışan selectorlar: {confirmed_sels}\n"
                    f"Başarısız selectorlar: {working_memory['failed_selectors'][-3:]}\n"
                    "Aksiyon dizisini JSON olarak planla. Selectorları DOM listesinden seç."
                )
                # JSON-retry wrapper: async thread pool'da (event loop bloke etmez)
                # asyncio.timeout: gw_complete retry dahil max 90s — Ollama'da takılırsa scroll fallback'e düşer
                try:
                    async with asyncio.timeout(90):
                        seq_data = await _agw_complete_json(
                            task_type="llm_agent_plan",  # → qwen2.5:14b (JSON güvenilirliği)
                            system_message=SEQUENCE_SYS,
                            user_message=seq_prompt,
                            temperature=0.2,
                            max_tokens=400,
                            retries=1,
                            default={},
                        )
                except (Exception, asyncio.TimeoutError) as _seq_exc:
                    logger.warning("LLM Agent seq plan hatası/timeout [%s]: %s — scroll fallback", hyp_id, _seq_exc)
                    seq_data = {}
                planned_actions: list = seq_data.get("actions", []) if isinstance(seq_data, dict) else []
                strategy_text: str = seq_data.get("strategy", thinking_text[:100]) if isinstance(seq_data, dict) else ""
                success_criteria: str = seq_data.get("success_criteria", "") if isinstance(seq_data, dict) else ""

                # Fallback: en az 1 scroll
                if not planned_actions:
                    planned_actions = [{"type": "scroll", "selector": "", "candidates": [], "value": "400",
                                        "description": "Sayfayı keşfetmek için kaydır", "critical": False}]

                yield _sse("agent_sequence_plan", {
                    "hypothesis_id": hyp_id,
                    "strategy": strategy_text,
                    "success_criteria": success_criteria,
                    "actions_count": len(planned_actions),
                    "actions": [
                        {
                            "type": a.get("type", ""),
                            "description": a.get("description", a.get("type", "")),
                            "critical": bool(a.get("critical", False)),
                        }
                        for a in planned_actions
                    ],
                })

                # ── 4c. Aksiyon Dizisini Çalıştır ───────────────────────────
                # max_steps = hipotez başına maksimum browser aksiyon bütçesi.
                # Plan 4 aksiyon döndürmüş olsa bile max_steps=2 ise sadece 2'si çalışır.
                all_act_data: list = []
                obs_text = ""
                prev_url = current_url
                _did_observe_early = False  # critical-fail observe çağrısı yapıldı mı?

                for sub_idx, planned_action in enumerate(planned_actions[:max_steps]):
                    sub_step = sub_idx + 1
                    sub_total = len(planned_actions)
                    is_last = (sub_idx == sub_total - 1)

                    # Selector fallback zinciri
                    primary = planned_action.get("selector", "")
                    candidates: list = planned_action.get("candidates", [])
                    # Önceden çalışan selectorları önce dene
                    mem_candidates = [v for v in working_memory["confirmed_selectors"].values()
                                      if v not in working_memory["failed_selectors"]]
                    all_candidates = [c for c in ([primary] + candidates + mem_candidates) if c]

                    action = dict(planned_action)
                    action["selector"] = primary  # ilk dene

                    yield _sse("agent_action", {
                        "step": hyp_idx + 1,
                        "sub_step": sub_step,
                        "sub_total": sub_total,
                        "action": action,
                        "hypothesis_id": hyp_id,
                    })

                    if action.get("type") == "done":
                        break

                    # Execute — selector fallback zinciri ile
                    act_data: dict = {}
                    tried_selector = primary
                    for candidate_sel in (all_candidates or [primary, ""]):
                        action_with_sel = dict(action)
                        action_with_sel["selector"] = candidate_sel
                        async with httpx.AsyncClient(timeout=20) as client:
                            act_resp = await client.post(
                                f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/act",
                                json=action_with_sel,
                                headers=_IKEY,
                            )
                        act_data = act_resp.json() if act_resp.status_code == 200 else {}
                        tried_selector = candidate_sel
                        if act_data.get("success", False):
                            # Çalışan selectoru kaydet
                            if candidate_sel:
                                working_memory["confirmed_selectors"][action.get("description", "el")] = candidate_sel
                            break
                        elif candidate_sel:
                            working_memory["failed_selectors"].append(candidate_sel)

                    all_act_data.append(act_data)
                    new_url = act_data.get("url", current_url)

                    yield _sse("agent_screenshot", {
                        "step": hyp_idx + 1,
                        "sub_step": sub_step,
                        "sub_total": sub_total,
                        "screenshot_b64": act_data.get("screenshot_b64", ""),
                        "url": new_url,
                        "success": act_data.get("success", False),
                        "error": act_data.get("error"),
                        "hypothesis_id": hyp_id,
                        "tried_selector": tried_selector,
                    })

                    if new_url != current_url:
                        yield _sse("agent_navigate", {
                            "from_url": current_url,
                            "to_url": new_url,
                            "step": hyp_idx + 1,
                            "sub_step": sub_step,
                        })
                        current_url = new_url

                    # Akıllı observe: son aksiyon VEYA kritik aksiyon başarısız oldu.
                    # Critical fail'lerde hemen observe et — hata bağlamını kaybetmemek için.
                    # Yine de hipotez başına en fazla 1 observe (is_last'a fallback).
                    _act_failed = not act_data.get("success", True)
                    _is_critical = bool(planned_action.get("critical"))
                    _critical_failed = _act_failed and _is_critical and not _did_observe_early
                    should_observe_now = is_last or _critical_failed
                    if _critical_failed:
                        _did_observe_early = True
                    if should_observe_now:
                        # Inline mini gözlem (streamed) — tüm aksiyon listesi üzerinden
                        OBSERVE_SYS = (
                            "Sen bir QA gözlemcisisin. Test aksiyon dizisi sonuçlarını değerlendir. "
                            "4-6 cümle Türkçe gözlem yaz. "
                            "Ciddi sorun bulursan 'BULGU:' ile başlat. "
                            "Hipotezin doğrulanıp doğrulanmadığını açıkça belirt."
                        )
                        _all_console = [
                            e.get("text", "")[:60]
                            for d in all_act_data
                            for e in d.get("console_errors", [])
                        ]
                        _all_network = [
                            str(e.get("status", "")) + " " + e.get("url", "")[:50]
                            for d in all_act_data
                            for e in d.get("network_errors", [])
                        ]
                        _steps_summary = "; ".join(
                            f"Adım {i+1}: {pa.get('description','?')} → "
                            f"{'OK' if d.get('success') else 'HATA: ' + str(d.get('error','?'))[:40]}"
                            for i, (pa, d) in enumerate(zip(planned_actions[:sub_step], all_act_data))
                        )
                        obs_prompt = (
                            f"Hipotez [{hyp_id}]: {hyp['claim']}\n"
                            f"Başarı kriteri: {success_criteria}\n\n"
                            f"Aksiyon özeti: {_steps_summary}\n"
                            f"Başlangıç URL: {prev_url} → Bitiş URL: {new_url}\n"
                            f"Console hataları: {_all_console[:5]}\n"
                            f"Network hataları: {_all_network[:5]}\n\n"
                            "Gözlemini yaz."
                        )
                        obs_text = ""
                        try:
                            async with asyncio.timeout(60):  # gözlem max 60s
                                async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=30, write=10, pool=5)) as client:
                                    async with client.stream(
                                        "POST", f"{_GW_BASE}/ai/stream",
                                        json=_gw_payload(OBSERVE_SYS, obs_prompt, max_tok=250, temp=0.4, task_type="llm_agent_observe"),
                                        headers=_GW_HEADERS,
                                    ) as resp:
                                        async for line in resp.aiter_lines():
                                            if not line.startswith("data: "):
                                                continue
                                            raw = line[6:]
                                            if raw == "[DONE]":
                                                break
                                            try:
                                                tok = _json.loads(raw).get("token", "")
                                                if tok:
                                                    obs_text += tok
                                                    yield _sse("agent_observation", {
                                                        "token": tok,
                                                        "step": hyp_idx + 1,
                                                        "sub_step": sub_step,
                                                        "hypothesis_id": hyp_id,
                                                    })
                                            except Exception:
                                                pass
                        except (Exception, asyncio.TimeoutError) as _obs_exc:
                            logger.warning("LLM Agent gözlem hatası/timeout [%s]: %s — aksiyon özeti kullanılıyor", hyp_id, _obs_exc)
                            if not obs_text:
                                obs_text = f"Gözlem zaman aşımı. Aksiyon özeti: {_steps_summary[:200]}"
                            yield _sse("agent_observation", {
                                "token": obs_text,
                                "step": hyp_idx + 1,
                                "sub_step": sub_step,
                                "hypothesis_id": hyp_id,
                            })

                        # Kritik bulgu → diziye devam etme
                        if "BULGU:" in obs_text and planned_action.get("critical", True):
                            break

                # ── 4d. Bulgu Tespiti & Sınıflandırma ───────────────────────
                all_console = [
                    e.get("text", "")[:80]
                    for d in all_act_data for e in d.get("console_errors", [])
                ]
                all_network = [
                    str(e.get("status", "")) + " " + e.get("url", "")[:60]
                    for d in all_act_data for e in d.get("network_errors", [])
                ]
                any_failed = any(not d.get("success", True) for d in all_act_data)

                has_finding = (
                    "BULGU:" in obs_text
                    or any_failed
                    or bool(all_console)
                    or bool(all_network)
                    or any(kw in obs_text.lower() for kw in ("hata", "error", "başarısız", "sorun", "kritik"))
                )

                # clf'yi burada başlat: has_finding=False ise blok atlanır ama
                # verdict/confidence aşağıda yine de clf'yi kullanır.
                clf: dict = {}
                if has_finding:
                    # Bulgu sınıflandırma + verdict → tek LLM çağrısına birleştirildi (hız için)
                    CLASSIFY_VERDICT_SYS = (
                        "QA değerlendirici. SADECE JSON döndür:\n"
                        '{"severity":"critical|high|medium|low|info",'
                        '"category":"auth|ui|navigation|form|api|performance|security|other",'
                        '"title":"kısa başlık (max 60 kar)",'
                        '"steps_to_reproduce":["adım1"],'
                        '"impact":"kısa etki",'
                        '"verdict":"verified|rejected|partial|inconclusive",'
                        '"confidence":0.0-1.0,'
                        '"evidence":"kısa kanıt",'
                        '"next_suggestion":"öneri"}'
                    )
                    # JSON-retry wrapper: thread pool'da (event loop bloke etmez)
                    # asyncio.timeout: LLM zaten iki çağrı yapabilir (90×2=180s); max 90s zorla
                    try:
                        async with asyncio.timeout(90):
                            clf = await _agw_complete_json(
                                task_type="llm_agent_classify",  # → qwen2.5:14b (kritik karar)
                                system_message=CLASSIFY_VERDICT_SYS,
                                user_message=(
                                    f"Hipotez: {hyp['claim']}\n"
                                    f"Kriter: {success_criteria}\n"
                                    f"Gözlem: {obs_text[:300]}\n"
                                    f"Aksiyonlar: {[a.get('description','') for a in planned_actions[:4]]}\n"
                                    f"Başarı: {[d.get('success',False) for d in all_act_data]}\n"
                                    f"URL: {current_url}"
                                ),
                                temperature=0.2,
                                max_tokens=300,
                                retries=1,
                                default={},
                            )
                    except (Exception, asyncio.TimeoutError) as _clf_exc:
                        logger.warning("LLM Agent sınıflandırma hatası/timeout [%s]: %s — boş clf", hyp_id, _clf_exc)
                        clf = {}
                    finding = {
                        "id": f"F{len(findings)+1}",
                        "step": hyp_idx + 1,
                        "hypothesis_id": hyp_id,
                        "severity": clf.get("severity", "medium"),
                        "category": clf.get("category", "other"),
                        "title": clf.get("title", obs_text[:60]),
                        "description": obs_text[:500],
                        "steps_to_reproduce": clf.get("steps_to_reproduce", []),
                        "impact": clf.get("impact", ""),
                        "url": current_url,
                        "action_sequence": [a.get("description", "") for a in planned_actions],
                        "reproducible": True,
                        "console_errors": all_console[:3],
                        "network_errors": all_network[:3],
                    }
                    # Deduplication: aynı başlık + URL kombinasyonu daha önce eklenmişse atla
                    _f_key = (finding.get("title", "")[:50].lower(), finding.get("url", "")[:60])
                    _is_dup = any(
                        (f.get("title", "")[:50].lower(), f.get("url", "")[:60]) == _f_key
                        for f in findings
                    )
                    if not _is_dup:
                        findings.append(finding)
                        yield _sse("agent_finding", finding)
                    else:
                        # Duplicate bulgu atlandı ama hypothesis_result'a yine de yansıtılacak
                        yield _sse("agent_finding_skipped", {
                            "reason": "duplicate",
                            "title": finding.get("title", ""),
                            "hypothesis_id": hyp_id,
                        })

                # ── 4e. Hipotez Sonucu (sınıflandırma+verdict birleşik yanıttan) ──
                verdict = clf.get("verdict", "partial")
                confidence = float(clf.get("confidence", 0.6))
                next_suggestion = clf.get("next_suggestion", "")

                hyp_result = {
                    "hypothesis_id": hyp_id,
                    "verdict": verdict,
                    "confidence": confidence,
                    "evidence": clf.get("evidence", obs_text[:150]),
                    "has_finding": has_finding,
                    "next_suggestion": next_suggestion,
                    "actions_executed": len(all_act_data),
                    # Performans görünürlüğü: hangi hipotez ne kadar sürdü?
                    "duration_ms": round((__import__("time").time() - _hyp_start_time) * 1000),
                }
                hyp_results.append(hyp_result)
                yield _sse("agent_hypothesis_result", hyp_result)

                # ── 4f. Çalışma Belleğini Güncelle ──────────────────────────
                fact = (
                    f"[{hyp_id}/{verdict}] {hyp['claim'][:50]}: "
                    f"{obs_text[:80].strip()}"
                )
                working_memory["learned_facts"].append(fact)
                working_memory["tested_flows"].append(hyp["claim"][:50])
                if next_suggestion:
                    yield _sse("agent_memory_update", {
                        "fact": fact,
                        "next_suggestion": next_suggestion,
                        "confirmed_selectors_count": len(working_memory["confirmed_selectors"]),
                    })

                # Fetch fresh network/console data after each hypothesis
                try:
                    async with httpx.AsyncClient(timeout=6) as client:
                        net_snap = await client.get(
                            f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/network",
                            headers=_IKEY,
                        )
                    if net_snap.status_code == 200:
                        net_data = net_snap.json()
                        new_errors = [c for c in net_data.get("errors", []) if c not in initial_network]
                        if new_errors:
                            yield _sse("agent_network_activity", {
                                "new_errors": new_errors[:5],
                                "total_calls": net_data.get("total_calls", 0),
                                "error_rate": net_data.get("error_rate", 0),
                                "hypothesis_id": hyp_id,
                            })
                except Exception:
                    pass

                tested_areas.add(_norm_area(hyp.get("area", "genel")))
                history.append(
                    f"[{hyp_id}] {hyp['claim'][:50]} → {verdict} "
                    f"({len(all_act_data)} adım, güven: {confidence:.0%})"
                )

                # Anlık kapsam güncellemesi: her hipotezden sonra frontend'e gönder
                _total_areas = {"auth", "form", "navigation", "api", "security", "performance", "accessibility", "ux"}
                _live_cov = round(len(tested_areas & _total_areas) / len(_total_areas) * 100)
                yield _sse("agent_live_coverage", {
                    "coverage_pct": _live_cov,
                    "tested_areas": list(tested_areas),
                    "hypotheses_done": hyp_idx + 1,
                    "hypotheses_total": len(hypotheses),
                    "findings_count": len(findings),
                })

            # ══ FAZ 4.5: Adaptif 2. Dalga — Bulgulara Dayalı Hipotezler ════
            # Eğer bulgular varsa veya güvenlik alanları test edilmediyse, 2. dalga üret
            security_areas_tested = any(
                h.get("area") in ("security", "auth") for h in hypotheses
            )
            findings_need_followup = any(
                f.get("severity") in ("critical", "high") for f in findings
            )
            untested_areas = {"security", "form", "navigation", "api"} - tested_areas

            # Wave 2 yalnızca yeterli zaman varsa ve çok sayıda hipotez koşulmadıysa başlat
            # Time gate max_steps ile ölçeklenir: küçük testler için 200s, daha uzun testler
            # için 200 + (max_steps-3)*60 (her ekstra step ~60s). Üst sınır 500s.
            _elapsed = __import__("time").time() - start_time
            _wave2_time_limit = min(500, 200 + max(0, (max_steps - 3)) * 60)
            # Smart skip: tüm öncelikli alanlar test edildi VE kritik bulgu yoksa wave 2'yi atla
            _all_priority_covered = not untested_areas and not findings_need_followup
            if _all_priority_covered:
                yield _sse("agent_wave_skipped", {
                    "wave": 2,
                    "reason": "Tüm öncelikli alanlar (security/form/navigation/api) test edildi ve kritik bulgu yok",
                    "tested_areas": list(tested_areas),
                })
            elif (findings_need_followup or untested_areas) and len(hypotheses) < 15 and _elapsed < _wave2_time_limit:
                yield _sse("agent_wave_start", {
                    "wave": 2,
                    "reason": "Kritik bulgular veya test edilmemiş alanlar tespit edildi",
                    "findings_so_far": len(findings),
                    "untested_areas": list(untested_areas),
                })

                WAVE2_SYS = (
                    "QA stratejisti. Mevcut test bulgularına dayanarak "
                    "hedefli takip hipotezleri üret. "
                    "Kritik bulgularla ilgili daha derin testler yap. "
                    "SADECE JSON döndür."
                )
                wave2_prompt = (
                    f"Bulgular: " +
                    " | ".join(f"[{f.get('severity','?')}] {f.get('title','?')[:50]}" for f in findings[:5]) +
                    f"\nTest edilmemiş: {list(untested_areas)} | Sayfa: {dom.get('page_type','generic')}\n"
                    f"Geçmiş: {' | '.join(history[-3:])}\n"
                    "\nTAM OLARAK 3 takip hipotezi üret. SADECE JSON dizisi döndür:\n"
                    '[{"id":"W1","claim":"...","area":"security","priority":"high","actions_hint":"...","test_type":"security"},...]'
                )

                wave2_raw = ""
                _wave2_failed = False
                try:
                    async with asyncio.timeout(90):  # dalga-2 hipotez planı max 90s
                        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=45, write=10, pool=5)) as client:
                            async with client.stream(
                                "POST", f"{_GW_BASE}/ai/stream",
                                json=_gw_payload(WAVE2_SYS, wave2_prompt, max_tok=800, temp=0.35, task_type="llm_agent_plan"),
                                headers=_GW_HEADERS,
                            ) as resp:
                                async for line in resp.aiter_lines():
                                    if not line.startswith("data: "): continue
                                    raw = line[6:]
                                    if raw == "[DONE]": break
                                    try:
                                        tok = _json.loads(raw).get("token", "")
                                        if tok:
                                            wave2_raw += tok
                                            yield _sse("agent_plan_token", {"token": tok, "wave": 2})
                                    except Exception:
                                        pass
                except (Exception, asyncio.TimeoutError) as _w2_exc:
                    logger.warning("LLM Agent dalga-2 hipotez hatası/timeout: %s — dalga-2 atlanıyor", _w2_exc)
                    _wave2_failed = True

                # wave2_raw="" → _parse_hypotheses fallback 3 default döner — istemiyoruz.
                # LLM başarılıysa parse et, timeout/hata durumunda dalga-2'yi tamamen atla.
                wave2_hypotheses = [] if _wave2_failed else _parse_hypotheses(wave2_raw)
                # Re-ID them as W1, W2, ...
                for i, wh in enumerate(wave2_hypotheses):
                    wh["id"] = f"W{i+1}"
                    wh["wave"] = 2

                if wave2_hypotheses:
                    hypotheses.extend(wave2_hypotheses)
                    yield _sse("agent_plan", {
                        "plan": wave2_raw,
                        "hypotheses": wave2_hypotheses,
                        "wave": 2,
                        "url": current_url,
                    })

                    # Execute wave 2 hypotheses (same loop, max 4)
                    for hyp_idx2, hyp in enumerate(wave2_hypotheses[:2]):
                        hyp_id = hyp["id"]
                        _hyp2_start_time = __import__("time").time()
                        # Get fresh DOM
                        async with httpx.AsyncClient(timeout=12) as client:
                            dom_snap_resp2 = await client.get(
                                f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/dom",
                                headers=_IKEY,
                            )
                        current_dom2 = dom_snap_resp2.json() if dom_snap_resp2.status_code == 200 else dom
                        elements_text2 = _format_elements_for_action(current_dom2)
                        memory_text2 = (
                            "Öğrenilen gerçekler: " + "; ".join(working_memory["learned_facts"][-5:])
                            if working_memory["learned_facts"] else "Henüz bilgi yok."
                        )

                        yield _sse("agent_hypothesis_start", {
                            "hypothesis": hyp,
                            "index": hyp_idx2,
                            "total": len(wave2_hypotheses),
                            "wave": 2,
                            "working_memory_facts": working_memory["learned_facts"][-3:],
                        })

                        # Quick plan for wave 2 (thread pool — event loop'u bloke etmez)
                        W2_PLAN_SYS = (
                            "Aksiyon planlayıcı. Hipotezi test etmek için 2-4 adımlık JSON aksiyonu döndür. "
                            "Sadece JSON: {\"strategy\":\"...\",\"success_criteria\":\"...\",\"actions\":[...]}"
                        )
                        try:
                            async with asyncio.timeout(60):  # dalga-2 plan max 60s
                                w2_plan = await _agw_complete_json(
                                    task_type="llm_agent_plan",  # → qwen2.5:14b
                                    system_message=W2_PLAN_SYS,
                                    user_message=(
                                        f"Hipotez: {hyp['claim']}\n"
                                        f"Alan: {hyp.get('area','')}\n"
                                        f"İpucu: {hyp.get('actions_hint','')}\n"
                                        f"Mevcut sayfadaki elementler:\n{elements_text2}\n"
                                        f"Bellek: {memory_text2}"
                                    ),
                                    temperature=0.3,
                                    max_tokens=350,
                                    retries=1,
                                    default={},
                                )
                        except (Exception, asyncio.TimeoutError) as _w2p_exc:
                            logger.warning("LLM Agent dalga-2 plan hatası/timeout [%s]: %s — scroll fallback", hyp_id, _w2p_exc)
                            w2_plan = {}
                        w2_actions = w2_plan.get("actions", [])
                        if not w2_actions:
                            w2_actions = [{"type": "scroll", "selector": "", "candidates": [],
                                           "value": "300", "description": "Sayfayı keşfet", "critical": False}]

                        yield _sse("agent_sequence_plan", {
                            "hypothesis_id": hyp_id,
                            "strategy": w2_plan.get("strategy", hyp["claim"]),
                            "success_criteria": w2_plan.get("success_criteria", ""),
                            "actions_count": len(w2_actions),
                            "actions": [{"type": a.get("type",""), "description": a.get("description",""),
                                         "critical": bool(a.get("critical",False))} for a in w2_actions],
                            "wave": 2,
                        })

                        w2_act_data = []
                        w2_obs_text = ""
                        prev_url_w2 = current_url
                        for sub_idx2, w2_act in enumerate(w2_actions):
                            primary2 = w2_act.get("selector", "")
                            candidates2 = w2_act.get("candidates", [])
                            mem_cands2 = [v for v in working_memory["confirmed_selectors"].values()
                                          if v not in working_memory["failed_selectors"]]
                            all_cands2 = [c for c in ([primary2] + candidates2 + mem_cands2) if c]

                            act2 = dict(w2_act)
                            act_resp2 = None
                            tried_sel2 = primary2
                            for cand2 in (all_cands2 or [""]):
                                act2["selector"] = cand2
                                tried_sel2 = cand2
                                async with httpx.AsyncClient(timeout=20) as client:
                                    r2 = await client.post(
                                        f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}/act",
                                        json=act2, headers=_IKEY,
                                    )
                                if r2.status_code == 200:
                                    act_resp2 = r2.json()
                                    if act_resp2.get("success"):
                                        if w2_act.get("description"):
                                            working_memory["confirmed_selectors"][w2_act["description"]] = cand2
                                        break
                                    else:
                                        if cand2:
                                            working_memory["failed_selectors"].append(cand2)

                            if act_resp2:
                                w2_act_data.append(act_resp2)
                                new_url2 = act_resp2.get("url", current_url)
                                yield _sse("agent_action", {
                                    "step": len(hypotheses) - len(wave2_hypotheses) + hyp_idx2 + 1,
                                    "sub_step": sub_idx2 + 1,
                                    "sub_total": len(w2_actions),
                                    "action": {"type": w2_act.get("type",""), "description": w2_act.get("description",""), "selector": tried_sel2},
                                    "wave": 2,
                                })
                                if act_resp2.get("screenshot_b64"):
                                    yield _sse("agent_screenshot", {
                                        "screenshot_b64": act_resp2["screenshot_b64"],
                                        "url": new_url2,
                                        "sub_step": sub_idx2 + 1,
                                        "wave": 2,
                                    })
                                if act_resp2.get("url_changed"):
                                    current_url = new_url2
                                    yield _sse("agent_navigate", {"to_url": new_url2, "wave": 2})

                        # Quick observation for wave 2
                        _w2_steps = "; ".join(
                            f"{a.get('description','?')} → {'OK' if d.get('success') else 'HATA'}"
                            for a, d in zip(w2_actions[:len(w2_act_data)], w2_act_data)
                        )
                        try:
                            async with asyncio.timeout(45):  # dalga-2 gözlem max 45s
                                w2_obs_raw = await _agw_complete(
                                    task_type="llm_agent_observe",  # → llama3.1:8b (hız)
                                    system_message="QA gözlemci. Kısa ve net gözlem yaz. BULGU: varsa belirt.",
                                    user_message=(
                                        f"Hipotez: {hyp['claim']}\n"
                                        f"Aksiyon özeti: {_w2_steps}\n"
                                        f"URL: {current_url}"
                                    ),
                                    temperature=0.3,
                                    max_tokens=250,
                                )
                        except (Exception, asyncio.TimeoutError) as _w2o_exc:
                            logger.warning("LLM Agent dalga-2 gözlem hatası/timeout [%s]: %s — adım özeti fallback", hyp_id, _w2o_exc)
                            w2_obs_raw = f"Gözlem zaman aşımı. Aksiyon özeti: {_w2_steps[:200]}"
                        w2_obs_text = w2_obs_raw
                        yield _sse("agent_observation", {
                            "token": w2_obs_text,
                            "step": len(hypotheses) - len(wave2_hypotheses) + hyp_idx2 + 1,
                            "hypothesis_id": hyp_id,
                            "wave": 2,
                        })

                        # Finding + verdict for wave 2
                        w2_has_finding = "BULGU:" in w2_obs_text or any(
                            kw in w2_obs_text.lower() for kw in ("hata", "error", "sızdı", "açık", "kritik")
                        )
                        if w2_has_finding:
                            w2_finding = {
                                "id": f"W{hyp_idx2+1}F",
                                "step": len(hypotheses),
                                "hypothesis_id": hyp_id,
                                "severity": "high",
                                "category": hyp.get("area", "other"),
                                "title": f"[Dalga 2] {hyp['claim'][:50]}",
                                "description": w2_obs_text[:400],
                                "steps_to_reproduce": [a.get("description","") for a in w2_actions],
                                "impact": "2. dalga testinde tespit edildi",
                                "url": current_url,
                                "action_sequence": [a.get("description","") for a in w2_actions],
                                "reproducible": True,
                                "wave": 2,
                            }
                            findings.append(w2_finding)
                            yield _sse("agent_finding", w2_finding)

                        w2_verdict = "verified" if w2_has_finding else "rejected"
                        yield _sse("agent_hypothesis_result", {
                            "hypothesis_id": hyp_id,
                            "verdict": w2_verdict,
                            "confidence": 0.75 if w2_has_finding else 0.5,
                            "evidence": w2_obs_text[:120],
                            "wave": 2,
                        })
                        hyp_results.append({
                            "hypothesis_id": hyp_id,
                            "verdict": w2_verdict,
                            "confidence": 0.75 if w2_has_finding else 0.5,
                            "wave": 2,
                            "duration_ms": round((__import__("time").time() - _hyp2_start_time) * 1000),
                        })

                        fact2 = f"[{hyp_id}/wave2/{w2_verdict}] {hyp['claim'][:40]}: {w2_obs_text[:60].strip()}"
                        working_memory["learned_facts"].append(fact2)
                        yield _sse("agent_memory_update", {
                            "fact": fact2,
                            "next_suggestion": "",
                            "confirmed_selectors_count": len(working_memory["confirmed_selectors"]),
                            "wave": 2,
                        })
                        tested_areas.add(_norm_area(hyp.get("area", "genel")))
                        history.append(f"[{hyp_id}/W2] {hyp['claim'][:50]} → {w2_verdict}")

            # ══ FAZ 5: Executive Özet (Streamed) ════════════════════════════
            # Compute coverage
            total_areas = {"auth", "form", "navigation", "api", "security", "performance", "accessibility", "ux"}
            coverage_pct = round(len(tested_areas & total_areas) / len(total_areas) * 100)
            wave1_count = sum(1 for h in hypotheses if not h.get("wave"))
            wave2_count = sum(1 for h in hypotheses if h.get("wave") == 2)

            yield _sse("agent_coverage_update", {
                "coverage_pct": coverage_pct,
                "tested_areas": list(tested_areas),
                "wave1_count": wave1_count,
                "wave2_count": wave2_count,
                "findings_by_severity": {
                    "critical": sum(1 for f in findings if f.get("severity") == "critical"),
                    "high": sum(1 for f in findings if f.get("severity") == "high"),
                    "medium": sum(1 for f in findings if f.get("severity") == "medium"),
                    "low": sum(1 for f in findings if f.get("severity") == "low"),
                },
            })

            yield _sse("agent_summarizing", {
                "steps_done": len(hypotheses),
                "findings_count": len(findings),
                "areas_tested": list(tested_areas),
                "hypotheses_results": hyp_results,
            })

            SUMMARY_SYS = (
                "Sen kıdemli bir QA mühendisi ve test mimarısın. "
                "Tamamlanan test oturumunu analiz ederek kısa ve etkili bir rapor yaz. "
                "Şu bölümleri içer:\n"
                "## Özet\n## Kritik Bulgular\n## Test Kapsamı\n## Öneriler\n\n"
                "Türkçe yaz, net ve profesyonel ol."
            )
            # Hard cap: büyük oturumlar bağlam penceresini taşırmasın (mistral:latest 4096 token)
            _max_findings_in_summary = 8
            findings_summary = "\n".join(
                f"[{f['severity'].upper()}] {f.get('title', f['description'][:50])}"
                for f in findings[:_max_findings_in_summary]
            ) + (f"\n…ve {len(findings) - _max_findings_in_summary} bulgu daha" if len(findings) > _max_findings_in_summary else "")
            hyp_summary = "\n".join(
                f"- [{r['verdict']}] {next((h['claim'][:50] for h in hypotheses if h['id']==r['hypothesis_id']), r['hypothesis_id'])}"
                for r in hyp_results[:10]  # en fazla 10 hipotez sonucu
            )
            _tech_names_sum = ", ".join(t.get("name","") for t in tech_stack[:5]) if tech_stack else "bilinmiyor"
            summary_prompt = (
                f"Test URL: {target_url}\n"
                f"Test tipi: {test_focus or 'genel keşif + güvenlik'} | Sayfa: {dom.get('page_type', 'generic')}\n"
                f"Teknoloji: {_tech_names_sum}\n"
                f"Hipotez: {len(hypotheses)} ({wave1_count} dalga-1, {wave2_count} dalga-2) | "
                f"Kapsam: %{coverage_pct} ({', '.join(list(tested_areas)[:6])})\n\n"
                f"Hipotez sonuçları:\n{hyp_summary}\n\n"
                f"Bulgular ({len(findings)} adet):\n{findings_summary or 'Bulgu yok'}\n\n"
                "Kısa test raporu yaz (4 bölüm: Özet, Kritik Bulgular, Kapsam, Öneriler). "
                "Güvenlik bulgularını özellikle vurgula."
            )

            summary_text = ""
            try:
                async with asyncio.timeout(120):  # özet max 120s — timeout'ta fallback bulgu listesi
                    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10, read=45, write=10, pool=5)) as client:
                        async with client.stream(
                            "POST", f"{_GW_BASE}/ai/stream",
                            json=_gw_payload(SUMMARY_SYS, summary_prompt, max_tok=600, temp=0.4, task_type="llm_agent_summary"),
                            headers=_GW_HEADERS,
                        ) as resp:
                            async for line in resp.aiter_lines():
                                if not line.startswith("data: "):
                                    continue
                                raw = line[6:]
                                if raw == "[DONE]":
                                    break
                                try:
                                    tok = _json.loads(raw).get("token", "")
                                    if tok:
                                        summary_text += tok
                                        yield _sse("agent_summary_token", {"token": tok})
                                except Exception:
                                    pass
            except (Exception, asyncio.TimeoutError) as _sum_exc:
                logger.warning("LLM Agent özet hatası/timeout: %s — bulgular listeleniyor", _sum_exc)
                # Fallback özet: raw bulgular listesi
                # total_areas: FAZ 5 başında tanımlanmış; fallback'te de güvenle kullanılabilir
                _cov_pct = round(len(tested_areas & total_areas) / len(total_areas) * 100) if total_areas else 0
                summary_text = (
                    f"## Test Özeti (LLM hatası)\n\n"
                    f"**URL:** {target_url}\n"
                    f"**Hipotez:** {len(hypotheses)} | **Bulgu:** {len(findings)}\n"
                    f"**Kapsam:** %{_cov_pct}\n\n"
                    + ("\n".join(f"- [{f['severity'].upper()}] {f.get('title','?')}" for f in findings[:10]) or "Bulgu yok.")
                )
                yield _sse("agent_summary_token", {"token": summary_text})

            yield _sse("agent_summary", {
                "summary": summary_text,
                "findings": findings,
                "hypotheses": hypotheses,
                "hypotheses_results": hyp_results,
                "areas_tested": list(tested_areas),
            })

        except Exception as exc:
            logger.exception("LLM Agent döngüsü hatası: %s", exc)
            yield _sse("agent_error", {"error": str(exc)})

        finally:
            if session_id:
                try:
                    async with httpx.AsyncClient(timeout=10) as client:
                        await client.delete(
                            f"{ENGINE_BASE_URL}/api/llm-agent/{session_id}",
                            headers=_IKEY,
                        )
                except Exception as cleanup_exc:
                    logger.warning("LLM Agent oturum kapatma hatası: %s", cleanup_exc)

            duration = round(__import__("time").time() - start_time, 1)
            yield _sse("agent_done", {
                "findings_count": len(findings),
                "hypotheses_count": len(hypotheses),
                "duration_seconds": duration,
                "target_url": target_url,
                "areas_tested": list(tested_areas),
                # session_id frontend'e döner; bir sonraki çalıştırmada reuse_session_id olarak gönderilirse
                # browser context kapatılmadan aynı sayfada devam edilir (~1-3s tasarruf).
                "session_id": session_id,
            })

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )
