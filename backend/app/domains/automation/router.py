"""Automation Engine proxy — forwards requests to the Flask engine service."""

import logging
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User

logger = logging.getLogger(__name__)

from app.config import settings
from app.domains.automation.brain import AutomationBrainService, SqlAlchemyAutomationRunStore, brain_service
from app.domains.automation.schemas import (
    AutomationBrainSummary,
    AutomationCapability,
    AutomationRunCreate,
    AutomationRunList,
    AutomationRunOut,
)
from app.domains.automation_suite import service as suite_service
from app.domains.automation_suite.schemas import SuiteRunRequest
from app.domains.api_testing import service as api_testing_service
from app.domains.mobile.orchestrator import get_store as get_mobile_store
from app.domains.mobile.orchestrator import start_suite as start_mobile_suite
from app.domains.mobile.schemas import AppiumAction
from app.domains.mobile.schemas import SessionCreate as MobileSessionCreate
from app.domains.tspm import flow_regression_service as flow_regression_svc
from app.domains.tspm.schemas import RegressionSuggestRequest

router = APIRouter(prefix="/automation", tags=["automation"])

ENGINE_BASE = (os.environ.get("ENGINE_BASE_URL") or settings.engine_base_url).rstrip("/")
_INTERNAL_KEY = os.environ.get("ENGINE_INTERNAL_KEY") or settings.engine_internal_key

# ── Proxy güvenlik sabitleri ───────────────────────────────────────────────────

_ALLOWED_PROXY_METHODS = {"GET", "POST", "PUT", "DELETE", "PATCH"}

# İzin verilen proxy path'leri — engine'in güvenli API yüzeyi
_ALLOWED_PROXY_PATHS_PREFIX = (
    "api/features",     # feature file listesi / içeriği
    "api/run",          # test çalıştırma
    "api/results",      # sonuçlar
    "api/suites",       # test suite'leri
    "api/llm-agent",    # LLM ReAct browser ajanı
    "api/warmup",       # pool ısıtma
    "api/sessions",     # oturum yönetimi
    "health",           # sağlık kontrolü
)

