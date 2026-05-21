"""FastAPI Router — /api/v1/agents/v2/*"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import StreamingResponse

from app.config import settings
from app.deps import get_current_user
from app.infra.models import User

from .api_schemas import (
    RunAgentV2Request, RunAgentV2Response,
    RunV2ListItem, RunV2ListResponse, RunV2Status,
)
from .config import get_config
from .budget_guard import clear_cancel, raise_if_cancelled, request_cancel
from .orchestrator import LANGGRAPH_AVAILABLE
from .run_store import get_run_store
from .state import AgentState
from .tools.ai_gateway import get_gateway_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/v2", tags=["agents-v2"])


class WorkflowValidationError(RuntimeError):
    """Terminal workflow error for failed structured-output validation."""


@router.post(
    "/run",
    response_model=RunAgentV2Response,
    status_code=status.HTTP_202_ACCEPTED,
)
async def run_agent(
    body: RunAgentV2Request,
    background: BackgroundTasks,
    request: Request,
):
    input_payload = _build_payload(body)
    if not input_payload:
        raise HTTPException(
            status_code=400,
            detail="Kaynak belirtilmemiş. url/file_path/text/swagger_url gerekli.",
        )

    tenant_id = getattr(request.state, "tenant_id", "default")
    user_id = getattr(request.state, "user_id", "anonymous")

    cfg = get_config()
    if body.auto_pr:
        cfg.auto_pr_enabled = True
    if body.auto_merge:
        cfg.auto_merge_enabled = True
    if body.enable_ai_xpath:
        cfg.vision_enabled = True

    store = get_run_store()
    run_id, initial_state = store.create(
        project_id=body.project_id,
        user_id=user_id,
        tenant_id=tenant_id,
        input_source=body.input_source,
        input_payload=input_payload,
    )

    store.update_status(run_id, "queued")
    store.publish(run_id, {
        "event_type": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "message": "Pipeline kuyruğa eklendi",
    })

    background.add_task(_execute_pipeline, run_id, initial_state)

    return RunAgentV2Response(
        run_id=run_id,
        status="queued",
        created_at=datetime.utcnow(),
        stream_url=f"/api/v1/agents/v2/runs/{run_id}/stream",
        detail_url=f"/api/v1/agents/v2/runs/{run_id}",
    )


@router.get("/runs", response_model=RunV2ListResponse)
async def list_runs(
    project_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
    request: Request = None,  # type: ignore[assignment]
):
    tenant_id = getattr(request.state, "tenant_id", None) if request else None
    store = get_run_store()
    records = store.list(project_id=project_id, tenant_id=tenant_id, limit=page * page_size)

    start = (page - 1) * page_size
    end = start + page_size
    page_items = records[start:end]

    items = [
        RunV2ListItem(
            run_id=r.run_id,
            project_id=r.project_id,
            status=r.status,
            input_source=r.input_source,
            created_at=r.created_at,
            completed_at=r.completed_at,
            cost_usd=r.state.get("cost_usd", 0.0) if r.state else 0.0,
            scenario_count=sum(
                s.get("scenario_count", 0) if isinstance(s, dict) else 0
                for s in (r.state.get("scenarios", []) if r.state else [])
            ),
            passed_count=(
                (r.state.get("run_result") or {}).get("passed_count", 0)
                if r.state else 0
            ),
            failed_count=(
                (r.state.get("run_result") or {}).get("failed_count", 0)
                if r.state else 0
            ),
        )
        for r in page_items
    ]
    return RunV2ListResponse(runs=items, total=len(records), page=page, page_size=page_size)


@router.get("/runs/{run_id}", response_model=RunV2Status)
async def get_run(run_id: str):
    store = get_run_store()
    rec = store.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Run bulunamadı: {run_id}")
    return RunV2Status(**rec.to_status_dict())


@router.get("/runs/{run_id}/stream")
async def stream_run(run_id: str):
    store = get_run_store()
    rec = store.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Run bulunamadı: {run_id}")

    async def event_stream() -> AsyncIterator[str]:
        for evt in rec.events:
            yield f"event: {evt.get('event_type', 'message')}\ndata: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"

        queue = store.subscribe(run_id)
        try:
            while True:
                if rec.status in ("completed", "failed", "failed_validation", "cancelled"):
                    yield f"event: final\ndata: {json.dumps(rec.to_status_dict(), ensure_ascii=False, default=str)}\n\n"
                    break
                try:
                    evt = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"event: {evt.get('event_type', 'message')}\ndata: {json.dumps(evt, ensure_ascii=False, default=str)}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        finally:
            store.unsubscribe(run_id, queue)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/runs/{run_id}/cancel")
async def cancel_run(run_id: str):
    store = get_run_store()
    rec = store.get(run_id)
    if not rec:
        raise HTTPException(status_code=404, detail=f"Run bulunamadı: {run_id}")
    if rec.status in ("completed", "failed", "cancelled"):
        return {"run_id": run_id, "status": rec.status, "message": "Zaten bitmiş"}
    state = dict(rec.state or {})
    state["cancelled"] = True
    store.update_state(run_id, state)
    request_cancel(run_id)
    store.update_status(run_id, "cancelled", "Kullanıcı iptal etti")
    store.publish(run_id, {
        "event_type": "failed",
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "message": "Kullanıcı iptal etti",
    })
    return {"run_id": run_id, "status": "cancelled"}


# ── Dosya yükleme (PDF/DOCX vb.) ──────────────────────────────────────────
_ALLOWED_UPLOAD_SUFFIXES = {".pdf", ".docx", ".md", ".txt", ".csv", ".json"}
_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


# Rate limiting dekoratoru — auth router'ındaki pattern ile tutarlı.
# slowapi yoksa no-op wrapper dönülür.
try:
    from app.main import limiter as _limiter  # type: ignore

    _has_limiter = _limiter is not None
except (ImportError, AttributeError):
    _limiter = None
    _has_limiter = False


def _rate_limit(rate: str):
    if _has_limiter and _limiter is not None:
        return _limiter.limit(rate)

    def _noop(func):
        return func

    return _noop


@router.post("/upload", status_code=status.HTTP_201_CREATED)
@_rate_limit("10/minute")
async def upload_source_file(
    request: Request,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Sıfır-bilgi pipeline için kaynak dosya yükler.

    Frontend (`sıfır-bilgi/page.tsx`) bu uca multipart/form-data ile dosya
    gönderir; dönen `file_path` alanını `startAgentRun({file_path})`
    çağrısında kullanır.

    Güvenlik:
      * **Auth**: `get_current_user` ile JWT zorunlu — anonymous upload yok.
      * **Rate limit**: `10/minute` per-IP (slowapi kurulu ise).
      * **Uzantı whitelist**: `_ALLOWED_UPLOAD_SUFFIXES`.
      * **Boyut limiti**: 20 MB. Limitin üstü 413 ile reddedilir.
      * **Path traversal koruması**: Dosya adı UUID ile yeniden adlandırılır.
    """
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in _ALLOWED_UPLOAD_SUFFIXES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Desteklenmeyen dosya uzantısı: {suffix or '(boş)'}. "
                f"İzin verilenler: {sorted(_ALLOWED_UPLOAD_SUFFIXES)}"
            ),
        )

    # Büyük dosyalarda tüm içeriği belleğe almayalım
    upload_dir = Path(settings.artifacts_dir) / "agents_v2_uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    new_name = f"{uuid.uuid4().hex}{suffix}"
    target = upload_dir / new_name

    bytes_written = 0
    try:
        with target.open("wb") as fp:
            while True:
                chunk = await file.read(1024 * 1024)  # 1 MB
                if not chunk:
                    break
                bytes_written += len(chunk)
                if bytes_written > _MAX_UPLOAD_BYTES:
                    fp.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Dosya çok büyük (limit {_MAX_UPLOAD_BYTES // (1024*1024)} MB).",
                    )
                fp.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Yükleme başarısız: {exc}",
        )

    logger.info(
        "agents_v2 upload: user=%s size=%d name=%s",
        getattr(user, "email", "?"),
        bytes_written,
        file.filename,
    )

    return {
        "file_path": str(target),
        "original_name": file.filename,
        "size_bytes": bytes_written,
        "suffix": suffix,
    }


