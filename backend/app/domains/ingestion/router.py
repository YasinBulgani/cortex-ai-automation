"""Ingestion router — /api/v1/ingestion.

POST /ingestion/text                         — raw metin
POST /ingestion/jira/webhook                 — Jira webhook
POST /ingestion/confluence/webhook           — Confluence webhook
GET  /ingestion/projects/{project_id}        — proje requirements listesi
GET  /ingestion/{req_id}                     — detay
"""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Annotated, Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.deps import get_current_user
from app.domains.ingestion import service as svc
from app.infra.database import get_db
from app.infra.models import User
from sqlalchemy import func, select
from sqlalchemy.orm import Session

router = APIRouter(prefix="/ingestion", tags=["ingestion"])

CurrentUser = Annotated[User, Depends(get_current_user)]


class TextIngestIn(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1)
    source: str = "text"
    source_ref: Optional[str] = None


# ── Webhook HMAC signature verification ──────────────────────────────────────
# Webhooks (Jira, Confluence) use HMAC-SHA256 signature verification instead of user
# auth, since they are called by external services, not authenticated users.

def _webhook_secret_required() -> bool:
    from app.config import settings as _settings
    forced = os.environ.get("INGESTION_REQUIRE_WEBHOOK_SECRET", "").lower() in {"1", "true", "yes"}
    return forced or _settings.is_production_like


def _verify_webhook_signature(
    body: bytes,
    x_webhook_signature: str | None = Header(None, alias="x-webhook-signature"),
) -> None:
    """Verify webhook HMAC-SHA256 signature.

    Args:
        body: Raw request body bytes
        x_webhook_signature: X-Webhook-Signature header (sha256=<hex>)

    Raises:
        HTTPException: 503 if secret not configured but required, 401 if signature invalid
    """
    expected_secret = os.environ.get("WEBHOOK_SECRET", "")
    if _webhook_secret_required() and not expected_secret:
        raise HTTPException(503, "Webhook secret zorunlu ancak yapılandırılmamış (WEBHOOK_SECRET)")
    if expected_secret:
        if not x_webhook_signature:
            raise HTTPException(401, "Webhook signature başlığı eksik")
        expected = "sha256=" + hmac.new(expected_secret.encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(x_webhook_signature, expected):
            raise HTTPException(401, "Geçersiz webhook imzası")


@router.post("/text", status_code=status.HTTP_201_CREATED)
def ingest_text_endpoint(body: TextIngestIn, user: Annotated[User, Depends(get_current_user)]) -> dict:
    try:
        req = svc.ingest_text(
            project_id=body.project_id,
            title=body.title,
            body=body.body,
            source=body.source,
            source_ref=body.source_ref,
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return req.to_dict()


@router.post("/jira/webhook", status_code=status.HTTP_201_CREATED)
async def jira_webhook(
    request: Request,
    project_id: str,
    x_webhook_signature: Optional[str] = Header(None, alias="x-webhook-signature"),
) -> dict:
    """Jira webhook — `?project_id=` query param ile hedef proje belirlenir.

    Auth: HMAC-SHA256 signature verification via X-Webhook-Signature header.
    """
    body = await request.body()

    # Verify webhook signature
    _verify_webhook_signature(body, x_webhook_signature)

    try:
        import json
        payload = json.loads(body) if body else {}
        req = svc.ingest_jira_payload(project_id=project_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return req.to_dict()


@router.post("/confluence/webhook", status_code=status.HTTP_201_CREATED)
async def confluence_webhook(
    request: Request,
    project_id: str,
    x_webhook_signature: Optional[str] = Header(None, alias="x-webhook-signature"),
) -> dict:
    """Confluence webhook — Auth: HMAC-SHA256 signature verification via X-Webhook-Signature header."""
    body = await request.body()

    # Verify webhook signature
    _verify_webhook_signature(body, x_webhook_signature)

    try:
        import json
        payload = json.loads(body) if body else {}
        req = svc.ingest_confluence_payload(project_id=project_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return req.to_dict()


def _require_project_access(project_id: str, db: Session, user: User) -> None:
    from app.domains.tspm.models import TspmProject, TspmProjectMember
    if db.get(TspmProject, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proje bulunamadı")
    for role in (user.roles or []):
        for rp in (role.permissions or []):
            if getattr(rp, "permission", "") == "admin.*":
                return
    is_member = db.scalar(
        select(func.count()).where(
            TspmProjectMember.project_id == project_id,
            TspmProjectMember.user_id == user.id,
        )
    )
    if not is_member:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu projeye erişim yetkiniz yok")


@router.get("/projects/{project_id}")
def list_for_project(
    project_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[dict]:
    _require_project_access(project_id, db, user)
    return [r.to_dict() for r in svc.list_ingested(project_id=project_id)]


@router.get("/{req_id}")
def get_ingested(
    req_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    req = svc.get_ingested(req_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement bulunamadı")
    if req.project_id:
        _require_project_access(req.project_id, db, user)
    return req.to_dict()
