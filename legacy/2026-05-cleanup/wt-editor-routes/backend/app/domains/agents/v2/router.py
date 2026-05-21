"""FastAPI Router — /api/v1/agents/v2/*"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status
from fastapi.responses import StreamingResponse

from .api_schemas import (
    RunAgentV2Request, RunAgentV2Response,
    RunV2ListItem, RunV2ListResponse, RunV2Status,
)
from .config import get_config
from .orchestrator import LANGGRAPH_AVAILABLE
from .run_store import get_run_store
from .state import AgentState
from .tools.ai_gateway import get_gateway_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents/v2", tags=["agents-v2"])


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
                if rec.status in ("completed", "failed", "cancelled"):
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
    store.update_status(run_id, "cancelled", "Kullanıcı iptal etti")
    store.publish(run_id, {
        "event_type": "failed",
        "timestamp": datetime.utcnow().isoformat(),
        "run_id": run_id,
        "message": "Kullanıcı iptal etti",
    })
    return {"run_id": run_id, "status": "cancelled"}


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
        final_state = await _execute_manual(run_id, initial_state)
        store.update_state(run_id, final_state)
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
    except Exception as exc:
        logger.exception("Pipeline hata: %s", exc)
        store.update_status(run_id, "failed", str(exc))
        store.publish(run_id, {
            "event_type": "failed",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "message": str(exc),
        })


async def _execute_manual(run_id: str, state: AgentState) -> AgentState:
    store = get_run_store()
    from .agents import (
        analyst_node, explorer_node, locator_node, scenario_node,
        coder_node, runner_node, healer_node, reviewer_node, reporter_node,
    )

    async def _step(name: str, fn, st: AgentState) -> AgentState:
        store.publish(run_id, {
            "event_type": "agent_started",
            "timestamp": datetime.utcnow().isoformat(),
            "run_id": run_id,
            "agent_name": name,
        })
        try:
            new_state = await fn(st)
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
