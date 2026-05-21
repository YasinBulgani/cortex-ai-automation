"""Ingestion router — /api/v1/ingestion.

POST /ingestion/text                         — raw metin
POST /ingestion/jira/webhook                 — Jira webhook
POST /ingestion/confluence/webhook           — Confluence webhook
GET  /ingestion/projects/{project_id}        — proje requirements listesi
GET  /ingestion/{req_id}                     — detay
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.domains.ingestion import service as svc

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class TextIngestIn(BaseModel):
    project_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1)
    source: str = "text"
    source_ref: Optional[str] = None


@router.post("/text", status_code=status.HTTP_201_CREATED)
def ingest_text_endpoint(body: TextIngestIn) -> dict:
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
def jira_webhook(payload: Dict[str, Any], project_id: str) -> dict:
    """Jira webhook — `?project_id=` query param ile hedef proje belirlenir.

    Production'da auth + signature verification eklenmeli.
    """
    try:
        req = svc.ingest_jira_payload(project_id=project_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return req.to_dict()


@router.post("/confluence/webhook", status_code=status.HTTP_201_CREATED)
def confluence_webhook(payload: Dict[str, Any], project_id: str) -> dict:
    try:
        req = svc.ingest_confluence_payload(project_id=project_id, payload=payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return req.to_dict()


@router.get("/projects/{project_id}")
def list_for_project(project_id: str) -> list[dict]:
    return [r.to_dict() for r in svc.list_ingested(project_id=project_id)]


@router.get("/{req_id}")
def get_ingested(req_id: str) -> dict:
    req = svc.get_ingested(req_id)
    if req is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement bulunamadı")
    return req.to_dict()