_AGENT_CATALOG = [
    {"id": "monkey-testing",     "name": "Monkey Testing",        "category": "test-quality",   "availability": "active",       "tagline": "Rastgele tıklama ile UI keşfi"},
    {"id": "self-healing",       "name": "Self-Healing",          "category": "test-quality",   "availability": "active",       "tagline": "Otomatik test onarımı"},
    {"id": "smart-locator",      "name": "Smart Locator",         "category": "test-quality",   "availability": "active",       "tagline": "XPath / CSS otomatik bulma"},
    {"id": "coverage-analysis",  "name": "Coverage Analysis",     "category": "code-analysis",  "availability": "active",       "tagline": "Test kapsama boşluk analizi"},
    {"id": "bdd-generator",      "name": "BDD Generator",         "category": "test-quality",   "availability": "active",       "tagline": "Gherkin senaryo üretimi"},
    {"id": "synthetic-data",     "name": "Synthetic Data",        "category": "data",           "availability": "active",       "tagline": "KVKK-uyumlu test verisi"},
    {"id": "ai-test-generator",  "name": "AI Test Generator",     "category": "automation",     "availability": "active",       "tagline": "URL'den otomatik test üretimi"},
    {"id": "regression-suite",   "name": "Regression Suite",      "category": "automation",     "availability": "beta",         "tagline": "Otomatik regresyon paketi"},
    {"id": "otel-trace",         "name": "OTel Trace Analyzer",   "category": "observability",  "availability": "experimental", "tagline": "Trace anomali tespiti"},
    {"id": "banking-safety",     "name": "Banking Safety Guard",  "category": "test-quality",   "availability": "active",       "tagline": "BRSA uyumluluk kontrolleri"},
]


