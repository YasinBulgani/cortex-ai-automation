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

from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user, resolve_project_permissions
from app.infra.database import get_db
from app.infra.models import User
from app.domains.pilot import service as svc

router = APIRouter(prefix="/pilot", tags=["pilot"])

AuthUser = Annotated[User, Depends(get_current_user)]


class CreateSessionIn(BaseModel):
    project_id: str = Field(min_length=1, max_length=100)


class ConverseIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)


class ClarifyIn(BaseModel):
    answer: Any


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
def create_session_endpoint(
    body: CreateSessionIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict:
    # Proje üyeliği doğrula — başka tenant/proje'ye session bağlamayı engelle.
    perms = resolve_project_permissions(db, user, body.project_id)
    if "admin.*" not in perms and "project.read" not in perms:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu proje icin yetkiniz yok")
    s = svc.create_session(project_id=body.project_id, user_id=user.id)
    return s.to_dict()


@router.get("/sessions/{session_id}")
def get_session_endpoint(session_id: str, user: Annotated[User, Depends(get_current_user)]) -> dict:
    s = svc.get_session(session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot session bulunamadı")
    if s.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu session'a erişim yetkiniz yok")
    return s.to_dict()


@router.get("/sessions")
def list_sessions_endpoint(
    user: Annotated[User, Depends(get_current_user)],
    project_id: Optional[str] = Query(None),
) -> list[dict]:
    return [s.to_dict() for s in svc.list_sessions(project_id=project_id, user_id=user.id)]


@router.post("/sessions/{session_id}/converse")
def converse_endpoint(session_id: str, body: ConverseIn, user: Annotated[User, Depends(get_current_user)]) -> dict:
    s = svc.get_session(session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot session bulunamadı")
    if s.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu session'a erişim yetkiniz yok")
    try:
        s = svc.converse(session_id, body.text)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return s.to_dict()


@router.post("/sessions/{session_id}/clarify")
def clarify_endpoint(session_id: str, body: ClarifyIn, user: Annotated[User, Depends(get_current_user)]) -> dict:
    s = svc.get_session(session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot session bulunamadı")
    if s.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu session'a erişim yetkiniz yok")
    try:
        s = svc.answer_clarification(session_id, body.answer)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return s.to_dict()


@router.post("/sessions/{session_id}/execute-stage")
def execute_stage_endpoint(session_id: str, user: Annotated[User, Depends(get_current_user)]) -> dict:
    s = svc.get_session(session_id)
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot session bulunamadı")
    if s.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Bu session'a erişim yetkiniz yok")
    try:
        s = svc.execute_next_stage(session_id)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return s.to_dict()