# Frontend → Engine'e iletilecek header'lar (Authorization dahil değil — engine internal key kullanır)
_FORWARDED_REQUEST_HEADERS = {
    "content-type",
    "accept",
    "accept-encoding",
    "accept-language",
    "cache-control",
    "x-request-id",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _map_suite_status(status: str) -> str:
    if status == "error":
        return "failed"
    if status in {"queued", "running", "passed", "failed", "cancelled"}:
        return status
    return "failed"


def _merge_metrics(run: AutomationRunOut, values: dict[str, Any]) -> dict[str, Any]:
    return {**run.metrics, **{key: value for key, value in values.items() if value is not None}}


def _sync_external_suite_run(
    service: AutomationBrainService,
    run: AutomationRunOut,
) -> AutomationRunOut:
    """Pull automation-suite status into the normalized run contract."""
    external_run_id = run.metrics.get("external_run_id")
    if run.metrics.get("external_runner") != "automation_suite" or not isinstance(external_run_id, str):
        return run

    suite_status = suite_service.get_run_status(external_run_id)
    if suite_status is None:
        return run

    artifacts = list(run.artifacts)
    if suite_status.report_url and not any(item.get("url") == suite_status.report_url for item in artifacts):
        artifacts.append(
            {
                "type": "report",
                "label": "Automation Suite raporu",
                "url": suite_status.report_url,
            }
        )

    updated = run.model_copy(
        update={
            "status": _map_suite_status(suite_status.status),
            "started_at": suite_status.started_at or run.started_at,
            "finished_at": suite_status.completed_at or run.finished_at,
            "duration_ms": suite_status.duration_ms or run.duration_ms,
            "error": suite_status.error or run.error,
            "artifacts": artifacts,
            "metrics": _merge_metrics(
                run,
                {
                    "external_status": suite_status.status,
                    "passed": suite_status.passed,
                    "failed": suite_status.failed,
                    "framework": suite_status.framework,
                    "last_synced_at": _utcnow().isoformat(),
                },
            ),
        },
    )
    return service.store.replace(updated)


def _sync_external_mobile_run(
    service: AutomationBrainService,
    run: AutomationRunOut,
) -> AutomationRunOut:
    session_ids = run.metrics.get("external_session_ids")
    if run.metrics.get("external_runner") != "mobile_farm" or not isinstance(session_ids, list):
        return run

    sessions = [
        get_mobile_store().get(session_id)
        for session_id in session_ids
        if isinstance(session_id, str)
    ]
    sessions = [session for session in sessions if session is not None]
    if not sessions:
        return run

    statuses = [session.status for session in sessions]
    terminal = {"passed", "failed", "cancelled"}
    if any(status in {"queued", "running"} for status in statuses):
        status = "running"
    elif statuses and all(status == "passed" for status in statuses):
        status = "passed"
    elif statuses and all(status == "cancelled" for status in statuses):
        status = "cancelled"
    elif any(status == "failed" for status in statuses):
        status = "failed"
    else:
        status = "running"

    finished_times = [
        session.finished_at
        for session in sessions
        if session.finished_at is not None and session.status in terminal
    ]
    finished_at = max(finished_times) if len(finished_times) == len(sessions) else run.finished_at
    duration_ms = run.duration_ms
    if finished_at and run.started_at:
        duration_ms = int((finished_at - run.started_at).total_seconds() * 1000)

    updated = run.model_copy(
        update={
            "status": status,
            "finished_at": finished_at,
            "duration_ms": duration_ms,
            "error": next((session.failure_message for session in sessions if session.failure_message), run.error),
            "metrics": _merge_metrics(
                run,
                {
                    "external_status": status,
                    "session_count": len(sessions),
                    "passed_sessions": sum(1 for item in sessions if item.status == "passed"),
                    "failed_sessions": sum(1 for item in sessions if item.status == "failed"),
                    "running_sessions": sum(1 for item in sessions if item.status == "running"),
                    "cancelled_sessions": sum(1 for item in sessions if item.status == "cancelled"),
                    "device_ids": [item.device_id for item in sessions],
                    "last_synced_at": _utcnow().isoformat(),
                },
            ),
        },
    )
    return service.store.replace(updated)


def _sync_external_run(service: AutomationBrainService, run: AutomationRunOut) -> AutomationRunOut:
    run = _sync_external_suite_run(service, run)
    return _sync_external_mobile_run(service, run)


def _api_test_case_ids(run: AutomationRunOut) -> list[str]:
    raw_ids = run.metadata.get("test_case_ids")
    if isinstance(raw_ids, list):
        return [str(item) for item in raw_ids if str(item).strip()]
    if run.target:
        return [item.strip() for item in run.target.split(",") if item.strip()]
    return []


async def _start_web_suite_run(
    service: AutomationBrainService,
    run: AutomationRunOut,
) -> AutomationRunOut:
    if run.kind != "web" or not run.target:
        return run

    try:
        suite_run = await suite_service.start_run(
            SuiteRunRequest(
                feature_path=run.target,
                framework="playwright",
                headless=True,
                tags=[],
            )
        )
    except Exception as exc:  # pragma: no cover - defensive bridge around external runner
        logger.exception("Automation Brain web run could not start for %s", run.target)
        failed = run.model_copy(
            update={
                "status": "failed",
                "provenance": "fallback",
                "finished_at": _utcnow(),
                "error": f"Web runner başlatılamadı: {exc}",
            },
        )
        return service.store.replace(failed)

    started = run.model_copy(
        update={
            "status": "running",
            "provenance": "real",
            "started_at": _utcnow(),
            "metrics": _merge_metrics(
                run,
                {
                    "external_runner": "automation_suite",
                    "external_run_id": suite_run.run_id,
                    "external_status": suite_run.status,
                    "framework": "playwright",
                },
            ),
            "next_action": {
                "type": "open_runner_status",
                "label": "Runner durumunu aç",
                "href": f"/p/{run.project_id}/automation",
                "api": f"/api/v1/automation-suite/runs/{suite_run.run_id}",
            },
        },
    )
    return service.store.replace(started)


async def _start_api_test_run(
    service: AutomationBrainService,
    run: AutomationRunOut,
    db: Session,
) -> AutomationRunOut:
    test_case_ids = _api_test_case_ids(run)
    if not test_case_ids:
        failed = run.model_copy(
            update={
                "status": "failed",
                "provenance": "fallback",
                "finished_at": _utcnow(),
                "error": "API koşumu için metadata.test_case_ids veya target zorunlu",
            },
        )
        return service.store.replace(failed)

    try:
        result = await api_testing_service.execute_test_cases(
            db,
            run.project_id,
            test_case_ids,
            environment_id=run.metadata.get("environment_id"),
            stop_on_failure=bool(run.metadata.get("stop_on_failure", False)),
        )
    except Exception as exc:  # pragma: no cover - defensive bridge around API executor
        logger.exception("Automation Brain API run could not start")
        failed = run.model_copy(
            update={
                "status": "failed",
                "provenance": "fallback",
                "finished_at": _utcnow(),
                "error": f"API test runner başlatılamadı: {exc}",
            },
        )
        return service.store.replace(failed)

    total = int(result.get("total") or 0)
    failed_count = int(result.get("failed") or 0)
    error_count = int(result.get("errors") or 0)
    run_id = str(result.get("run_id") or "")
    status = "passed" if total > 0 and failed_count == 0 and error_count == 0 else "failed"
    error = None if run_id else "Eşleşen API test case bulunamadı"
    completed = run.model_copy(
        update={
            "status": status,
            "provenance": "real" if run_id else "fallback",
            "started_at": run.started_at or _utcnow(),
            "finished_at": _utcnow(),
            "duration_ms": int(float(result.get("duration_ms") or 0)),
            "error": error,
            "metrics": _merge_metrics(
                run,
                {
                    "external_runner": "api_testing",
                    "external_run_id": run_id or None,
                    "external_status": "completed" if run_id else "empty",
                    "test_case_ids": test_case_ids,
                    "total": total,
                    "passed": int(result.get("passed") or 0),
                    "failed": failed_count,
                    "errors": error_count,
                },
            ),
            "next_action": {
                "type": "open_api_testing",
                "label": "API koşum detayını aç",
                "href": f"/p/{run.project_id}/api-testing",
                "api": f"/api/v1/api-testing/projects/{run.project_id}/executions/{run_id}" if run_id else None,
            },
        },
    )
    return service.store.replace(completed)


async def _start_mobile_farm_run(
    service: AutomationBrainService,
    run: AutomationRunOut,
) -> AutomationRunOut:
    metadata = run.metadata
    prompt = str(
        metadata.get("mobile_prompt")
        or metadata.get("prompt")
        or "Uygulamayı aç, ana ekranın görünür olduğunu doğrula ve temel smoke kontrolünü tamamla."
    )
    platform = metadata.get("platform") if metadata.get("platform") in {"android", "ios", "both"} else "both"
    mode = metadata.get("mode") if metadata.get("mode") in {"simulation", "appium"} else "simulation"
    parallel_raw = metadata.get("parallel", 2)
    try:
        parallel = max(1, min(2, int(parallel_raw)))
    except (TypeError, ValueError):
        parallel = 2
    device_ids = metadata.get("device_ids")
    if not isinstance(device_ids, list):
        device_ids = [run.device] if run.device and not run.device.startswith("auto") else None
    raw_steps = metadata.get("steps")
    steps = raw_steps if isinstance(raw_steps, list) else [
        AppiumAction(action="launch"),
        AppiumAction(action="wait", ms=500),
        AppiumAction(action="verifyVisible", value="home"),
    ]

    try:
        sessions = await start_mobile_suite(
            MobileSessionCreate(
                scenario_name=run.name,
                prompt=prompt,
                platform=platform,  # type: ignore[arg-type]
                parallel=parallel,
                device_ids=device_ids,
                mode=mode,  # type: ignore[arg-type]
                steps=steps,  # type: ignore[arg-type]
                app=metadata.get("app") if isinstance(metadata.get("app"), dict) else None,
            )
        )
    except Exception as exc:  # pragma: no cover - defensive bridge around external runner
        logger.exception("Automation Brain mobile run could not start")
        failed = run.model_copy(
            update={
                "status": "failed",
                "provenance": "fallback",
                "finished_at": _utcnow(),
                "error": f"Mobile farm başlatılamadı: {exc}",
            },
        )
        return service.store.replace(failed)

    if not sessions:
        failed = run.model_copy(
            update={
                "status": "failed",
                "provenance": "fallback",
                "finished_at": _utcnow(),
                "error": "Uygun mobil cihaz bulunamadı",
            },
        )
        return service.store.replace(failed)

    started = run.model_copy(
        update={
            "status": "running",
            "provenance": "real",
            "started_at": _utcnow(),
            "metrics": _merge_metrics(
                run,
                {
                    "external_runner": "mobile_farm",
                    "external_session_ids": [session.id for session in sessions],
                    "external_status": "running",
                    "session_count": len(sessions),
                    "device_ids": [session.device_id for session in sessions],
                    "mode": mode,
                    "platform": platform,
                },
            ),
            "next_action": {
                "type": "open_mobile_farm",
                "label": "Mobil farmı aç",
                "href": f"/p/{run.project_id}/mobile",
                "api": "/api/v1/mobile/sessions",
            },
        },
    )
    return service.store.replace(started)


async def _start_regression_suggestion_run(
    service: AutomationBrainService,
    run: AutomationRunOut,
    db: Session,
) -> AutomationRunOut:
    instructions = str(
        run.metadata.get("extra_instructions")
        or run.metadata.get("instructions")
        or "E2E smoke, kritik kullanıcı akışları ve son hata risklerini öne çıkar."
    )

    try:
        result = flow_regression_svc.suggest_regression_sets_for_project(
            db,
            run.project_id,
            RegressionSuggestRequest(extra_instructions=instructions),
        )
    except Exception as exc:  # pragma: no cover - defensive bridge around regression service
        logger.exception("Automation Brain regression suggestion could not run")
        failed = run.model_copy(
            update={
                "status": "failed",
                "provenance": "fallback",
                "finished_at": _utcnow(),
                "error": f"Regression önerisi üretilemedi: {exc}",
            },
        )
        return service.store.replace(failed)

    sets = [item.model_dump() if hasattr(item, "model_dump") else dict(item) for item in result.sets]
    scenario_ids = {
        scenario_id
        for item in sets
        for scenario_id in item.get("scenario_ids", [])
        if isinstance(scenario_id, str)
    }
    completed = run.model_copy(
        update={
            "status": "passed",
            "provenance": "real",
            "started_at": run.started_at or _utcnow(),
            "finished_at": _utcnow(),
            "metrics": _merge_metrics(
                run,
                {
                    "external_runner": "regression_suggester",
                    "external_status": "completed",
                    "suggested_sets": sets,
                    "suggested_set_count": len(sets),
                    "covered_scenario_count": len(scenario_ids),
                },
            ),
            "next_action": {
                "type": "open_regression",
                "label": "Regresyon önerilerini aç",
                "href": f"/p/{run.project_id}/regression",
                "api": f"/api/v1/tspm/projects/{run.project_id}/regression-sets/suggest",
            },
        },
    )
    return service.store.replace(completed)


def _normalize_proxy_path(path: str) -> str:
    """Proxy path'ini normalize et: baştaki slash'ı temizle."""
    return path.lstrip("/")


def _is_allowed_proxy_path(path: str) -> bool:
    """Engine'e proxy'lenebilecek path'ler için beyaz liste kontrolü."""
    normalized = path.lstrip("/")
    return any(normalized.startswith(prefix) for prefix in _ALLOWED_PROXY_PATHS_PREFIX)


@router.get("/health")
async def engine_health():
    """Check automation engine health."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(
                f"{ENGINE_BASE}/health",
                headers={"X-Internal-Key": _INTERNAL_KEY},
            )
            return resp.json()
    except httpx.RequestError:
        logger.warning("Automation engine health check failed for %s", ENGINE_BASE)
        return {"status": "unreachable", "engine_url": ENGINE_BASE}


@router.get(
    "/brain",
    response_model=AutomationBrainSummary,
    dependencies=[Depends(get_current_user)],
)
async def automation_brain_summary(
    project_id: str | None = None,
    db: Session = Depends(get_db),
):
    """Return the central automation brain summary."""
    service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
    for run in service.list_runs(project_id=project_id, limit=100).items:
        _sync_external_run(service, run)
    return service.summary(project_id=project_id)


@router.get(
    "/brain/capabilities",
    response_model=list[AutomationCapability],
    dependencies=[Depends(get_current_user)],
)
async def automation_brain_capabilities():
    """List automation adapters known by the brain."""
    return brain_service.capabilities()


@router.post(
    "/runs",
    response_model=AutomationRunOut,
    dependencies=[Depends(get_current_user)],
)
async def create_automation_run(
    payload: AutomationRunCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a normalized automation run envelope."""
    service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
    run = service.create_run(payload, created_by=str(user.id))
    if payload.execute_now and payload.kind == "web" and payload.target:
        return await _start_web_suite_run(service, run)
    if payload.execute_now and payload.kind == "api":
        return await _start_api_test_run(service, run, db)
    if payload.execute_now and payload.kind == "mobile":
        return await _start_mobile_farm_run(service, run)
    if payload.execute_now and payload.kind == "regression":
        return await _start_regression_suggestion_run(service, run, db)
    return run


@router.get(
    "/runs",
    response_model=AutomationRunList,
    dependencies=[Depends(get_current_user)],
)
async def list_automation_runs(
    project_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List normalized automation runs."""
    service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
    runs = service.list_runs(project_id=project_id, limit=limit)
    return AutomationRunList(
        items=[_sync_external_run(service, run) for run in runs.items],
        total=runs.total,
    )


@router.get(
    "/runs/{run_id}",
    response_model=AutomationRunOut,
    dependencies=[Depends(get_current_user)],
)
async def get_automation_run(run_id: str, db: Session = Depends(get_db)):
    """Get a normalized automation run."""
    service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Automation run bulunamadı")
    return _sync_external_run(service, run)


@router.post(
    "/runs/{run_id}/cancel",
    response_model=AutomationRunOut,
    dependencies=[Depends(get_current_user)],
)
async def cancel_automation_run(run_id: str, db: Session = Depends(get_db)):
    """Cancel a queued/running automation run."""
    service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
    run = service.cancel_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Automation run bulunamadı")
    session_ids = run.metrics.get("external_session_ids")
    if run.metrics.get("external_runner") == "mobile_farm" and isinstance(session_ids, list):
        store = get_mobile_store()
        for session_id in session_ids:
            if isinstance(session_id, str):
                store.update(session_id, status="cancelled", finished_at=_utcnow())
    return run


@router.post(
    "/runs/{run_id}/retry",
    response_model=AutomationRunOut,
    dependencies=[Depends(get_current_user)],
)
async def retry_automation_run(
    run_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a retry run using the same normalized contract."""
    service = AutomationBrainService(SqlAlchemyAutomationRunStore(db))
    run = service.retry_run(run_id, created_by=str(user.id))
    if run is None:
        raise HTTPException(status_code=404, detail="Automation run bulunamadı")
    return run


@router.api_route(
    "/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
    include_in_schema=False,
    dependencies=[Depends(get_current_user)],
)
async def _proxy_to_engine(path: str, request: Request):
    """
    Transparent proxy to the automation engine.
    Frontend calls  /api/v1/automation/proxy/api/features
    and this forwards to ENGINE_BASE/api/features.
    """
    if request.method.upper() not in _ALLOWED_PROXY_METHODS:
        raise HTTPException(status_code=405, detail="Method desteklenmiyor")

    normalized_path = _normalize_proxy_path(path)
    if not _is_allowed_proxy_path(normalized_path):
        raise HTTPException(status_code=403, detail="Bu proxy path'e izin verilmiyor")

    target = f"{ENGINE_BASE.rstrip('/')}/{normalized_path}"
    headers = {
        k: v
        for k, v in request.headers.items()
        if k.lower() in _FORWARDED_REQUEST_HEADERS
    }
    headers["x-internal-key"] = _INTERNAL_KEY

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(
            method=request.method,
            url=target,
            headers=headers,
            params=request.query_params,
            content=await request.body(),
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers),
    )


@router.get(
    "/proxy/{path:path}",
    operation_id="automation_proxy_get",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_get(path: str, request: Request):
    """GET isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.post(
    "/proxy/{path:path}",
    operation_id="automation_proxy_post",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_post(path: str, request: Request):
    """POST isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.put(
    "/proxy/{path:path}",
    operation_id="automation_proxy_put",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_put(path: str, request: Request):
    """PUT isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.delete(
    "/proxy/{path:path}",
    operation_id="automation_proxy_delete",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_delete(path: str, request: Request):
    """DELETE isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)


@router.patch(
    "/proxy/{path:path}",
    operation_id="automation_proxy_patch",
    dependencies=[Depends(get_current_user)],
)
async def proxy_to_engine_patch(path: str, request: Request):
    """PATCH isteklerini otomasyon motoruna yonlendirir."""
    return await _proxy_to_engine(path, request)