@router.get("/catalog", response_model=list[dict])
async def agents_v2_catalog(
    _user: User = Depends(get_current_user),
):
    """Kullanılabilir AI agent kataloğunu döndürür."""
    return _AGENT_CATALOG


@router.get("/health")
async def agents_v2_health():
    gw = get_gateway_client()
    gateway_ok = False
    try:
        gateway_ok = await gw.ping()
    except Exception:
        gateway_ok = False

    return {
        "status": "ok",
        "langgraph_available": LANGGRAPH_AVAILABLE,
        "ai_gateway_reachable": gateway_ok,
        "active_runs": sum(1 for r in get_run_store().list() if r.status == "running"),
    }


def _build_payload(body: RunAgentV2Request) -> dict | None:
    payload: dict = {}
    if body.url:
        payload["url"] = body.url
    if body.file_path:
        payload["path"] = body.file_path
    if body.text:
        payload["text"] = body.text
    if body.swagger_url:
        payload["swagger_url"] = body.swagger_url
        if not payload.get("url"):
            payload["url"] = body.swagger_url
    if body.extra_context:
        payload["extra_context"] = body.extra_context
    if body.credentials:
        payload["credentials"] = body.credentials
    if body.allowed_hosts:
        payload["allowed_hosts"] = body.allowed_hosts
    payload["max_pages"] = body.max_pages
    payload["max_depth"] = body.max_depth

    if not any([body.url, body.file_path, body.text, body.swagger_url]):
        return None
    return payload


