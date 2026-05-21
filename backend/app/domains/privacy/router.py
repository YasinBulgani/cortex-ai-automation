"""Privacy and DSAR endpoints."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.deps import _user_permissions, get_current_user
from app.domains.audit.service import log_audit
from app.domains.privacy.schemas import DSARDeleteRequest, DSARDeleteResponse, DSARExportResponse
from app.domains.privacy.service import build_user_dsar_export, delete_user_ai_data
from app.infra.database import get_db
from app.infra.models import User

router = APIRouter(prefix="/privacy", tags=["privacy"])


@router.get("/dsar/users/{user_id}/export", response_model=DSARExportResponse)
def export_user_ai_data(
    user_id: str,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
) -> dict:
    _require_privacy_admin(actor)
    return build_user_dsar_export(db, user_id=user_id)


@router.post("/dsar/users/{user_id}/delete", response_model=DSARDeleteResponse)
def delete_user_ai_data_endpoint(
    user_id: str,
    body: DSARDeleteRequest,
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    actor: Annotated[User, Depends(get_current_user)],
) -> dict:
    _require_privacy_admin(actor)
    result = delete_user_ai_data(
        db,
        user_id=user_id,
        dry_run=body.dry_run,
        purge_artifact_files=body.purge_artifact_files,
    )
    log_audit(
        db,
        actor_user_id=actor.id,
        action="privacy.dsar.delete",
        resource_type="user_ai_data",
        resource_id=user_id,
        payload={
            "dry_run": body.dry_run,
            "purge_artifact_files": body.purge_artifact_files,
            "reason": body.reason,
            "deleted": result.get("deleted", {}),
        },
        ip=request.client.host if request.client else None,
    )
    db.commit()
    return result


def _require_privacy_admin(user: User) -> None:
    perms = _user_permissions(user)
    if "admin.*" in perms or "privacy.manage" in perms:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Privacy/DSAR işlemi için admin veya privacy.manage yetkisi gerekli",
    )
