"""N8N Integration Router — webhook receiver + n8n API proxy.

TSPM router (/api/v1/tspm/projects/{id}/workflows) handles workflow CRUD.
This router adds:
  POST /n8n/webhook/{workflow_id}         - receive n8n execution result callback
  GET  /n8n/available-workflows            - proxy list from n8n REST API
"""

from __future__ import annotations

import hmac
import logging
import os
from datetime import datetime, timezone
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.deps import get_current_user
from app.domains.tspm.models import TspmN8nExecution, TspmN8nWorkflow
from app.infra.database import get_db
from app.infra.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/n8n", tags=["n8n"])

N8N_BASE = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.environ.get("N8N_API_KEY", "")
N8N_CALLBACK_TOKEN = os.environ.get("N8N_CALLBACK_TOKEN", "")

CurrentUser = Annotated[User, Depends(get_current_user)]


def _n8n_headers() -> dict:
    h = {"Content-Type": "application/json"}
    if N8N_API_KEY:
        h["X-N8N-API-KEY"] = N8N_API_KEY
    return h


def _callback_secret_required() -> bool:
    forced = os.environ.get("N8N_REQUIRE_CALLBACK_SECRET", "").lower() in {"1", "true", "yes"}
    return forced or settings.is_production_like


@router.post("/webhook/{workflow_id}")
async def receive_n8n_callback(
    workflow_id: str,
    request: Request,
    db: Session = Depends(get_db),
    x_n8n_token: str = Header(default=""),
):
    """Called by n8n to report execution result back to TestwrightAI."""
    wf = db.get(TspmN8nWorkflow, workflow_id)
    if not wf:
        raise HTTPException(404, "Workflow link not found")

    workflow_token = ""
    if isinstance(wf.config, dict):
        workflow_token = str(wf.config.get("callback_token", "")).strip()
    expected_token = workflow_token or N8N_CALLBACK_TOKEN
    if _callback_secret_required() and not expected_token:
        raise HTTPException(503, "n8n callback token zorunlu fakat ayarlanmamis")
    if expected_token and not hmac.compare_digest(x_n8n_token, expected_token):
        raise HTTPException(401, "Invalid n8n callback token")

    body: dict[str, Any] = {}
    try:
        body = await request.json()
    except ValueError as exc:
        logger.warning(
            "Invalid n8n callback payload for workflow %s: %s",
            workflow_id,
            exc,
        )

    n8n_exec_id = str(body.get("executionId", ""))
    ex = None
    if n8n_exec_id:
        ex = db.execute(
            select(TspmN8nExecution).where(
                TspmN8nExecution.workflow_link_id == workflow_id,
                TspmN8nExecution.n8n_execution_id == n8n_exec_id,
            )
        ).scalar_one_or_none()

    if not ex:
        ex = TspmN8nExecution(
            workflow_link_id=wf.id,
            n8n_execution_id=n8n_exec_id or None,
            status="running",
            input_data=body,
        )
        db.add(ex)
        db.flush()

    finished = body.get("finished", False)
    success = body.get("success", body.get("status") == "success")
    ex.status = "success" if (finished and success) else ("error" if finished else "running")
    ex.output_data = body.get("data", body)
    ex.error = body.get("error") or body.get("errorMessage")
    if finished:
        ex.finished_at = datetime.now(timezone.utc)

    db.commit()
    return {"ok": True, "execution_id": ex.id}


@router.get("/available-workflows")
async def list_available_n8n_workflows(_user: CurrentUser):
    """Fetch workflow list directly from n8n REST API."""
    if not N8N_API_KEY:
        return {"workflows": [], "note": "N8N_API_KEY not configured"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{N8N_BASE}/api/v1/workflows",
                headers=_n8n_headers(),
            )
            data = resp.json()
            return {"workflows": data.get("data", data)}
    except httpx.HTTPError as exc:
        logger.exception("Failed to fetch n8n workflows")
        return {"workflows": [], "error": str(exc)}
    except ValueError as exc:
        logger.exception("n8n returned invalid workflow payload")
        return {"workflows": [], "error": str(exc)}
