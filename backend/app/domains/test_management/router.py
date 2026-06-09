"""Neurex Management API.

Manual QA operation endpoints under /api/v1/test-management/*.
"""

from __future__ import annotations

import hashlib
import ipaddress
import re as _re
import secrets
import socket
from datetime import datetime as _datetime, timezone as _timezone

_UTC = _timezone.utc  # Python 3.9 uyumlu
from typing import Annotated, Optional, cast
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.deps import require_permission, get_current_user
from app.infra.database import get_async_db
from app.domains.test_management import comments_service, design_service, intelligence_service, service
from app.domains.test_management.intelligence_schemas import (
    AnomalyOut,
    CaseRiskScoreOut,
    ETAPredictionOut,
    ReleaseReadinessPredictionOut,
    RunIntelligenceReportOut,
    TesterPerformanceOut,
    TesterProfileOut,
)
from app.domains.test_management.schemas import (
    ALLOWED_COMMENT_ENTITY_TYPES,
    ALLOWED_TECHNIQUES,
    AuditEventOut,
    PagedResponse,
    BulkUpdateCasesRequest,
    BulkUpdateCasesResponse,
    BvaRunCreate,
    CaseDataGenerateRequest,
    CaseDataRowIn,
    CaseDataRowOut,
    CaseDependencyCreate,
    CaseDependencyOut,
    CaseParamSetCreate,
    CaseParamSetOut,
    CaseReviewActionRequest,
    CaseReviewOut,
    CaseReviewSubmitRequest,
    DefectLinkCreate,
    DefectLinkExistingRequest,
    DefectLinkOut,
    DefectLinkUpdate,
    DefectSearchResult,
    DefectRootCauseRequest,
    DefectRootCauseResponse,
    DesignRunOut,
    DtRunCreate,
    EqRunCreate,
    PairwiseRunCreate,
    EvidenceOut,
    ExecutionSummaryOut,
    ExplorationNoteIn,
    ExplorationSessionCreate,
    ExplorationSessionOut,
    ExplorationSessionUpdate,
    MyWorkItemOut,
    RunCompareOut,
    ExpandCaseResponse,
    FlakyTestOut,
    FlakyTestsResponse,
    ImportJobDetailOut,
    ManagementProjectCreate,
    ManagementProjectOut,
    ManagementSettingsOut,
    ManagementUserSettingsUpdate,
    MgmtCommentCreate,
    MgmtCommentOut,
    MgmtCommentReact,
    MgmtCommentUpdate,
    MgmtNotificationCreate,
    MgmtNotificationOut,
    NotificationUnreadCount,
    ProjectApiKeyCreate,
    ProjectApiKeyCreated,
    ProjectApiKeyOut,
    PromoteCasesRequest,
    PromoteCasesResponse,
    QualityScanResponse,
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
    RequirementLinkUpdate,
    RequirementOut,
    RequirementUpdate,
    RunCaseOut,
    RunCaseUpdate,
    RunDetailOut,
    SharedStepCreate,
    SharedStepOut,
    SharedStepUpdate,
    SimilarCaseQuery,
    SimilarCaseResult,
    SsoTestRequest,
    SsoTestResponse,
    StandupOut,
    StepResultUpdate,
    TestCaseCloneRequest,
    TestCaseCreate,
    TestCaseGenerateRequest,
    TestCaseGenerateResponse,
    TestCaseImproveRequest,
    TestCaseImproveResponse,
    TestCaseOut,
    TestCaseUpdate,
    TestCaseVersionOut,
    TestCycleCreate,
    TestCycleOut,
    TestCycleUpdate,
    TestFolderCreate,
    TestFolderOut,
    TestFolderUpdate,
    TestImportJobCreate,
    TestImportJobOut,
    TestPlanAIGenerateRequest,
    TestPlanAIGenerateResponse,
    TestPlanCreate,
    TestPlanOut,
    TestPlanUpdate,
    TestRunCreate,
    TestRunOut,
    TestRunUpdate,
    TestSuiteCreate,
    TestSuiteOut,
    TestSuiteUpdate,
    TraceabilityRow,
    WebhookSubscription,
    WebhookSubscriptionCreate,
    WebhookTestRequest,
    WebhookTestResponse,
)
from app.infra.database import get_db
from app.infra.models import User

# Type aliases for async DB dependency
AsyncDB = Annotated[AsyncSession, Depends(get_async_db)]

def _is_ssrf_blocked(url: str) -> bool:
    """RFC-1918, link-local ve loopback adresleri engelle (IPv4 + IPv6).

    S-HIGH-4: IPv6 validation was missing — now both IPv4 and IPv6 addresses checked.
    Blocked: private (RFC-1918), loopback (::1, 127.0.0.1), link-local, reserved, unspecified.
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""

        # Localhost aliases (IPv4 + IPv6)
        if hostname in ("localhost", "127.0.0.1", "::1", "0.0.0.0", "::", ""):
            return True

        # Try to parse as IPv6 literal first (DNS resolution won't work for IPv6 literals)
        try:
            ip = ipaddress.ip_address(hostname)
            return (
                ip.is_private
                or ip.is_loopback
                or ip.is_link_local
                or ip.is_reserved
                or ip.is_unspecified
            )
        except ValueError:
            # Not a literal IP, try DNS resolution for both IPv4 and IPv6
            pass

        # DNS çözümle — IPv4 ve IPv6'yı deneyin
        try:
            # Try IPv4 first
            addr = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(addr)
            if (ip.is_private or ip.is_loopback or ip.is_link_local or
                ip.is_reserved or ip.is_unspecified):
                return True
        except Exception:
            pass

        # Try IPv6 resolution
        try:
            addr_info = socket.getaddrinfo(hostname, None, socket.AF_INET6)
            if addr_info:
                ipv6_str = addr_info[0][4][0]
                ip = ipaddress.ip_address(ipv6_str)
                if (ip.is_private or ip.is_loopback or ip.is_link_local or
                    ip.is_reserved or ip.is_unspecified):
                    return True
        except Exception:
            pass

        return False
    except Exception:
        return True


_UUID_RE = _re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", _re.I
)


def _validate_uuid(value: str, field: str = "id") -> str:
    if not _UUID_RE.match(value):
        raise HTTPException(400, f"Geçersiz {field} formatı")
    return value


router = APIRouter(prefix="/test-management", tags=["test-management"])

DB = Annotated[Session, Depends(get_db)]
ReadUser = Annotated[User, Depends(require_permission("test_management.read"))]
WriteUser = Annotated[User, Depends(require_permission("test_management.write"))]
ExecuteUser = Annotated[User, Depends(require_permission("test_management.execute"))]
AdminUser = Annotated[User, Depends(require_permission("test_management.admin"))]


@router.get("/health", summary="Neurex Management domain health", include_in_schema=False)
async def health(_user: ReadUser) -> dict[str, str]:
    return {"status": "ok"}


@router.get("/projects", response_model=list[ManagementProjectOut])
async def list_projects(db: AsyncDB, _user: ReadUser) -> list[ManagementProjectOut]:
    return service.list_projects(db, user=_user)


@router.post(
    "/projects",
    response_model=ManagementProjectOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(payload: ManagementProjectCreate, db: AsyncDB, user: AdminUser) -> ManagementProjectOut:
    return service.create_project(db, payload, user)


@router.get("/projects/{project_id}", response_model=ManagementProjectOut)
async def get_project(project_id: str, db: AsyncDB, _user: ReadUser) -> ManagementProjectOut:
    return service.get_project(db, project_id)


@router.post(
    "/projects/by-tspm/{tspm_project_id}/ensure",
    response_model=ManagementProjectOut,
    status_code=status.HTTP_200_OK,
)
async def ensure_project_for_tspm(tspm_project_id: str, db: AsyncDB, user: WriteUser) -> ManagementProjectOut:
    return service.ensure_project_for_tspm(db, tspm_project_id, user)


@router.get("/projects/{project_id}/settings", response_model=ManagementSettingsOut)
async def get_settings(project_id: str, db: AsyncDB, _user: ReadUser) -> ManagementSettingsOut:
    return cast(ManagementSettingsOut, service.management_settings(db, project_id))


@router.patch("/projects/{project_id}/settings/user", response_model=dict)
async def update_user_settings(
    project_id: str,
    payload: ManagementUserSettingsUpdate,
    db: AsyncDB,
    user: WriteUser,
) -> dict:
    """Kullanıcı tarafından özelleştirilebilen proje ayarlarını güncelle."""
    updates = payload.model_dump(exclude_none=True)
    return service.update_management_user_settings(db, project_id, updates)


def _api_key_public(record: dict) -> ProjectApiKeyOut:
    return ProjectApiKeyOut(
        id=record["id"],
        name=record["name"],
        masked_key=record["masked_key"],
        created_at=record["created_at"],
        expires_at=record.get("expires_at"),
        revoked_at=record.get("revoked_at"),
    )


@router.get("/projects/{project_id}/api-keys", response_model=list[ProjectApiKeyOut])
async def list_project_api_keys(project_id: str, db: AsyncDB, _user: ReadUser) -> list[ProjectApiKeyOut]:
    settings = service.management_settings(db, project_id).get("user_settings", {})
    records = settings.get("api_keys", []) if isinstance(settings, dict) else []
    return [_api_key_public(record) for record in records if isinstance(record, dict)]


@router.post("/projects/{project_id}/api-keys", response_model=ProjectApiKeyCreated, status_code=status.HTTP_201_CREATED)
async def create_project_api_key(
    project_id: str,
    payload: ProjectApiKeyCreate,
    db: AsyncDB,
    _user: WriteUser,
) -> ProjectApiKeyCreated:
    raw_key = f"sk-live-{secrets.token_urlsafe(32)}"
    created_at = service.utcnow()
    record = {
        "id": secrets.token_hex(16),
        "name": payload.name.strip(),
        "masked_key": f"{raw_key[:10]}...{raw_key[-4:]}",
        "key_hash": hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
        "created_at": created_at.isoformat(),
        "expires_at": payload.expires_at.isoformat() if payload.expires_at else None,
        "revoked_at": None,
    }
    settings = service.management_settings(db, project_id).get("user_settings", {})
    records = settings.get("api_keys", []) if isinstance(settings, dict) else []
    service.update_management_user_settings(db, project_id, {"api_keys": [record, *records]})
    return ProjectApiKeyCreated(**_api_key_public(record).model_dump(), key=raw_key)


@router.delete("/projects/{project_id}/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_project_api_key(project_id: str, key_id: str, db: AsyncDB, _user: WriteUser) -> None:
    settings = service.management_settings(db, project_id).get("user_settings", {})
    records = settings.get("api_keys", []) if isinstance(settings, dict) else []
    updated = []
    found = False
    for record in records:
        if isinstance(record, dict) and record.get("id") == key_id:
            record = {**record, "revoked_at": service.utcnow().isoformat()}
            found = True
        updated.append(record)
    if not found:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "API anahtarı bulunamadı")
    service.update_management_user_settings(db, project_id, {"api_keys": updated})


def _dispatch_webhooks(subscriptions: list[dict], event: str, payload: dict) -> None:
    """Fire registered outbound webhooks for an event.

    Runs as a BackgroundTask (after the response) so it never blocks or breaks the
    main request. Each hook is independent and best-effort: SSRF-guarded, HMAC-SHA256
    signed when a secret is set, short timeout, and any failure is swallowed.
    """
    import hashlib as _hashlib
    import hmac as _hmac
    import json as _json

    for sub in subscriptions or []:
        try:
            if not sub.get("active", True):
                continue
            if event not in (sub.get("events") or []):
                continue
            url = sub.get("url") or ""
            if not url or _is_ssrf_blocked(url):
                continue
            body = {"event": event, **payload}
            raw = _json.dumps(body, default=str).encode()
            headers = {"Content-Type": "application/json", "X-Webhook-Event": event}
            secret = sub.get("secret")
            if secret:
                sig = _hmac.new(secret.encode(), raw, _hashlib.sha256).hexdigest()
                headers["X-Webhook-Signature"] = f"sha256={sig}"
            httpx.post(url, content=raw, headers=headers, timeout=6.0, follow_redirects=False)
        except Exception:
            continue  # one failing hook must not affect the others or the request


def _project_webhook_subs(db, project_id: str, event: str) -> list[dict]:
    """Load active webhook subscriptions for a project that are interested in `event`."""
    try:
        proj = service.get_project(db, project_id)
        subs = (proj.settings_data or {}).get("webhook_subscriptions", [])
        return [s for s in subs if s.get("active", True) and event in (s.get("events") or [])]
    except Exception:
        return []


@router.post("/projects/{project_id}/webhook-test", response_model=WebhookTestResponse)
async def test_outbound_webhook(
    project_id: str,
    payload: WebhookTestRequest,
    _db: AsyncDB,
    _user: WriteUser,
) -> WebhookTestResponse:
    """Send a short server-side test payload to an outbound webhook target."""
    _validate_uuid(project_id, "project_id")
    parsed = urlparse(payload.url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geçerli bir HTTP(S) webhook URL'i girin")
    if _is_ssrf_blocked(payload.url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu hedefe webhook testi yapılamaz (iç ağ adresi)")

    headers = {"Content-Type": "application/json"}
    if payload.secret:
        headers["X-Webhook-Secret"] = payload.secret

    body = {
        "event": "run.completed",
        "project_id": project_id,
        "run_id": "test-run-id",
        "status": "passed",
        "pass_rate": 87.5,
        **payload.payload,
    }
    try:
        response = httpx.post(payload.url, headers=headers, json=body, timeout=8.0, follow_redirects=False)
    except httpx.HTTPError as exc:
        return WebhookTestResponse(ok=False, message=f"Webhook isteği gönderilemedi: {exc}")

    return WebhookTestResponse(
        ok=200 <= response.status_code < 300,
        status_code=response.status_code,
        message="Webhook testi başarılı." if 200 <= response.status_code < 300 else "Webhook hedefi hata döndürdü.",
    )


@router.post("/projects/{project_id}/sso-test", response_model=SsoTestResponse)
async def test_sso_endpoint(
    project_id: str,
    payload: SsoTestRequest,
    _db: AsyncDB,
    _user: WriteUser,
) -> SsoTestResponse:
    """Probe a SAML SSO URL from the backend so browser CORS does not affect the result."""
    parsed = urlparse(payload.sso_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Geçerli bir HTTP(S) SSO URL'i girin")
    if _is_ssrf_blocked(payload.sso_url):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Bu hedefe SSO testi yapılamaz (iç ağ adresi)")

    try:
        response = httpx.head(payload.sso_url, timeout=8.0, follow_redirects=False)
        if response.status_code in {405, 501}:
            response = httpx.get(payload.sso_url, timeout=8.0, follow_redirects=False)
    except httpx.HTTPError as exc:
        return SsoTestResponse(ok=False, message=f"SSO URL yoklanamadı: {exc}")

    return SsoTestResponse(
        ok=response.status_code < 500,
        status_code=response.status_code,
        message=(
            "SSO endpoint'e backend üzerinden ulaşıldı."
            if response.status_code < 500
            else "SSO hedefi sunucu hatası döndürdü."
        ),
    )


@router.get("/projects/{project_id}/audit-events", response_model=list[AuditEventOut])
async def list_audit_events(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> list[AuditEventOut]:
    return service.list_audit_events(db, project_id, limit=limit)


@router.get("/projects/{project_id}/repository", response_model=RepositoryOut)
async def repository(project_id: str, db: AsyncDB, _user: ReadUser) -> RepositoryOut:
    return service.repository(db, project_id)


@router.get("/projects/{project_id}/export")
async def export_repository(project_id: str, db: AsyncDB, _user: ReadUser) -> dict[str, object]:
    return service.export_repository(db, project_id)


@router.get("/projects/{project_id}/repository/export")
async def export_repository_alias(project_id: str, db: AsyncDB, _user: ReadUser) -> dict[str, object]:
    """Alias for /export — frontend hook compatibility."""
    return service.export_repository(db, project_id)


@router.get("/projects/{project_id}/suites", response_model=list[TestSuiteOut])
async def list_suites(project_id: str, db: AsyncDB, _user: ReadUser) -> list[TestSuiteOut]:
    """Projedeki tüm test suite'lerini listeler."""
    from app.domains.test_management.models import TestSuite
    suites = (await db.scalars(
        select(TestSuite)
        .where(TestSuite.project_id == project_id)
        .order_by(TestSuite.order_index, TestSuite.created_at)
    )).all()
    return list(suites)


