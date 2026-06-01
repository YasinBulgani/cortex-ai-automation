"""N8N — thin service facade for n8n workflow integration.

HTTP-agnostic. Raises ValueError/KeyError instead of HTTPException.
Wraps n8n REST API calls and local TspmN8nWorkflow/Execution models.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domains.tspm.models import TspmN8nExecution, TspmN8nWorkflow

logger = logging.getLogger(__name__)

_N8N_BASE = os.environ.get("N8N_BASE_URL", "http://localhost:5678")
_N8N_API_KEY = os.environ.get("N8N_API_KEY", "")


def _n8n_headers() -> Dict[str, str]:
    h = {"Content-Type": "application/json"}
    if _N8N_API_KEY:
        h["X-N8N-API-KEY"] = _N8N_API_KEY
    return h


def list_workflows() -> List[Dict[str, Any]]:
    """Fetch available workflows from the n8n REST API.

    Returns:
        List of workflow dicts from n8n.

    Raises:
        ValueError: N8N_API_KEY not configured or n8n unreachable.
    """
    if not _N8N_API_KEY:
        raise ValueError("N8N_API_KEY yapılandırılmamış — n8n entegrasyonu devre dışı.")

    try:
        with httpx.Client(timeout=10) as client:
            resp = client.get(f"{_N8N_BASE}/api/v1/workflows", headers=_n8n_headers())
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", data) if isinstance(data, dict) else data
    except httpx.HTTPError as exc:
        raise ValueError(f"n8n bağlantı hatası: {exc}") from exc


def trigger_workflow(
    db: Session,
    workflow_link_id: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Trigger a linked n8n workflow via its webhook URL.

    Args:
        db: SQLAlchemy session.
        workflow_link_id: TspmN8nWorkflow.id in the local DB.
        payload: Data to send to the n8n webhook.

    Returns:
        Dict with execution tracking info.

    Raises:
        KeyError: Workflow link not found.
        ValueError: Webhook URL missing or n8n call fails.
    """
    wf = db.get(TspmN8nWorkflow, workflow_link_id)
    if wf is None:
        raise KeyError(f"N8N workflow link '{workflow_link_id}' bulunamadı.")

    webhook_url: str = ""
    if isinstance(wf.config, dict):
        webhook_url = str(wf.config.get("webhook_url", "")).strip()
    if not webhook_url:
        raise ValueError(f"Workflow '{workflow_link_id}' için webhook_url yapılandırılmamış.")

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(webhook_url, json=payload or {})
            resp.raise_for_status()
            result = resp.json() if resp.content else {}
    except httpx.HTTPError as exc:
        raise ValueError(f"n8n webhook çağrısı başarısız: {exc}") from exc

    logger.info("N8N workflow tetiklendi: %s", workflow_link_id)
    return {"workflow_link_id": workflow_link_id, "n8n_response": result}


def get_execution(db: Session, execution_id: str) -> Dict[str, Any]:
    """Fetch a single n8n execution record from the local DB.

    Args:
        db: SQLAlchemy session.
        execution_id: TspmN8nExecution.id.

    Returns:
        Execution dict.

    Raises:
        KeyError: Execution not found.
    """
    ex = db.get(TspmN8nExecution, execution_id)
    if ex is None:
        raise KeyError(f"N8N execution '{execution_id}' bulunamadı.")
    return {c.key: getattr(ex, c.key) for c in ex.__table__.columns}
