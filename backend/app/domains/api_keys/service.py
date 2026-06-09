"""Service layer for API key management."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone as _tz
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.domains.api_keys.models import ApiKey
from app.infra.crypto import hash_secret


ROTATION_OVERLAP_WINDOW = timedelta(hours=24)  # New key active before old expires
KEY_EXPIRY_DEFAULT = timedelta(days=90)


def generate_api_key() -> str:
    """Generate a cryptographically secure random API key."""
    return f"sk_{secrets.token_urlsafe(32)}"


def create_api_key(
    db: Session,
    user_id: str,
    name: str,
    expires_in: timedelta = KEY_EXPIRY_DEFAULT,
    created_by: Optional[str] = None,
) -> tuple[ApiKey, str]:
    """Create new API key.

    Returns:
        (ApiKey model, plaintext_key) - plaintext is only available once
    """
    plaintext_key = generate_api_key()
    key_hash = hash_secret(plaintext_key)

    expires_at = datetime.now(_tz.utc) + expires_in

    api_key = ApiKey(
        user_id=user_id,
        name=name,
        key_hash=key_hash,
        is_active=True,
        expires_at=expires_at,
        created_by=created_by or user_id,
    )
    db.add(api_key)
    db.flush()

    return api_key, plaintext_key


def rotate_api_key(
    db: Session,
    old_key_id: str,
    user_id: str,
    new_name: Optional[str] = None,
    created_by: Optional[str] = None,
) -> tuple[ApiKey, str]:
    """Rotate API key: deactivate old, create new.

    Supports overlap window (24h) for graceful migration.
    """
    old_key = db.get(ApiKey, old_key_id)
    if old_key is None:
        raise KeyError("API key not found")

    if old_key.user_id != user_id:
        raise PermissionError("Cannot rotate key belonging to another user")

    # Mark old key as rotated (keep active for overlap window)
    old_key.rotation_reason = "rotated"
    new_expires = datetime.now(_tz.utc) + ROTATION_OVERLAP_WINDOW
    if old_key.expires_at is None or new_expires > old_key.expires_at:
        old_key.expires_at = new_expires

    # Create new key
    plaintext_key = generate_api_key()
    key_hash = hash_secret(plaintext_key)
    expires_at = datetime.now(_tz.utc) + KEY_EXPIRY_DEFAULT

    new_key = ApiKey(
        user_id=user_id,
        name=new_name or f"{old_key.name} (rotated)",
        key_hash=key_hash,
        is_active=True,
        expires_at=expires_at,
        rotated_from_id=old_key_id,
        rotation_reason="automatic_rotation",
        created_by=created_by or user_id,
    )
    db.add(new_key)
    db.flush()

    return new_key, plaintext_key


def revoke_api_key(
    db: Session,
    key_id: str,
    user_id: str,
    reason: Optional[str] = None,
) -> ApiKey:
    """Immediately revoke an API key."""
    api_key = db.get(ApiKey, key_id)
    if api_key is None:
        raise KeyError("API key not found")

    if api_key.user_id != user_id:
        raise PermissionError("Cannot revoke key belonging to another user")

    api_key.is_active = False
    api_key.revoked_at = datetime.now(_tz.utc)
    api_key.revoked_reason = reason
    db.flush()

    return api_key


def get_active_keys(db: Session, user_id: str) -> list[ApiKey]:
    """Get all active keys for user."""
    now = datetime.now(_tz.utc)
    return db.scalars(
        select(ApiKey).where(
            ApiKey.user_id == user_id,
            ApiKey.is_active == True,  # noqa: E712
            or_(
                ApiKey.expires_at.is_(None),
                ApiKey.expires_at > now,
            ),
        )
    ).all()


def verify_api_key(db: Session, plaintext_key: str, user_id: str) -> Optional[ApiKey]:
    """Verify API key belongs to user and is active."""
    key_hash = hash_secret(plaintext_key)
    now = datetime.now(_tz.utc)

    api_key = db.scalar(
        select(ApiKey).where(
            ApiKey.key_hash == key_hash,
            ApiKey.user_id == user_id,
            ApiKey.is_active == True,  # noqa: E712
            or_(
                ApiKey.expires_at.is_(None),
                ApiKey.expires_at > now,
            ),
        )
    )

    if api_key is not None:
        # Update last_used_at
        api_key.last_used_at = now
        db.flush()

    return api_key


def list_user_keys(db: Session, user_id: str) -> list[ApiKey]:
    """List all (active & revoked) keys for user."""
    return db.scalars(
        select(ApiKey).where(ApiKey.user_id == user_id).order_by(ApiKey.created_at.desc())
    ).all()


def cleanup_expired_keys(db: Session, older_than_days: int = 30) -> int:
    """Delete keys expired more than N days ago."""
    cutoff = datetime.now(_tz.utc) - timedelta(days=older_than_days)
    expired = db.query(ApiKey).filter(
        ApiKey.expires_at < cutoff,
        ApiKey.revoked_at.isnot(None),
    ).delete()
    db.flush()
    return expired
