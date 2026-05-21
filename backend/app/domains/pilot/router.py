"""Pilot router — /api/v1/pilot.

Endpoints:
  POST   /pilot/sessions           — yeni session başlat
  GET    /pilot/sessions/{id}      — session durumu
  GET    /pilot/sessions           — kullanıcı session listesi
  POST   /pilot/sessions/{id}/converse        — kullanıcı mesajı
  POST   /pilot/sessions/{id}/clarify         — pending soru cevabı
  POST   /pilot/sessions/{id}/execute-stage   — sıradaki stage'i koş
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.domains.pilot import service as svc

router = APIRouter(prefix="/pilot", tags=["pilot"])


class CreateSessionIn(BaseModel):
    project_id: str = Field(min_length=1)
    user_id: str = "anonymous"


class ConverseIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ClarifyIn(BaseModel):
    answer: Any


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session_endpoint(body: CreateSessionIn) -> dict:
    s = svc.create_session(project_id=body.project_id, user_id=body.user_id)
    return s.to_dict()


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str) -> dict:
    s = svc.get_session(session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot session bulunamadı")
    return s.to_dict()


@router.get("/sessions")
def list_sessions_endpoint(
    project_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
) -> list[dict]:
    return [s.to_dict() for s in svc.list_sessions(project_id=project_id, user_id=user_id)]


@router.post("/sessions/{session_id}/converse")
def converse_endpoint(session_id: str, body: ConverseIn) -> dict:
    try:
        s = svc.converse(session_id, body.text)
    except ValueError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return s.to_dict()


@router.post("/sessions/{session_id}/clarify")
def clarify_endpoint(session_id: str, body: ClarifyIn) -> dict:
    try:
        s = svc.answer_clarification(session_id, body.answer)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return s.to_dict()


@router.post("/sessions/{session_id}/execute-stage")
def execute_stage_endpoint(session_id: str) -> dict:
    try:
        s = svc.execute_next_stage(session_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return s.to_dict()