async def _execute_pipeline(run_id: str, initial_state: AgentState) -> None:
    store = get_run_store()
    store.update_status(run_id, "running")
    store.publish(run_id, {
        "event_type": "started",
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "message": "Pipeline başladı",
    })

    try:
        raise_if_cancelled(initial_state, agent_name="pipeline")
        final_state = await _execute_manual(run_id, initial_state)
        raise_if_cancelled(final_state, agent_name="pipeline")
        store.update_state(run_id, final_state)
        try:
            from app.domains.ai.workflows_router import register_state_artifacts

            register_state_artifacts(run_id, final_state)
        except Exception as artifact_exc:
            logger.warning("Workflow artifact registration failed: %s", artifact_exc)
        store.update_status(run_id, "completed")
        store.publish(run_id, {
            "event_type": "completed",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "data": {
                "cost_usd": final_state.get("cost_usd", 0.0),
                "tokens_used": final_state.get("tokens_used", 0),
            },
        })
        clear_cancel(run_id)
    except asyncio.CancelledError as exc:
        logger.info("Pipeline iptal edildi: %s", exc)
        rec = store.get(run_id)
        state = dict((rec.state if rec else initial_state) or {})
        state["cancelled"] = True
        state["status"] = "cancelled"
        store.update_state(run_id, state)
        store.update_status(run_id, "cancelled", str(exc) or "Kullanıcı iptal etti")
        store.publish(run_id, {
            "event_type": "cancelled",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "message": str(exc) or "Kullanıcı iptal etti",
        })
        clear_cancel(run_id)
    except Exception as exc:
        logger.exception("Pipeline hata: %s", exc)
        failed_validation = isinstance(exc, WorkflowValidationError)
        terminal_status = "failed_validation" if failed_validation else "failed"
        store.update_status(run_id, terminal_status, str(exc))
        store.publish(run_id, {
            "event_type": terminal_status,
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "message": str(exc),
        })
        clear_cancel(run_id)


async def _execute_manual(run_id: str, state: AgentState) -> AgentState:
    store = get_run_store()
    from .agents import (
        analyst_node, explorer_node, locator_node, scenario_node,
        coder_node, runner_node, healer_node, reviewer_node, reporter_node,
    )

    async def _step(name: str, fn, st: AgentState) -> AgentState:
        raise_if_cancelled(st, agent_name=name)
        store.publish(run_id, {
            "event_type": "agent_started",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "agent_name": name,
        })
        try:
            new_state = await fn(st)
            raise_if_cancelled(new_state, agent_name=name)
        except Exception as exc:
            logger.exception("Agent %s: %s", name, exc)
            store.publish(run_id, {
                "event_type": "error",
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": run_id,
                "agent_name": name,
                "message": str(exc),
            })
            raise
        validation_error = _failed_validation_error(new_state)
        if validation_error:
            store.publish(run_id, {
                "event_type": "failed_validation",
                "timestamp": datetime.utcnow().isoformat(),
                "run_id": run_id,
                "agent_name": name,
                "message": validation_error,
            })
            raise WorkflowValidationError(validation_error)
        store.publish(run_id, {
            "event_type": "agent_finished",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "agent_name": name,
            "data": {
                "cost_so_far": new_state.get("cost_usd", 0.0),
                "tokens_so_far": new_state.get("tokens_used", 0),
            },
        })
        store.update_state(run_id, new_state)
        return new_state

    state = await _step("analyst", analyst_node, state)

    if state.get("input_payload", {}).get("url"):
        state = await _step("explorer", explorer_node, state)
        state = await _step("locator", locator_node, state)

    state = await _step("scenario", scenario_node, state)
    state = await _step("coder", coder_node, state)
    state = await _step("runner", runner_node, state)

    if state.get("run_result", {}).get("failed_count", 0) > 0:
        state = await _step("healer", healer_node, state)

    state = await _step("reviewer", reviewer_node, state)
    state = await _step("reporter", reporter_node, state)

    state["status"] = "completed"
    state["completed_at"] = datetime.utcnow()
    return state


def _failed_validation_error(state: AgentState) -> str | None:
    for item in state.get("errors", []) or []:
        if not isinstance(item, dict):
            continue
        error_type = str(item.get("error_type") or "")
        message = str(item.get("error") or "")
        if error_type == "StructuredOutputValidationError":
            return message or error_type
        if "Structured output validation failed" in message:
            return message
    return None
