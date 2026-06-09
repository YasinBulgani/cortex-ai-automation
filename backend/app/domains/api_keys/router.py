"""API key management endpoints.

POST /api/v1/api-keys — Create new key
GET /api/v1/api-keys — List user's keys
POST /api/v1/api-keys/{key_id}/rotate — Rotate key
DELETE /api/v1/api-keys/{key_id} — Revoke key
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_current_user
from app.infra.database import get_db
from app.infra.models import User
from app.domains.api_keys import service as svc


router = APIRouter(prefix="/api-keys", tags=["api_keys"])


class ApiKeyCreateIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    expires_in_days: int = Field(default=90, ge=1, le=365)


class ApiKeyOut(BaseModel):
    id: str
    name: str
    is_active: bool
    created_at: str
    expires_at: Optional[str] = None
    last_used_at: Optional[str] = None

    class Config:
        from_attributes = True


class ApiKeyCreateOut(ApiKeyOut):
    """Key creation response includes plaintext (shown only once)."""
    plaintext_key: str


class ApiKeyRotateIn(BaseModel):
    new_name: Optional[str] = Field(default=None, max_length=200)


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreateOut)
def create_api_key(
    body: ApiKeyCreateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """Create new API key for current user.

    **Important:** Plaintext key is only shown once. Store it securely.
    """
    from datetime import timedelta

    try:
        api_key, plaintext = svc.create_api_key(
            db,
            user_id=str(user.id),
            name=body.name,
            expires_in=timedelta(days=body.expires_in_days),
            created_by=str(user.id),
        )
        db.commit()
        db.refresh(api_key)

        return {
            "id": api_key.id,
            "name": api_key.name,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "last_used_at": None,
            "plaintext_key": plaintext,
        }
    except Exception as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.get("", response_model=list[ApiKeyOut])
def list_api_keys(
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all API keys (active & revoked) for current user."""
    keys = svc.list_user_keys(db, user_id=str(user.id))
    return [
        {
            "id": k.id,
            "name": k.name,
            "is_active": k.is_active,
            "created_at": k.created_at.isoformat(),
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
        }
        for k in keys
    ]


@router.post("/{key_id}/rotate", status_code=status.HTTP_201_CREATED, response_model=ApiKeyCreateOut)
def rotate_api_key(
    key_id: str,
    body: ApiKeyRotateIn,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> dict:
    """Rotate an API key.

    Creates new key with 24h overlap window for graceful migration.
    Old key remains valid for 24h before expiring.
    """
    try:
        old_key = db.get(svc.ApiKey, key_id)
        if old_key is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Key not found")

        if old_key.user_id != str(user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot rotate key of another user")

        api_key, plaintext = svc.rotate_api_key(
            db,
            old_key_id=key_id,
            user_id=str(user.id),
            new_name=body.new_name,
            created_by=str(user.id),
        )
        db.commit()
        db.refresh(api_key)

        return {
            "id": api_key.id,
            "name": api_key.name,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at.isoformat(),
            "expires_at": api_key.expires_at.isoformat() if api_key.expires_at else None,
            "last_used_at": None,
            "plaintext_key": plaintext,
        }
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_api_key(
    key_id: str,
    user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
) -> None:
    """Revoke an API key immediately."""
    try:
        old_key = db.get(svc.ApiKey, key_id)
        if old_key is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Key not found")

        if old_key.user_id != str(user.id):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot revoke key of another user")

        svc.revoke_api_key(db, key_id=key_id, user_id=str(user.id), reason="manual_revocation")
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