@router.post("/projects/{project_id}/suites", response_model=TestSuiteOut, status_code=status.HTTP_201_CREATED)
async def create_suite(project_id: str, payload: TestSuiteCreate, db: AsyncDB, user: WriteUser) -> TestSuiteOut:
    try:
        return service.create_suite(db, project_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/folders", response_model=list[TestFolderOut])
async def list_folders(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    suite_id: Optional[str] = None,
) -> list[TestFolderOut]:
    """Projedeki tüm klasörleri listeler. suite_id filtresi opsiyoneldir."""
    from app.domains.test_management.models import TestFolder, TestSuite
    stmt = (
        select(TestFolder)
        .join(TestSuite, TestFolder.suite_id == TestSuite.id)
        .where(TestSuite.project_id == project_id)
    )
    if suite_id:
        stmt = stmt.where(TestFolder.suite_id == suite_id)
    stmt = stmt.order_by(TestFolder.order_index, TestFolder.created_at)
    folders = (await db.scalars(stmt)).all()
    return list(folders)


@router.post("/projects/{project_id}/folders", response_model=TestFolderOut, status_code=status.HTTP_201_CREATED)
async def create_folder(project_id: str, payload: TestFolderCreate, db: AsyncDB, user: WriteUser) -> TestFolderOut:
    try:
        return service.create_folder(db, project_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/projects/{project_id}/suites/{suite_id}", response_model=TestSuiteOut)
async def update_suite(project_id: str, suite_id: str, payload: TestSuiteUpdate, db: AsyncDB, user: WriteUser) -> TestSuiteOut:
    try:
        return service.update_suite(db, project_id, suite_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/projects/{project_id}/suites/{suite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_suite(project_id: str, suite_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_suite(db, project_id, suite_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/projects/{project_id}/folders/{folder_id}", response_model=TestFolderOut)
async def update_folder(project_id: str, folder_id: str, payload: TestFolderUpdate, db: AsyncDB, user: WriteUser) -> TestFolderOut:
    try:
        return service.update_folder(db, project_id, folder_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/projects/{project_id}/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(project_id: str, folder_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_folder(db, project_id, folder_id, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/projects/{project_id}/cases",
    response_model=PagedResponse[TestCaseOut],
    summary="Test case listesi (sayfalı). limit/offset ile sayfalama desteklenir.",
)
async def list_cases(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    q: str | None = Query(default=None, description="Başlık veya case key'e göre filtre"),
    include_archived: bool = Query(default=False, description="Arşivlenmiş case'leri dahil et"),
    limit: int = Query(default=50, ge=1, le=500, description="Sayfa başına kayıt sayısı"),
    offset: int = Query(default=0, ge=0, description="Atlanacak kayıt sayısı (cursor)"),
    priority: str | None = Query(default=None, description="Önceliğe göre filtre (low/medium/high/critical)"),
    status: str | None = Query(default=None, description="Duruma göre filtre (draft/active/deprecated/archived)"),
    automation_status: str | None = Query(default=None, description="Otomasyon durumu (manual/automated/in_progress)"),
    suite_id: str | None = Query(default=None, description="Suite ID'ye göre filtre"),
    folder_id: str | None = Query(default=None, description="Klasör ID'ye göre filtre"),
    owner_id: str | None = Query(default=None, description="Sahip kullanıcı ID'sine göre filtre"),
) -> PagedResponse[TestCaseOut]:
    filter_kwargs = dict(
        q=q,
        include_archived=include_archived,
        priority=priority,
        status=status,
        automation_status=automation_status,
        suite_id=suite_id,
        folder_id=folder_id,
        owner_id=owner_id,
    )
    total = service.count_cases(db, project_id, **filter_kwargs)
    items = service.list_cases(db, project_id, limit=limit, offset=offset, **filter_kwargs)
    return PagedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.post("/projects/{project_id}/cases", response_model=TestCaseOut, status_code=status.HTTP_201_CREATED)
async def create_case(project_id: str, payload: TestCaseCreate, db: AsyncDB, user: WriteUser) -> TestCaseOut:
    try:
        return service.create_case(db, project_id, payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/projects/{project_id}/cases/quality-scan",
    response_model=QualityScanResponse,
    summary="Test case kalite taraması — kısa başlık, boş adım, vs.",
)
async def quality_scan(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    limit: int = Query(default=50, ge=1, le=200),
) -> QualityScanResponse:
    from app.domains.test_management.schemas import QualityScanResult
    cases = service.list_cases(db, project_id)[:limit]
    results = []
    for case in cases:
        issues = []
        score  = 100
        if len((case.title or "").split()) < 3:
            issues.append("Başlık çok kısa (< 3 kelime)")
            score -= 20
        if not case.objective:
            issues.append("Amaç eksik")
            score -= 10
        if not case.steps or len(case.steps) == 0:
            issues.append("Test adımı yok")
            score -= 30
        elif len(case.steps) == 1:
            issues.append("Sadece 1 test adımı var")
            score -= 10
        if case.steps:
            empty_steps = [s for s in case.steps if not s.action.strip()]
            if empty_steps:
                issues.append(f"{len(empty_steps)} boş adım var")
                score -= 15
            missing_expected = [s for s in case.steps if not s.expected_result.strip()]
            if len(missing_expected) > len(case.steps) // 2:
                issues.append("Adımların yarısından fazlasında beklenen sonuç eksik")
                score -= 15
        if not case.tags or len(case.tags) == 0:
            issues.append("Etiket yok")
            score -= 5
        if issues:
            results.append(QualityScanResult(
                case_id=case.id,
                case_key=case.case_key,
                title=case.title,
                issues=issues,
                score=max(0, score),
                recommendation="İyileştir" if score < 60 else "Gözden geçir",
            ))
    return QualityScanResponse(
        total=len(cases),
        scanned=len(cases),
        issues_found=len(results),
        results=sorted(results, key=lambda r: r.score),
    )


@router.get(
    "/projects/{project_id}/cases/search",
    response_model=list[TestCaseOut],
    summary="Search test cases by title or case key (frontend search)",
)
async def search_cases(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    q: str = Query(default="", description="Search query — matches title and case_key"),
) -> list[TestCaseOut]:
    return service.search_cases(db, project_id, q=q)


@router.get("/projects/{project_id}/cases/{case_id}", response_model=TestCaseOut)
async def get_case(project_id: str, case_id: str, db: AsyncDB, _user: ReadUser) -> TestCaseOut:
    import uuid as _uuid
    try:
        _uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test case bulunamadı")
    return service.get_case(db, project_id, case_id)


@router.get("/projects/{project_id}/cases/{case_id}/versions", response_model=list[TestCaseVersionOut])
async def list_case_versions(project_id: str, case_id: str, db: AsyncDB, _user: ReadUser) -> list[TestCaseVersionOut]:
    return service.list_case_versions(db, project_id, case_id)


@router.get("/projects/{project_id}/cases/{case_id}/sub-cases", response_model=list[TestCaseOut])
async def list_sub_cases(project_id: str, case_id: str, db: AsyncDB, _user: ReadUser) -> list[TestCaseOut]:
    """Return all direct sub-cases of the given parent case."""
    try:
        return cast(list[TestCaseOut], service.list_sub_cases(db, project_id, case_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/projects/{project_id}/cases/{case_id}/sub-cases",
    response_model=TestCaseOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_sub_case(
    project_id: str,
    case_id: str,
    payload: TestCaseCreate,
    db: AsyncDB,
    user: WriteUser,
) -> TestCaseOut:
    """Create a sub-case under the given parent case."""
    try:
        return cast(TestCaseOut, service.create_sub_case(db, project_id, case_id, payload, user))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/projects/{project_id}/cases/{case_id}/dependencies", response_model=list[CaseDependencyOut])
async def list_case_dependencies(project_id: str, case_id: str, db: AsyncDB, _user: ReadUser) -> list[CaseDependencyOut]:
    try:
        return cast(list[CaseDependencyOut], service.list_case_dependencies(db, project_id, case_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/projects/{project_id}/cases/{case_id}/dependencies", response_model=CaseDependencyOut, status_code=201)
async def add_case_dependency(project_id: str, case_id: str, payload: CaseDependencyCreate, db: AsyncDB, user: WriteUser) -> CaseDependencyOut:
    try:
        return cast(CaseDependencyOut, service.add_case_dependency(db, project_id, case_id, payload, user))
    except (KeyError, ValueError) as e:
        raise HTTPException(status_code=400 if isinstance(e, ValueError) else 404, detail=str(e)) from e


@router.delete("/projects/{project_id}/cases/{case_id}/dependencies/{dep_id}", status_code=204)
async def remove_case_dependency(project_id: str, case_id: str, dep_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.remove_case_dependency(db, project_id, case_id, dep_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/projects/{project_id}/cases/{case_id}", response_model=TestCaseOut)
async def update_case(project_id: str, case_id: str, payload: TestCaseUpdate, db: AsyncDB, user: WriteUser) -> TestCaseOut:
    return service.update_case(db, project_id, case_id, payload, user)


@router.post("/projects/{project_id}/cases/{case_id}/archive", response_model=TestCaseOut)
async def archive_case(project_id: str, case_id: str, db: AsyncDB, user: WriteUser) -> TestCaseOut:
    return service.archive_case(db, project_id, case_id, user)


@router.patch(
    "/projects/{project_id}/cases/{case_id}/move",
    response_model=TestCaseOut,
    summary="Case'i farklı suite/folder'a taşı",
)
async def move_case(
    project_id: str,
    case_id: str,
    payload: dict,
    db: AsyncDB,
    user: WriteUser,
) -> TestCaseOut:
    from app.domains.test_management.schemas import TestCaseUpdate
    patch_data: dict = {}
    if "suite_id" in payload:
        patch_data["suite_id"] = payload["suite_id"]
    if "folder_id" in payload:
        patch_data["folder_id"] = payload["folder_id"]
    try:
        return service.update_case(db, project_id, case_id, TestCaseUpdate(**patch_data), user)
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=404 if isinstance(exc, KeyError) else 400, detail=str(exc)) from exc


@router.delete(
    "/projects/{project_id}/cases/{case_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Test case'i kalıcı olarak sil",
)
async def delete_case(project_id: str, case_id: str, db: AsyncDB, user: WriteUser) -> None:
    import uuid as _uuid
    try:
        _uuid.UUID(case_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Test case bulunamadı")
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
async def clone_case(project_id: str, case_id: str, payload: TestCaseCloneRequest, db: AsyncDB, user: WriteUser) -> TestCaseOut:
    try:
        return service.clone_case(db, project_id, case_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/improve",
    response_model=TestCaseImproveResponse,
    summary="AI ile mevcut test case'i iyileştir",
)
async def improve_case(project_id: str, case_id: str, payload: TestCaseImproveRequest, db: AsyncDB, user: WriteUser) -> TestCaseImproveResponse:
    try:
        return await service.improve_case_async(db, project_id, case_id, payload, user)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"İyileştirme hatası: {exc}") from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/submit-review",
    response_model=CaseReviewOut,
    summary="Test case'i incelemeye gönder (draft → pending)",
)
async def submit_case_for_review(
    project_id: str, case_id: str, payload: CaseReviewSubmitRequest, db: AsyncDB, user: WriteUser
) -> CaseReviewOut:
    try:
        case = service.submit_case_for_review(db, project_id, case_id, user, payload.comment)
        return CaseReviewOut.model_validate(case)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/approve",
    response_model=CaseReviewOut,
    summary="Test case incelemesini onayla (pending → approved)",
)
async def approve_case_review(
    project_id: str, case_id: str, payload: CaseReviewActionRequest, db: AsyncDB, user: WriteUser
) -> CaseReviewOut:
    try:
        case = service.approve_case_review(db, project_id, case_id, user, payload.comment)
        return CaseReviewOut.model_validate(case)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/reject",
    response_model=CaseReviewOut,
    summary="Test case incelemesini reddet (pending → rejected)",
)
async def reject_case_review(
    project_id: str, case_id: str, payload: CaseReviewActionRequest, db: AsyncDB, user: WriteUser
) -> CaseReviewOut:
    try:
        case = service.reject_case_review(db, project_id, case_id, user, payload.comment)
        return CaseReviewOut.model_validate(case)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/projects/{project_id}/cases/review-queue",
    response_model=list[CaseReviewOut],
    summary="Belirli review durumundaki case'leri listele",
)
async def list_review_queue(
    project_id: str,
    review_status: str = Query(default="pending", description="none|pending|approved|rejected"),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncDB = ...,
    _user: ReadUser = ...,
) -> list[CaseReviewOut]:
    cases = service.get_review_queue(db, project_id, status=review_status, limit=limit)
    return [CaseReviewOut.model_validate(c) for c in cases]


@router.get(
    "/projects/{project_id}/cases/flaky",
    response_model=FlakyTestsResponse,
    summary="Yüksek flakiness skoruna sahip unstable test case'leri listele",
)
async def list_flaky_cases(
    project_id: str,
    threshold: float = Query(default=0.2, ge=0.0, le=1.0, description="Minimum flakiness skoru (0-1)"),
    min_runs: int = Query(default=3, ge=1, description="Minimum koşum sayısı"),
    limit: int = Query(default=50, ge=1, le=200),
    include_manual: bool = Query(default=False, description="Saf manuel case'leri de dahil et (varsayılan: hariç)"),
    db: AsyncDB = ...,
    _user: ReadUser = ...,
) -> FlakyTestsResponse:
    result = service.list_flaky_cases(
        db, project_id, threshold=threshold, min_runs=min_runs, limit=limit, include_manual=include_manual
    )
    return FlakyTestsResponse(
        items=[FlakyTestOut.model_validate(c) for c in result["items"]],
        total=result["total"],
        threshold=result["threshold"],
    )


@router.post(
    "/projects/{project_id}/cases/generate",
    response_model=TestCaseGenerateResponse,
    summary="AI ile test case üret (save=true ise DB'ye kaydeder)",
)
async def generate_cases(project_id: str, payload: TestCaseGenerateRequest, db: AsyncDB, user: WriteUser) -> TestCaseGenerateResponse:
    try:
        cases = await service.generate_test_cases_async(db, project_id, payload, user)
        return TestCaseGenerateResponse(cases=cases)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Üretim hatası: {exc}") from exc


@router.post(
    "/projects/{project_id}/cases/bulk-update",
    response_model=BulkUpdateCasesResponse,
    summary="Toplu case güncelleme — priority/type/status/suite/folder/tag",
)
async def bulk_update_cases(project_id: str, payload: BulkUpdateCasesRequest, db: AsyncDB, user: WriteUser) -> BulkUpdateCasesResponse:
    updated = 0
    failed  = 0
    for case_id in payload.case_ids:
        try:
            patch: dict = {}
            if payload.priority:   patch["priority"]  = payload.priority
            if payload.type:       patch["type"]       = payload.type
            if payload.status:     patch["status"]     = payload.status
            if payload.suite_id:   patch["suite_id"]   = payload.suite_id
            if payload.folder_id is not None:
                patch["folder_id"] = payload.folder_id
            if patch:
                from app.domains.test_management.schemas import TestCaseUpdate
                service.update_case(db, project_id, case_id, TestCaseUpdate(**patch), user)
            if payload.tags_add or payload.tags_remove:
                case = service.get_case(db, service.resolve_project_id(db, project_id), case_id)
                tags = set(case.tags or [])
                tags.update(payload.tags_add)
                tags.difference_update(payload.tags_remove)
                service.update_case(db, project_id, case_id, TestCaseUpdate(tags=list(tags)), user)
            updated += 1
        except Exception:
            failed += 1
    return BulkUpdateCasesResponse(updated=updated, failed=failed)


@router.get(
    "/projects/{project_id}/runs/{run_id}/progress",
    summary="Test koşumunun canlı ilerleme durumunu döner",
)
async def run_progress(project_id: str, run_id: str, db: AsyncDB, _user: ReadUser) -> dict:
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    from sqlalchemy import select as _sel

    from app.domains.test_management.models import TestCycle as _TC, TestRun as _TR, TestRunCase as TRC
    pid = service.resolve_project_id(db, project_id)
    # Run'ın bu projeye ait olduğunu doğrula — IDOR önleme
    run = (await db.scalar(_sel(_TR).where(_TR.id == run_id)))
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadı")
    cycle = await db.get(_TC, run.cycle_id)
    if not cycle:
        raise HTTPException(status_code=404, detail="Run bulunamadı")
    if cycle.project_id is not None and cycle.project_id != pid:
        raise HTTPException(status_code=404, detail="Run bulunamadı")
    run_cases = list((await db.scalars(_sel(TRC).where(TRC.run_id == run_id))).all())
    total = len(run_cases)
    done_set = {"passed", "failed", "blocked", "skipped"}
    done = len([rc for rc in run_cases if rc.status in done_set])
    passed = len([rc for rc in run_cases if rc.status == "passed"])
    failed = len([rc for rc in run_cases if rc.status == "failed"])
    blocked = len([rc for rc in run_cases if rc.status == "blocked"])
    not_run = total - done
    pct = round((done / total * 100) if total > 0 else 0, 1)
    pass_rate = round((passed / done * 100) if done > 0 else 0, 1)
    return {
        "run_id": run_id,
        "total": total,
        "done": done,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "not_run": not_run,
        "progress_pct": pct,
        "pass_rate_pct": pass_rate,
    }


@router.post(
    "/projects/{project_id}/runs/{run_id}/complete",
    response_model=TestRunOut,
    summary="Koşumu manuel olarak tamamlandı olarak işaretle",
)
async def complete_run(project_id: str, run_id: str, db: AsyncDB, user: WriteUser, background: BackgroundTasks) -> TestRunOut:
    _validate_uuid(project_id, "project_id")
    _validate_uuid(run_id, "run_id")
    from sqlalchemy import select as _sel

    from app.domains.test_management.models import TestRun as TR
    pid = service.resolve_project_id(db, project_id)
    run = (await db.scalar(_sel(TR).where(TR.id == run_id)))
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadı")
    # Sahiplik kontrolü — IDOR önleme.
    # project_id, cycle üzerinde değil plan üzerinde tutulur (cycle.project_id auto-create'de
    # set edilmiyordu → eski kontrol her zaman 404 veriyordu). get_run ile aynı zinciri kullan.
    from app.domains.test_management.models import TestCycle as _TC2, TestPlan as _TP2
    cycle = await db.get(_TC2, run.cycle_id)
    plan = await db.get(_TP2, cycle.plan_id) if cycle else None
    if not cycle or not plan or plan.project_id != pid:
        raise HTTPException(status_code=404, detail="Run bulunamadı")
    run.status = "completed"
    run.completed_at = run.completed_at or _datetime.now(_UTC)
    await db.commit()
    await db.refresh(run)
    # Fire outbound webhooks (event-driven, best-effort, after response).
    subs = _project_webhook_subs(db, pid, "run.completed")
    if subs:
        rcs = list(run.run_cases)
        total = len(rcs)
        passed = sum(1 for rc in rcs if rc.status == "passed")
        background.add_task(
            _dispatch_webhooks, subs, "run.completed",
            {
                "project_id": pid,
                "run_id": run.id,
                "name": run.name,
                "status": run.status,
                "total": total,
                "passed": passed,
                "pass_rate": round(passed / total * 100, 1) if total else 0.0,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
            },
        )
    return run


@router.get(
    "/projects/{project_id}/standup",
    response_model=StandupOut,
    summary="Aktif run için standup verisini döner",
)
async def get_standup(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    run_id: str | None = Query(default=None),
) -> StandupOut:
    try:
        return service.get_standup(db, project_id, run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/projects/{project_id}/plans", response_model=TestPlanOut, status_code=status.HTTP_201_CREATED)
async def create_plan(project_id: str, payload: TestPlanCreate, db: AsyncDB, user: WriteUser) -> TestPlanOut:
    return service.create_plan(db, project_id, payload, user)


@router.post(
    "/projects/{project_id}/plans/ai-generate",
    response_model=TestPlanAIGenerateResponse,
    summary="AI ile test planı önerileri üret",
)
async def ai_generate_plan(project_id: str, payload: TestPlanAIGenerateRequest, db: AsyncDB, user: WriteUser) -> TestPlanAIGenerateResponse:
    try:
        return await service.ai_generate_plan_async(db, project_id, payload, user)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Plan üretim hatası: {exc}") from exc


@router.get("/projects/{project_id}/plans", response_model=list[TestPlanOut])
async def list_plans(project_id: str, db: AsyncDB, _user: ReadUser) -> list[TestPlanOut]:
    return service.list_plans(db, project_id)


@router.patch("/projects/{project_id}/plans/{plan_id}", response_model=TestPlanOut)
async def update_plan(project_id: str, plan_id: str, payload: TestPlanUpdate, db: AsyncDB, user: WriteUser) -> TestPlanOut:
    try:
        return service.update_plan(db, project_id, plan_id, payload, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/projects/{project_id}/plans/{plan_id}/impact-summary",
    summary="Plan silinirse etkilenecek kayıt sayıları",
)
async def plan_impact_summary(
    project_id: str,
    plan_id: str,
    db: AsyncDB,
    _user: ReadUser,
) -> dict:
    """Silme modalı açılmadan önce kullanıcıya etki özeti göster."""
    try:
        return service.get_plan_impact_summary(db, project_id, plan_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Plan bulunamadı")


@router.delete("/projects/{project_id}/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan(project_id: str, plan_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_plan(db, project_id, plan_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/projects/{project_id}/cycles",
    response_model=PagedResponse[TestCycleOut],
    summary="Test döngüsü listesi (sayfalı). limit/offset ile sayfalama desteklenir.",
)
async def list_cycles(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    plan_id: str | None = Query(default=None, description="Belirli bir plana ait cycle'ları filtrele"),
    limit: int = Query(default=50, ge=1, le=500, description="Sayfa başına kayıt sayısı"),
    offset: int = Query(default=0, ge=0, description="Atlanacak kayıt sayısı (cursor)"),
) -> PagedResponse[TestCycleOut]:
    total = service.count_cycles(db, project_id, plan_id=plan_id)
    items = service.list_cycles(db, project_id, plan_id=plan_id, limit=limit, offset=offset)
    return PagedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.post("/projects/{project_id}/cycles", response_model=TestCycleOut, status_code=status.HTTP_201_CREATED)
async def create_cycle(project_id: str, payload: TestCycleCreate, db: AsyncDB, user: WriteUser) -> TestCycleOut:
    return service.create_cycle(db, project_id, payload, user)


@router.patch("/projects/{project_id}/cycles/{cycle_id}", response_model=TestCycleOut)
async def update_cycle(project_id: str, cycle_id: str, payload: TestCycleUpdate, db: AsyncDB, user: WriteUser) -> TestCycleOut:
    try:
        return service.update_cycle(db, project_id, cycle_id, payload, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/projects/{project_id}/cycles/{cycle_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cycle(project_id: str, cycle_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_cycle(db, project_id, cycle_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/projects/{project_id}/regression/suggest", response_model=list[RegressionCandidateOut])
async def suggest_regression_candidates(
    project_id: str,
    payload: RegressionSelectionFilter,
    db: AsyncDB,
    _user: ReadUser,
) -> list[RegressionCandidateOut]:
    return service.suggest_regression_candidates(db, project_id, payload)


@router.get("/projects/{project_id}/regression/sets", response_model=list[RegressionSetOut])
async def list_regression_sets(project_id: str, db: AsyncDB, _user: ReadUser) -> list[RegressionSetOut]:
    return cast(list[RegressionSetOut], service.list_regression_sets(db, project_id))


@router.post(
    "/projects/{project_id}/regression/sets",
    response_model=RegressionSetOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_regression_set(
    project_id: str,
    payload: RegressionSetCreate,
    db: AsyncDB,
    user: WriteUser,
) -> RegressionSetOut:
    return cast(RegressionSetOut, service.create_regression_set(db, project_id, payload, user))


@router.patch(
    "/projects/{project_id}/regression/sets/{set_id}",
    response_model=RegressionSetOut,
)
async def update_regression_set(
    project_id: str,
    set_id: str,
    payload: RegressionSetUpdate,
    db: AsyncDB,
    user: WriteUser,
) -> RegressionSetOut:
    return cast(RegressionSetOut, service.update_regression_set(db, project_id, set_id, payload, user))


@router.post(
    "/projects/{project_id}/regression/sets/{set_id}/cases",
    response_model=RegressionSetOut,
)
async def add_cases_to_regression_set(
    project_id: str,
    set_id: str,
    payload: RegressionSetAddCases,
    db: AsyncDB,
    user: WriteUser,
) -> RegressionSetOut:
    return cast(RegressionSetOut, service.add_cases_to_regression_set(db, project_id, set_id, payload.case_ids, user))


@router.delete(
    "/projects/{project_id}/regression/sets/{set_id}/cases/{case_id}",
    response_model=RegressionSetOut,
)
async def remove_case_from_regression_set(
    project_id: str,
    set_id: str,
    case_id: str,
    db: AsyncDB,
    user: WriteUser,
) -> RegressionSetOut:
    return cast(RegressionSetOut, service.remove_case_from_regression_set(db, project_id, set_id, case_id, user))


@router.delete(
    "/projects/{project_id}/regression/sets/{set_id}",
    status_code=204,
)
async def delete_regression_set(
    project_id: str,
    set_id: str,
    db: AsyncDB,
    user: WriteUser,
) -> None:
    service.delete_regression_set(db, project_id, set_id, user)


@router.get(
    "/projects/{project_id}/runs",
    response_model=PagedResponse[TestRunOut],
    summary="Test koşumu listesi (sayfalı). limit/offset ile sayfalama desteklenir.",
)
async def list_runs(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    status: str | None = Query(default=None, description="Run durumuna göre filtre"),
    cycle_id: str | None = Query(default=None, description="Belirli bir cycle'a ait run'ları filtrele"),
    limit: int = Query(default=50, ge=1, le=500, description="Sayfa başına kayıt sayısı"),
    offset: int = Query(default=0, ge=0, description="Atlanacak kayıt sayısı (cursor)"),
) -> PagedResponse[TestRunOut]:
    total = service.count_runs(db, project_id, cycle_id=cycle_id, status_filter=status)
    items = service.list_runs(db, project_id, limit=limit, offset=offset, cycle_id=cycle_id, status_filter=status)
    return PagedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + len(items)) < total,
    )


@router.post("/projects/{project_id}/runs", response_model=TestRunOut, status_code=status.HTTP_201_CREATED)
async def create_run(project_id: str, payload: TestRunCreate, db: AsyncDB, user: WriteUser) -> TestRunOut:
    return service.create_run(db, project_id, payload, user)


@router.patch("/projects/{project_id}/runs/{run_id}", response_model=TestRunOut)
async def update_run(project_id: str, run_id: str, payload: TestRunUpdate, db: AsyncDB, user: WriteUser) -> TestRunOut:
    try:
        return service.update_run(db, project_id, run_id, payload, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/projects/{project_id}/runs/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(project_id: str, run_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_run(db, project_id, run_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/projects/{project_id}/runs/{run_id}", response_model=RunDetailOut)
async def get_run(project_id: str, run_id: str, db: AsyncDB, _user: ReadUser) -> RunDetailOut:
    return service.get_run(db, project_id, run_id)


@router.get(
    "/projects/{project_id}/run-compare",
    response_model=RunCompareOut,
    summary="İki test koşusunu karşılaştır (yeni bozulanlar / düzelenler / hâlâ başarısız)",
)
async def compare_runs(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    base: str = Query(..., description="Temel (eski) run id"),
    target: str = Query(..., description="Karşılaştırılan (yeni) run id"),
) -> RunCompareOut:
    try:
        return RunCompareOut(**service.compare_runs(db, project_id, base, target))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/projects/{project_id}/run-cases/{run_case_id}", response_model=RunCaseOut)
async def update_run_case(
    project_id: str,
    run_case_id: str,
    payload: RunCaseUpdate,
    db: AsyncDB,
    user: ExecuteUser,
) -> RunCaseOut:
    """Update the overall status of a test case in a run (TestRail-style case-level result)."""
    result = service.update_run_case(db, project_id, run_case_id, payload, user)
    # Recompute flakiness score asynchronously after status change
    if payload.status in ("passed", "failed") and result.case_id:
        try:
            service.recompute_case_flakiness(db, result.case_id)
        except Exception:
            pass  # Non-critical: do not fail the main request
    return result


@router.patch("/projects/{project_id}/run-cases/{run_case_id}/steps/{step_no}", response_model=RunCaseOut)
async def update_step_result(
    project_id: str,
    run_case_id: str,
    step_no: int,
    payload: StepResultUpdate,
    db: AsyncDB,
    user: ExecuteUser,
) -> RunCaseOut:
    return service.update_step_result(db, project_id, run_case_id, step_no, payload, user)


@router.get(
    "/projects/{project_id}/run-cases/{run_case_id}/evidence",
    response_model=list[EvidenceOut],
    summary="List evidence files for a run case (without run_id in path)",
)
async def list_evidence_by_run_case(
    project_id: str,
    run_case_id: str,
    db: AsyncDB,
    _user: ReadUser,
) -> list[EvidenceOut]:
    try:
        return [EvidenceOut(**item) for item in service.list_evidence_by_run_case(db, project_id, run_case_id)]
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/projects/{project_id}/reports/dashboard-summary")
async def dashboard_summary(project_id: str, db: AsyncDB, _user: ReadUser) -> dict:
    return service.dashboard_summary(db, project_id)


@router.get(
    "/projects/{project_id}/stats/dashboard",
    summary="Fast lightweight dashboard stats (summaryFast) — skips heavy pass-rate & coverage queries",
)
async def stats_dashboard(project_id: str, db: AsyncDB, _user: ReadUser) -> dict:
    """Lighter alternative to /reports/dashboard-summary.

    Returns total_cases, active_runs, failed_cases, critical_defects, suite_count.
    Use /reports/dashboard-summary for the full metric set (pass_rate, coverage, etc.).
    """
    return service.dashboard_summary_fast(db, project_id)


@router.get(
    "/projects/{project_id}/my-work",
    response_model=list[MyWorkItemOut],
    summary="Run-case'ler içinde mevcut kullanıcıya atanmış işler (My Work kuyruğu)",
)
async def my_work(
    project_id: str,
    db: AsyncDB,
    user: ReadUser,
    scope: str = Query(default="open", pattern="^(open|all)$"),
) -> list[MyWorkItemOut]:
    """Tüm run'lar boyunca giriş yapan kullanıcıya atanmış test case'leri döndürür.

    scope=open → sadece yapılacak işler (not_run/running, run tamamlanmamış)
    scope=all  → atanmış tüm run-case'ler
    """
    items = service.list_my_work(db, project_id, str(user.id), scope=scope)
    return [MyWorkItemOut(**item) for item in items]


# ── Exploratory testing sessions ────────────────────────────────────────────────

@router.get("/projects/{project_id}/exploration-sessions", response_model=list[ExplorationSessionOut])
async def list_exploration_sessions(project_id: str, db: AsyncDB, _user: ReadUser) -> list[ExplorationSessionOut]:
    return service.list_exploration_sessions(db, project_id)


@router.post(
    "/projects/{project_id}/exploration-sessions",
    response_model=ExplorationSessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_exploration_session(
    project_id: str, payload: ExplorationSessionCreate, db: AsyncDB, user: WriteUser
) -> ExplorationSessionOut:
    return service.create_exploration_session(db, project_id, payload, user)


@router.get("/projects/{project_id}/exploration-sessions/{session_id}", response_model=ExplorationSessionOut)
async def get_exploration_session(project_id: str, session_id: str, db: AsyncDB, _user: ReadUser) -> ExplorationSessionOut:
    try:
        return service.get_exploration_session(db, project_id, session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/projects/{project_id}/exploration-sessions/{session_id}", response_model=ExplorationSessionOut)
async def update_exploration_session(
    project_id: str, session_id: str, payload: ExplorationSessionUpdate, db: AsyncDB, user: WriteUser
) -> ExplorationSessionOut:
    try:
        return service.update_exploration_session(db, project_id, session_id, payload, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/projects/{project_id}/exploration-sessions/{session_id}/notes",
    response_model=ExplorationSessionOut,
)
async def add_exploration_note(
    project_id: str, session_id: str, payload: ExplorationNoteIn, db: AsyncDB, user: WriteUser
) -> ExplorationSessionOut:
    try:
        return service.add_exploration_note(db, project_id, session_id, payload, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/projects/{project_id}/exploration-sessions/{session_id}/notes/{note_id}",
    response_model=ExplorationSessionOut,
)
async def delete_exploration_note(
    project_id: str, session_id: str, note_id: str, db: AsyncDB, user: WriteUser
) -> ExplorationSessionOut:
    try:
        return service.delete_exploration_note(db, project_id, session_id, note_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete(
    "/projects/{project_id}/exploration-sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_exploration_session(project_id: str, session_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_exploration_session(db, project_id, session_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/projects/{project_id}/reports/execution-summary", response_model=ExecutionSummaryOut)
async def execution_summary(project_id: str, db: AsyncDB, _user: ReadUser) -> ExecutionSummaryOut:
    return service.execution_summary(db, project_id)


@router.get("/projects/{project_id}/reports/run-trend", response_model=list[dict])
async def run_trend(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[dict]:
    """Son N test koşusunun geçme oranı trendi (Reports sayfası grafikleri için)."""
    return service.get_run_trend(db, project_id, limit=limit)


@router.get("/projects/{project_id}/reports/release", response_model=ReleaseReportOut)
async def release_report(project_id: str, db: AsyncDB, _user: ReadUser) -> ReleaseReportOut:
    return service.release_report(db, project_id)


@router.get("/projects/{project_id}/reports/release/signoffs", response_model=list[ReleaseSignoffOut])
async def list_release_signoffs(project_id: str, db: AsyncDB, _user: ReadUser) -> list[ReleaseSignoffOut]:
    return service.list_release_signoffs(db, project_id)


@router.post(
    "/projects/{project_id}/reports/release/signoffs",
    response_model=ReleaseSignoffOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_release_signoff(
    project_id: str,
    payload: ReleaseSignoffCreate,
    db: AsyncDB,
    user: WriteUser,
) -> ReleaseSignoffOut:
    return service.create_release_signoff(db, project_id, payload, user)


@router.get("/projects/{project_id}/requirements/traceability", response_model=list[TraceabilityRow])
async def requirement_traceability(project_id: str, db: AsyncDB, _user: ReadUser) -> list[TraceabilityRow]:
    """Return the requirements ↔ test-case traceability matrix."""
    return cast(list[TraceabilityRow], service.requirement_traceability(db, project_id))


@router.get("/projects/{project_id}/requirements/catalog", response_model=list[RequirementOut])
async def list_requirements(project_id: str, db: AsyncDB, _user: ReadUser) -> list[RequirementOut]:
    return service.list_requirements(db, project_id)


@router.post(
    "/projects/{project_id}/requirements/catalog",
    response_model=RequirementOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement(
    project_id: str,
    payload: RequirementCreate,
    db: AsyncDB,
    user: WriteUser,
) -> RequirementOut:
    return service.create_requirement(db, project_id, payload, user)


@router.post(
    "/projects/{project_id}/requirements/bulk",
    summary="CSV veya JSON listeden toplu gereksinim oluştur",
)
async def bulk_create_requirements(
    project_id: str,
    payload: list[RequirementCreate],
    db: AsyncDB,
    user: WriteUser,
) -> dict:
    created = 0
    for req in payload[:200]:
        try:
            service.create_requirement(db, project_id, req, user)
            created += 1
        except Exception:
            pass
    return {"created": created, "total": len(payload)}


@router.get("/projects/{project_id}/requirements", response_model=list[RequirementLinkOut])
async def list_requirement_links(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    case_id: str | None = Query(default=None),
) -> list[RequirementLinkOut]:
    return service.list_requirement_links(db, project_id, case_id=case_id)


@router.post(
    "/projects/{project_id}/requirements",
    status_code=status.HTTP_201_CREATED,
)
async def create_requirement_or_link(
    project_id: str,
    payload: RequirementLinkCreate,
    db: AsyncDB,
    user: WriteUser,
) -> dict:
    """Esnek requirement oluşturma: case_id varsa link, yoksa standalone requirement."""
    import secrets as _secrets

    if payload.case_id:
        # Klasik link modu
        result = service.create_requirement_link(db, project_id, payload, user)
        return {
            "id": result.id, "project_id": result.project_id,
            "case_id": result.case_id, "external_key": result.external_key,
            "title_snapshot": result.title_snapshot, "coverage_status": result.coverage_status,
        }
    else:
        # Standalone requirement oluştur (catalog'a ekle)
        from app.domains.test_management.schemas import RequirementCreate
        title = payload.title or payload.title_snapshot or "Yeni Gereksinim"
        req_payload = RequirementCreate(
            external_source=payload.external_source,
            external_key=payload.external_key or f"REQ-{_secrets.token_hex(4).upper()}",
            title=title,
            description=payload.description,
            priority=payload.priority,
            status=payload.status,
            url=payload.url,
            tags=payload.tags,
        )
        result = service.create_requirement(db, project_id, req_payload, user)
        return {
            "id": result.id, "project_id": result.project_id,
            "external_key": result.external_key, "title": result.title,
            "description": result.description, "priority": result.priority,
            "status": result.status, "created_at": result.created_at.isoformat(),
        }


@router.patch("/projects/{project_id}/requirements/{req_id}")
async def update_requirement_or_link(
    project_id: str,
    req_id: str,
    payload: RequirementUpdate,
    db: AsyncDB,
    user: WriteUser,
) -> dict:
    """Standalone requirement veya link güncelle (ID'ye göre otomatik belirlenir)."""
    try:
        req = service.update_requirement(db, project_id, req_id, payload, user)
        return RequirementOut.model_validate(req).model_dump(mode="json")
    except KeyError:
        pass
    # Fallback: link güncelleme
    link_payload = RequirementLinkUpdate(**{k: v for k, v in payload.model_dump(exclude_unset=True).items() if k in RequirementLinkUpdate.model_fields})
    try:
        link = service.update_requirement_link(db, project_id, req_id, link_payload, user)
        return RequirementLinkOut.model_validate(link).model_dump(mode="json")
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/projects/{project_id}/requirements/{req_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_requirement_or_link(project_id: str, req_id: str, db: AsyncDB, user: WriteUser) -> None:
    """Standalone requirement veya link sil (ID'ye göre otomatik belirlenir)."""
    try:
        service.delete_requirement(db, project_id, req_id, user)
        return
    except KeyError:
        pass
    try:
        service.delete_requirement_link(db, project_id, req_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/projects/{project_id}/defects", response_model=list[DefectLinkOut])
async def list_defect_links(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    case_id: Optional[str] = Query(default=None),
) -> list[DefectLinkOut]:
    return service.list_defect_links(db, project_id, case_id=case_id)


@router.post(
    "/projects/{project_id}/defects",
    response_model=DefectLinkOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_defect_link(
    project_id: str, payload: DefectLinkCreate, db: AsyncDB, user: WriteUser, background: BackgroundTasks
) -> DefectLinkOut:
    defect = service.create_defect_link(db, project_id, payload, user)
    # Fire outbound webhooks (event-driven, best-effort, after response).
    pid = service.resolve_project_id(db, project_id)
    subs = _project_webhook_subs(db, pid, "defect.created")
    if subs:
        background.add_task(
            _dispatch_webhooks, subs, "defect.created",
            {
                "project_id": pid,
                "defect_id": defect.id,
                "external_key": defect.external_key,
                "title": defect.title,
                "severity": defect.severity,
                "status": defect.status,
            },
        )
    return defect


@router.get(
    "/projects/{project_id}/defects/search",
    response_model=list[DefectSearchResult],
    summary="Mevcut defect'leri ara (external_key bazında tekilleştirilmiş) — 'mevcut defect bağla' için",
)
async def search_defects(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    q: Optional[str] = Query(default=None, description="Başlık veya defect anahtarı araması"),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[DefectSearchResult]:
    return [DefectSearchResult(**item) for item in service.search_defects(db, project_id, q=q, limit=limit)]


@router.post(
    "/projects/{project_id}/defects/link-existing",
    response_model=DefectLinkOut,
    status_code=status.HTTP_201_CREATED,
    summary="Mevcut bir defect'i başarısız bir run-case'e bağla (aynı bug birden çok case'i düşürdüğünde)",
)
async def link_existing_defect(project_id: str, payload: DefectLinkExistingRequest, db: AsyncDB, user: WriteUser) -> DefectLinkOut:
    try:
        return service.link_existing_defect(
            db, project_id, payload.run_case_id, payload.defect_id, payload.step_result_id, user
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/projects/{project_id}/defects/{defect_id}", response_model=DefectLinkOut)
async def update_defect_link(
    project_id: str,
    defect_id: str,
    payload: DefectLinkUpdate,
    db: AsyncDB,
    user: WriteUser,
) -> DefectLinkOut:
    return service.update_defect_link(db, project_id, defect_id, payload, user)


@router.delete("/projects/{project_id}/defects/{defect_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_defect_link(project_id: str, defect_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_defect_link(db, project_id, defect_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get(
    "/projects/{project_id}/defects/export",
    summary="Defect'leri CSV veya JSON olarak dışa aktar",
)
async def export_defects(
    project_id: str,
    db: AsyncDB,
    _user: ReadUser,
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    """Defect'leri CSV veya JSON olarak dışa aktar."""
    import csv
    import io
    import json as _json
    from fastapi.responses import Response as _Response

    pid = service.resolve_project_id(db, project_id)
    defects = service.list_defect_links(db, pid)

    if format == "json":
        data = [
            {
                "id": d.id,
                "external_key": d.external_key,
                "title": d.title,
                "status": d.status,
                "severity": d.severity,
                "priority": d.priority,
                "root_cause": d.root_cause,
                "retest_status": d.retest_status,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in defects
        ]
        return _Response(
            content=_json.dumps(data, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=defects.json"},
        )
    else:  # csv
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "External Key", "Title", "Status", "Severity", "Priority", "Root Cause", "Retest Status", "Created"])
        for d in defects:
            writer.writerow([
                d.id, d.external_key, d.title, d.status,
                d.severity, d.priority, d.root_cause or "",
                d.retest_status, str(d.created_at) if d.created_at else "",
            ])
        return _Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=defects.csv"},
        )


@router.post(
    "/projects/{project_id}/defects/analyze-root-cause",
    response_model=DefectRootCauseResponse,
    summary="AI ile defect root cause analizi yap",
)
async def analyze_defect_root_cause(
    project_id: str,
    payload: DefectRootCauseRequest,
    db: AsyncDB,
    user: WriteUser,
) -> DefectRootCauseResponse:
    try:
        import json as _json

        from app.domains.ai import service as ai_svc
        prompt = (
            f"Defect: {payload.defect_title}\n"
            f"Durum: {payload.defect_status or 'open'}\n"
            f"Test bağlamı: {payload.test_context or 'Belirtilmemiş'}\n\n"
            "Bu defectin kök nedenini analiz et. JSON döndür:\n"
            '{"root_cause": "açıklama", "suggestions": ["öneri1", "öneri2"], "category": "ui|api|db|logic|env|data"}'
        )
        raw = ai_svc.call_llm(
            "Sen kıdemli bir QA ve yazılım mühendisisin. Defect root cause analizi yap. JSON döndür.",
            prompt, json_mode=True,
            _trace_project_id=str(project_id),
            _trace_task_type="root_cause_analysis",
        )
        data = _json.loads(raw) if isinstance(raw, str) else raw
        return DefectRootCauseResponse(
            root_cause=data.get("root_cause", "Analiz yapılamadı"),
            suggestions=data.get("suggestions", []),
            category=data.get("category"),
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analiz hatası: {exc}") from exc


@router.get("/projects/{project_id}/imports", response_model=list[TestImportJobOut])
async def list_import_jobs(project_id: str, db: AsyncDB, _user: ReadUser) -> list[TestImportJobOut]:
    return service.list_import_jobs(db, project_id)


@router.get("/projects/{project_id}/imports/{job_id}", response_model=ImportJobDetailOut)
async def get_import_job(project_id: str, job_id: str, db: AsyncDB, _user: ReadUser) -> ImportJobDetailOut:
    return service.get_import_job(db, project_id, job_id)


@router.post(
    "/projects/{project_id}/imports/{job_id}/commit",
    response_model=TestImportJobOut,
)
async def commit_import_job(project_id: str, job_id: str, db: AsyncDB, user: WriteUser) -> TestImportJobOut:
    return service.commit_import_job(db, project_id, job_id, user)


@router.post(
    "/projects/{project_id}/imports",
    response_model=TestImportJobOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_import_job(project_id: str, payload: TestImportJobCreate, db: AsyncDB, user: WriteUser) -> TestImportJobOut:
    return service.create_import_job(db, project_id, payload, user)


@router.post(
    "/projects/{project_id}/cases/search-similar",
    response_model=list[SimilarCaseResult],
    summary="Semantic similarity search across test cases",
)
async def search_similar_cases(
    project_id: str,
    payload: SimilarCaseQuery,
    db: AsyncDB,
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
async def list_evidence(
    project_id: str,
    run_id: str,
    run_case_id: str,
    db: AsyncDB,
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
async def create_comment(payload: MgmtCommentCreate, db: AsyncDB, user: WriteUser) -> MgmtCommentOut:
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
async def list_comments(
    db: AsyncDB,
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
async def patch_comment(
    comment_id: str,
    payload: MgmtCommentUpdate,
    db: AsyncDB,
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
async def remove_comment(comment_id: str, db: AsyncDB, user: WriteUser) -> MgmtCommentOut:
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
async def react_comment(
    comment_id: str,
    payload: MgmtCommentReact,
    db: AsyncDB,
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
async def list_notifications(
    db: AsyncDB,
    user: ReadUser,
    unread_only: bool = Query(default=False),
    include_archived: bool = Query(default=False),
    project_id: str | None = Query(default=None),
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
async def unread_count(db: AsyncDB, user: ReadUser) -> NotificationUnreadCount:
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
async def create_notification(
    payload: MgmtNotificationCreate,
    db: AsyncDB,
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
async def read_notification(
    notification_id: str,
    db: AsyncDB,
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
async def archive_notification(
    notification_id: str,
    db: AsyncDB,
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
async def read_all_notifications(db: AsyncDB, user: ReadUser) -> dict[str, int]:
    affected = comments_service.mark_all_read(db, user_id=str(user.id))
    return {"updated": affected}


@router.post(
    "/comments/summarize",
    summary="AI-generated TL;DR / decisions / open questions for a comment thread",
)
async def summarize_comment_thread(
    payload: dict,
    db: AsyncDB,
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
async def notifications_digest(
    db: AsyncDB,
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
async def design_create_bva(payload: BvaRunCreate, db: AsyncDB, user: WriteUser) -> DesignRunOut:
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
async def design_create_eq(payload: EqRunCreate, db: AsyncDB, user: WriteUser) -> DesignRunOut:
    tenant_id = _require_tenant(user)
    try:
        return design_service.create_eq_run(db, tenant_id, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/design/dt",
    response_model=DesignRunOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Decision Table run",
)
async def design_create_dt(payload: DtRunCreate, db: AsyncDB, user: WriteUser) -> DesignRunOut:
    tenant_id = _require_tenant(user)
    try:
        return design_service.create_dt_run(db, tenant_id, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/design/pairwise",
    response_model=DesignRunOut,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a Pairwise (All-Pairs) run",
)
async def design_create_pairwise(payload: PairwiseRunCreate, db: AsyncDB, user: WriteUser) -> DesignRunOut:
    tenant_id = _require_tenant(user)
    try:
        return design_service.create_pairwise_run(db, tenant_id, user, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/design/runs",
    response_model=list[DesignRunOut],
    summary="List design technique runs for the current tenant",
)
async def design_list_runs(
    db: AsyncDB,
    user: ReadUser,
    technique: str | None = Query(default=None),
    requirement_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
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
async def design_get_run(run_id: str, db: AsyncDB, user: ReadUser) -> DesignRunOut:
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
async def design_promote(
    run_id: str,
    payload: PromoteCasesRequest,
    db: AsyncDB,
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
async def design_create_param_set(
    case_id: str,
    payload: CaseParamSetCreate,
    db: AsyncDB,
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
async def design_list_param_sets(case_id: str, db: AsyncDB, user: ReadUser) -> list[CaseParamSetOut]:
    tenant_id = _require_tenant(user)
    sets = design_service.list_param_sets(db, tenant_id, case_id)
    return [CaseParamSetOut.model_validate(s) for s in sets]


@router.post(
    "/cases/{case_id}/data",
    response_model=list[CaseDataRowOut],
    status_code=status.HTTP_201_CREATED,
    summary="Append data rows to a parameter set (manual / csv / llm-generated)",
)
async def design_add_data_rows(
    case_id: str,
    payload: CaseDataGenerateRequest,
    db: AsyncDB,
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
async def design_list_data_rows(
    case_id: str,
    param_set_id: str,
    db: AsyncDB,
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
async def design_add_manual_rows(
    case_id: str,
    param_set_id: str,
    rows: list[CaseDataRowIn],
    db: AsyncDB,
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
async def design_expand_case(case_id: str, db: AsyncDB, user: WriteUser) -> ExpandCaseResponse:
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
async def run_intelligence(project_id: str, run_id: str, db: AsyncDB, _user: ReadUser) -> RunIntelligenceReportOut:
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
async def run_eta(project_id: str, run_id: str, db: AsyncDB, _user: ReadUser) -> ETAPredictionOut:
    from sqlalchemy import select as _select

    from app.domains.test_management.models import TestRun, TestRunCase

    run = (await db.execute(_select(TestRun).where(TestRun.id == run_id))).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadı")

    run_cases = (await db.execute(
        _select(TestRunCase).where(TestRunCase.run_id == run_id)
    )).scalars().all()

    eta = intelligence_service._predict_eta(run, run_cases)
    return ETAPredictionOut(**eta.__dict__)


@router.get(
    "/projects/{project_id}/intelligence/runs/{run_id}/anomalies",
    response_model=list[AnomalyOut],
    summary="Koşumdaki anomalileri tespit et: takılı case, inaktif tester, yüksek blocked oranı",
)
async def run_anomalies(project_id: str, run_id: str, db: AsyncDB, _user: ReadUser) -> list[AnomalyOut]:
    from sqlalchemy import select as _select

    from app.domains.test_management.models import TestRun, TestRunCase

    run = (await db.execute(_select(TestRun).where(TestRun.id == run_id))).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run bulunamadı")

    run_cases = (await db.execute(
        _select(TestRunCase).where(TestRunCase.run_id == run_id)
    )).scalars().all()

    eta = intelligence_service._predict_eta(run, run_cases)
    testers = intelligence_service._build_tester_profiles(run_cases)
    anomalies = intelligence_service._detect_anomalies(run, run_cases, testers, eta)
    return [AnomalyOut(**a.__dict__) for a in anomalies]


@router.get(
    "/projects/{project_id}/intelligence/runs/{run_id}/risk-queue",
    response_model=list[CaseRiskScoreOut],
    summary="Kalan case'leri risk skoruna göre sırala — en riskli önce",
)
async def run_risk_queue(project_id: str, run_id: str, db: AsyncDB, _user: ReadUser) -> list[CaseRiskScoreOut]:
    from sqlalchemy import select as _select

    from app.domains.test_management.models import TestRunCase

    run_cases = (await db.execute(
        _select(TestRunCase).where(TestRunCase.run_id == run_id)
    )).scalars().all()

    scored = intelligence_service._risk_sort_remaining(db, run_cases)
    return [CaseRiskScoreOut(**c.__dict__) for c in scored]


@router.get(
    "/projects/{project_id}/intelligence/release-prediction",
    response_model=ReleaseReadinessPredictionOut,
    summary="Mevcut ilerlemeye göre release gate'e ulaşılıp ulaşılamayacağını tahmin et",
)
async def release_prediction(project_id: str, db: AsyncDB, _user: ReadUser) -> ReleaseReadinessPredictionOut:
    result = intelligence_service.predict_release_readiness(db, project_id)
    return ReleaseReadinessPredictionOut(**result.__dict__)


@router.get(
    "/projects/{project_id}/intelligence/testers/{user_id}",
    response_model=TesterPerformanceOut,
    summary="Bir tester'ın bu proje genelindeki performans profili",
)
async def tester_performance(project_id: str, user_id: str, db: AsyncDB, _user: ReadUser) -> TesterPerformanceOut:
    data = intelligence_service.get_tester_performance(db, project_id, user_id)
    return TesterPerformanceOut(**data)


# ── Tester Home: bana atanmış case'ler ───────────────────────────────────────

@router.get(
    "/projects/{project_id}/my-cases",
    summary="Aktif run'larda oturum açmış kullanıcıya atanmış case'leri döner",
)
async def my_assigned_cases(project_id: str, db: AsyncDB, user: ReadUser) -> list[dict]:
    from sqlalchemy import select as _sel

    from app.domains.test_management.models import TestCycle, TestRun, TestRunCase

    rows = (await db.execute(
        _sel(TestRunCase, TestRun)
        .join(TestRun, TestRunCase.run_id == TestRun.id)
        .join(TestCycle, TestRun.cycle_id == TestCycle.id)
        .where(TestRunCase.assigned_to == user.id)
        .where(TestRun.status.in_(["not_started", "in_progress"]))
        .order_by(TestRun.created_at.desc())
    )).all()

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


# ── Shared Steps ──────────────────────────────────────────────────────────────

@router.get("/projects/{project_id}/shared-steps", response_model=list[SharedStepOut])
async def list_shared_steps(project_id: str, db: AsyncDB, _user: ReadUser) -> list[SharedStepOut]:
    return cast(list[SharedStepOut], service.list_shared_steps(db, project_id))


@router.post(
    "/projects/{project_id}/shared-steps",
    response_model=SharedStepOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_shared_step(project_id: str, payload: SharedStepCreate, db: AsyncDB, user: WriteUser) -> SharedStepOut:
    return cast(SharedStepOut, service.create_shared_step(db, project_id, payload, user))


@router.get("/projects/{project_id}/shared-steps/{step_id}", response_model=SharedStepOut)
async def get_shared_step(project_id: str, step_id: str, db: AsyncDB, _user: ReadUser) -> SharedStepOut:
    try:
        return cast(SharedStepOut, service.get_shared_step(db, project_id, step_id))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.patch("/projects/{project_id}/shared-steps/{step_id}", response_model=SharedStepOut)
async def update_shared_step(project_id: str, step_id: str, payload: SharedStepUpdate, db: AsyncDB, user: WriteUser) -> SharedStepOut:
    try:
        return cast(SharedStepOut, service.update_shared_step(db, project_id, step_id, payload, user))
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.delete("/projects/{project_id}/shared-steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shared_step(project_id: str, step_id: str, db: AsyncDB, user: WriteUser) -> None:
    try:
        service.delete_shared_step(db, project_id, step_id, user)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post("/projects/{project_id}/shared-steps/{step_id}/use", status_code=status.HTTP_204_NO_CONTENT)
async def increment_shared_step_usage(project_id: str, step_id: str, db: AsyncDB, _user: ReadUser) -> None:
    """Increment usage counter when a shared step template is inserted into a case."""
    try:
        service.get_shared_step(db, project_id, step_id)  # verify ownership
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    service.increment_shared_step_usage(db, step_id)
    await db.commit()


# ── SSO Konfigürasyonu ────────────────────────────────────────────────────────
# SSO/SAML yapılandırması settings_data JSON sütununda saklanır.

class SsoConfigIn(BaseModel):
    enabled: bool = False
    entity_id: str = ""
    sso_url: str = ""
    cert: str = ""
    provider: str = ""


class SsoConfigOut(BaseModel):
    enabled: bool = False
    entity_id: str = ""
    sso_url: str = ""
    provider: str = ""


async def _get_mgmt_project(db: AsyncSession, project_id: str):
    from app.domains.test_management.models import TestManagementProject as TMP
    pid = service.resolve_project_id(db, project_id)
    proj = (await db.scalars(select(TMP).where(TMP.id == pid))).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Management project not found")
    return proj


@router.get("/projects/{project_id}/sso-config", response_model=SsoConfigOut)
async def get_sso_config(project_id: str, db: AsyncDB, _user: ReadUser) -> SsoConfigOut:
    proj = await _get_mgmt_project(db, project_id)
    cfg = (proj.settings_data or {}).get("sso_config", {})
    return SsoConfigOut(**cfg) if cfg else SsoConfigOut()


@router.put("/projects/{project_id}/sso-config", response_model=SsoConfigOut)
async def save_sso_config(project_id: str, payload: SsoConfigIn, db: AsyncDB, user: WriteUser) -> SsoConfigOut:
    proj = await _get_mgmt_project(db, project_id)
    settings = dict(proj.settings_data or {})
    settings["sso_config"] = payload.model_dump()
    proj.settings_data = settings
    await db.commit()
    return SsoConfigOut(**{k: v for k, v in payload.model_dump().items() if k != "cert"})


# ── Webhook Bildirimleri ──────────────────────────────────────────────────────
# Webhook abonelikleri settings_data["webhook_notifications"] listesinde saklanır.


class WebhookNotifIn(BaseModel):
    name: str
    url: str
    events: list[str] = []
    active: bool = True


class WebhookNotifOut(BaseModel):
    id: str
    name: str
    url: str
    events: list[str]
    active: bool


@router.get("/projects/{project_id}/webhook-notifications", response_model=list[WebhookNotifOut])
async def list_webhooks(project_id: str, db: AsyncDB, _user: ReadUser) -> list[WebhookNotifOut]:
    proj = await _get_mgmt_project(db, project_id)
    hooks = (proj.settings_data or {}).get("webhook_notifications", [])
    return [WebhookNotifOut(**h) for h in hooks]


@router.post("/projects/{project_id}/webhook-notifications", response_model=WebhookNotifOut, status_code=status.HTTP_201_CREATED)
async def create_webhook(project_id: str, payload: WebhookNotifIn, db: AsyncDB, user: WriteUser) -> WebhookNotifOut:
    proj = await _get_mgmt_project(db, project_id)
    settings = dict(proj.settings_data or {})
    hooks: list[dict] = list(settings.get("webhook_notifications", []))
    new_hook = {"id": secrets.token_hex(8), **payload.model_dump()}
    hooks.append(new_hook)
    settings["webhook_notifications"] = hooks
    proj.settings_data = settings
    await db.commit()
    return WebhookNotifOut(**new_hook)


@router.delete("/projects/{project_id}/webhook-notifications/{hook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(project_id: str, hook_id: str, db: AsyncDB, user: WriteUser) -> None:
    proj = await _get_mgmt_project(db, project_id)
    settings = dict(proj.settings_data or {})
    hooks = [h for h in settings.get("webhook_notifications", []) if h.get("id") != hook_id]
    settings["webhook_notifications"] = hooks
    proj.settings_data = settings
    await db.commit()


# ── Webhook Subscriptions ────────────────────────────────────────────────────
# Webhook abonelikleri settings_data["webhook_subscriptions"] listesinde saklanır.
# api_keys ile aynı pattern kullanılır (service.get_management_settings + update_management_user_settings).


@router.get("/projects/{project_id}/webhook-subscriptions", response_model=list[WebhookSubscription])
async def list_webhook_subscriptions(project_id: str, db: AsyncDB, _user: ReadUser) -> list[WebhookSubscription]:
    settings = service.management_settings(db, project_id).get("user_settings", {})
    records = settings.get("webhook_subscriptions", []) if isinstance(settings, dict) else []
    return [WebhookSubscription(**r) for r in records if isinstance(r, dict)]


@router.post("/projects/{project_id}/webhook-subscriptions", response_model=WebhookSubscription, status_code=status.HTTP_201_CREATED)
async def create_webhook_subscription(
    project_id: str,
    payload: WebhookSubscriptionCreate,
    db: AsyncDB,
    _user: WriteUser,
) -> WebhookSubscription:
    settings = service.management_settings(db, project_id).get("user_settings", {})
    records = settings.get("webhook_subscriptions", []) if isinstance(settings, dict) else []
    new_sub = {
        "id": str(uuid4()),
        "url": payload.url,
        "events": payload.events,
        "secret": payload.secret,
        "active": True,
        "created_at": _datetime.now(_UTC).isoformat(),
    }
    service.update_management_user_settings(db, project_id, {"webhook_subscriptions": [new_sub, *records]})
    return WebhookSubscription(**new_sub)


@router.delete("/projects/{project_id}/webhook-subscriptions/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook_subscription(project_id: str, webhook_id: str, db: AsyncDB, _user: WriteUser) -> None:
    settings = service.management_settings(db, project_id).get("user_settings", {})
    records = [r for r in settings.get("webhook_subscriptions", []) if isinstance(r, dict) and r.get("id") != webhook_id]
    service.update_management_user_settings(db, project_id, {"webhook_subscriptions": records})


# ── Webhook Probe ─────────────────────────────────────────────────────────────


class WebhookProbeRequest(BaseModel):
    url: str
    events: list[str] = []


@router.post("/webhook-probe", response_model=dict)
async def webhook_probe(body: WebhookProbeRequest, _user: ReadUser) -> dict:
    """Webhook URL'ini backend tarafından test eder (CORS sorununu önler)."""
    if _is_ssrf_blocked(body.url):
        raise HTTPException(status_code=422, detail="Webhook URL'i dahili ağa erişim sağlamaya izin vermiyor")
    import httpx as _httpx
    payload = {"event": body.events[0] if body.events else "test", "test": True}
    try:
        resp = _httpx.post(body.url, json=payload, timeout=8.0)
        return {"status": resp.status_code, "ok": resp.is_success}
    except _httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="Webhook endpoint zaman aşımına uğradı") from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Webhook URL'e ulaşılamadı: {exc}") from exc


# ── Özel Dashboard'lar ────────────────────────────────────────────────────────
# Dashboard'lar settings_data["custom_dashboards"] listesinde saklanır.
# Frontend useCustomDashboard hook'u bu endpoint'leri kullanır.


class DashboardWidgetIn(BaseModel):
    id: str
    type: str
    title: str
    x: int = 0
    y: int = 0
    w: int = 2
    h: int = 2
    config: dict | None = None


class DashboardIn(BaseModel):
    name: str
    widgets: list[DashboardWidgetIn] = []


class DashboardOut(BaseModel):
    id: str
    name: str
    widgets: list[dict]
    created_at: str
    updated_at: str


def _now_iso() -> str:
    return _datetime.now(_UTC).isoformat()


@router.get("/projects/{project_id}/dashboards", response_model=list[DashboardOut])
async def list_dashboards(project_id: str, db: AsyncDB, _user: ReadUser) -> list[DashboardOut]:
    proj = await _get_mgmt_project(db, project_id)
    items = (proj.settings_data or {}).get("custom_dashboards", [])
    return [DashboardOut(**d) for d in items]


@router.post("/projects/{project_id}/dashboards", response_model=DashboardOut, status_code=status.HTTP_201_CREATED)
async def create_dashboard(project_id: str, payload: DashboardIn, db: AsyncDB, user: WriteUser) -> DashboardOut:
    proj = await _get_mgmt_project(db, project_id)
    settings = dict(proj.settings_data or {})
    items: list[dict] = list(settings.get("custom_dashboards", []))
    now = _now_iso()
    new_dash: dict = {
        "id": f"dash-{secrets.token_hex(6)}",
        "name": payload.name,
        "widgets": [w.model_dump() for w in payload.widgets],
        "created_at": now,
        "updated_at": now,
    }
    items.append(new_dash)
    settings["custom_dashboards"] = items
    proj.settings_data = settings
    await db.commit()
    return DashboardOut(**new_dash)


@router.put("/projects/{project_id}/dashboards/{dash_id}", response_model=DashboardOut)
async def update_dashboard(project_id: str, dash_id: str, payload: DashboardIn, db: AsyncDB, user: WriteUser) -> DashboardOut:
    proj = await _get_mgmt_project(db, project_id)
    settings = dict(proj.settings_data or {})
    items: list[dict] = list(settings.get("custom_dashboards", []))
    target = next((d for d in items if d.get("id") == dash_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Dashboard bulunamadı")
    target["name"] = payload.name
    target["widgets"] = [w.model_dump() for w in payload.widgets]
    target["updated_at"] = _now_iso()
    settings["custom_dashboards"] = items
    proj.settings_data = settings
    await db.commit()
    return DashboardOut(**target)


@router.delete("/projects/{project_id}/dashboards/{dash_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dashboard(project_id: str, dash_id: str, db: AsyncDB, user: WriteUser) -> None:
    proj = await _get_mgmt_project(db, project_id)
    settings = dict(proj.settings_data or {})
    items = [d for d in settings.get("custom_dashboards", []) if d.get("id") != dash_id]
    settings["custom_dashboards"] = items
    proj.settings_data = settings
    await db.commit()


# ── Convenience endpoints for frontend ────────────────────────────────────────

@router.get("/projects/{project_id}/tags", response_model=list[str])
async def list_project_tags(project_id: str, db: AsyncDB, _user: ReadUser) -> list[str]:
    """Return all unique tags used in the project's test cases."""
    from sqlalchemy import text
    project_id = service.resolve_project_id(db, project_id)
    rows = (await db.execute(
        text(
            "SELECT DISTINCT tag FROM test_management_cases, "
            "jsonb_array_elements_text(tags) AS tag "
            "WHERE project_id = :pid AND NOT archived ORDER BY tag"
        ),
        {"pid": project_id},
    )).fetchall()
    return [r[0] for r in rows]


@router.get("/projects/{project_id}/modules")
async def list_project_modules(project_id: str, db: AsyncDB, _user: ReadUser) -> list[dict]:
    """Return project modules (test suites) with case counts."""
    from sqlalchemy import func
    from app.domains.test_management.models import TestSuite, TestCase
    project_id = service.resolve_project_id(db, project_id)
    suites = (
        db.query(TestSuite, func.count(TestCase.id).label("case_count"))
        .outerjoin(TestCase, (TestCase.suite_id == TestSuite.id) & ~TestCase.archived)
        .filter(TestSuite.project_id == project_id)
        .group_by(TestSuite.id)
        .order_by(TestSuite.name)
        .all()
    )
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "status": s.status,
            "case_count": count,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s, count in suites
    ]


@router.get("/projects/{project_id}/milestones")
async def list_project_milestones(project_id: str, db: AsyncDB, _user: ReadUser) -> list[dict]:
    """Return project milestones (test plans) with cycle counts."""
    from sqlalchemy import func
    from app.domains.test_management.models import TestPlan, TestCycle
    project_id = service.resolve_project_id(db, project_id)
    plans = (
        db.query(TestPlan, func.count(TestCycle.id).label("cycle_count"))
        .outerjoin(TestCycle, TestCycle.plan_id == TestPlan.id)
        .filter(TestPlan.project_id == project_id)
        .group_by(TestPlan.id)
        .order_by(TestPlan.created_at.desc())
        .all()
    )
    return [
        {
            "id": p.id,
            "name": p.name,
            "description": p.scope_summary,
            "plan_type": p.plan_type,
            "status": p.status,
            "cycle_count": count,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
        for p, count in plans
    ]


# ─── Case Attachment Endpoints ────────────────────────────────────────────────

_ATTACHMENT_STORE: dict[str, dict] = {}  # In-memory store (production: S3/DB)
_MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/projects/{project_id}/cases/{case_id}/attachments",
    status_code=201,
    tags=["test-management"],
    summary="Test case'e dosya ekle",
)
async def upload_case_attachment(
    project_id: str,
    case_id: str,
    file: UploadFile,
    db: AsyncDB,
    user: WriteUser,
) -> dict:
    """Test case'e dosya ekler (max 10 MB).

    Desteklenen formatlar: resim, PDF, metin, video (ekran kaydı).
    """
    content = await file.read()
    if len(content) > _MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=413, detail="Dosya 10 MB sınırını aşıyor")

    attachment_id = str(uuid4())
    now_iso = _datetime.now(_UTC).isoformat()
    record = {
        "id": attachment_id,
        "project_id": project_id,
        "case_id": case_id,
        "filename": file.filename or "unknown",
        "size": len(content),
        "content_type": file.content_type or "application/octet-stream",
        "uploader_id": str(user.id),
        "created_at": now_iso,
    }
    _ATTACHMENT_STORE[attachment_id] = {**record, "_content": content}
    return record


@router.get(
    "/projects/{project_id}/cases/{case_id}/attachments",
    tags=["test-management"],
    summary="Test case dosyalarını listele",
)
async def list_case_attachments(
    project_id: str,
    case_id: str,
    db: AsyncDB,
    user: ReadUser,
) -> list:
    """Belirtilen test case'e ait dosyaları listeler."""
    return [
        {k: v for k, v in rec.items() if k != "_content"}
        for rec in _ATTACHMENT_STORE.values()
        if rec["case_id"] == case_id and rec["project_id"] == project_id
    ]


@router.get(
    "/projects/{project_id}/cases/{case_id}/attachments/{attachment_id}/download",
    tags=["test-management"],
    summary="Test case dosyasını indir",
)
async def download_case_attachment(
    project_id: str,
    case_id: str,
    attachment_id: str,
    db: AsyncDB,
    user: ReadUser,
) -> StreamingResponse:
    """Belirtilen eki indirir."""
    import io

    rec = _ATTACHMENT_STORE.get(attachment_id)
    if not rec or rec["case_id"] != case_id or rec["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Ek bulunamadı")
    content = rec["_content"]
    return StreamingResponse(
        io.BytesIO(content),
        media_type=rec["content_type"],
        headers={"Content-Disposition": f"attachment; filename=\"{rec['filename']}\""},
    )


@router.delete(
    "/projects/{project_id}/cases/{case_id}/attachments/{attachment_id}",
    status_code=204,
    tags=["test-management"],
    summary="Test case dosyasını sil",
)
async def delete_case_attachment(
    project_id: str,
    case_id: str,
    attachment_id: str,
    db: AsyncDB,
    user: WriteUser,
) -> None:
    """Belirtilen eki siler."""
    rec = _ATTACHMENT_STORE.get(attachment_id)
    if not rec or rec["case_id"] != case_id or rec["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Ek bulunamadı")
    del _ATTACHMENT_STORE[attachment_id]
