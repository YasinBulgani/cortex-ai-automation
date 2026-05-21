"""Service layer for Jenkins outbound connections.

Owns:
  - Fernet-encrypted persistence of API tokens
  - CRUD on cicd_jenkins_connections
  - Build a JenkinsClient instance from a stored connection

The Fernet key is derived from `settings.jwt_secret` so no extra env var
is required for development. For production, set JENKINS_ENCRYPTION_KEY
to a 32-byte url-safe base64 key (e.g. `Fernet.generate_key()`).
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.domains.cicd.jenkins_client import JenkinsClient, JenkinsClientError

logger = logging.getLogger(__name__)


def _derive_key() -> bytes:
    raw = os.environ.get("JENKINS_ENCRYPTION_KEY", "").strip()
    if raw:
        try:
            Fernet(raw.encode())
            return raw.encode()
        except (ValueError, TypeError):
            logger.warning("JENKINS_ENCRYPTION_KEY geçersiz, JWT_SECRET'tan türetiliyor")
    digest = hashlib.sha256(settings.jwt_secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def _fernet() -> Fernet:
    return Fernet(_derive_key())


def encrypt_token(plain: str) -> str:
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_token(cipher: str) -> str:
    try:
        return _fernet().decrypt(cipher.encode("ascii")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Token şifresi çözülemedi (anahtar değişmiş olabilir)") from exc


_PUBLIC_COLS = (
    "id, name, base_url, username, tenant_id, owner_user_id, "
    "last_status, last_tested_at, last_error, created_at, updated_at"
)


def _row_to_dict(row: dict) -> dict[str, Any]:
    out = dict(row)
    for k in ("last_tested_at", "created_at", "updated_at"):
        v = out.get(k)
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
    return out


def list_connections(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            f"""
            SELECT {_PUBLIC_COLS}
            FROM cicd_jenkins_connections
            WHERE tenant_id = :tenant_id
            ORDER BY created_at DESC
            """
        ),
        {"tenant_id": tenant_id},
    ).mappings().all()
    return [_row_to_dict(r) for r in rows]


def get_connection(db: Session, conn_id: str, tenant_id: str) -> Optional[dict[str, Any]]:
    row = db.execute(
        text(
            f"""
            SELECT {_PUBLIC_COLS}, token_encrypted
            FROM cicd_jenkins_connections
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {"id": conn_id, "tenant_id": tenant_id},
    ).mappings().first()
    return dict(row) if row else None


def create_connection(
    db: Session,
    *,
    name: str,
    base_url: str,
    username: str,
    token: str,
    tenant_id: str,
    owner_user_id: Optional[str] = None,
) -> dict[str, Any]:
    encrypted = encrypt_token(token)
    row = db.execute(
        text(
            f"""
            INSERT INTO cicd_jenkins_connections
                (name, base_url, username, token_encrypted, tenant_id, owner_user_id)
            VALUES (:name, :base_url, :username, :token, :tenant_id, :owner)
            RETURNING {_PUBLIC_COLS}
            """
        ),
        {
            "name": name,
            "base_url": base_url.rstrip("/"),
            "username": username,
            "token": encrypted,
            "tenant_id": tenant_id,
            "owner": owner_user_id,
        },
    ).mappings().first()
    db.commit()
    return _row_to_dict(dict(row)) if row else {}


def delete_connection(db: Session, conn_id: str, tenant_id: str) -> bool:
    result = db.execute(
        text(
            """
            DELETE FROM cicd_jenkins_connections
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {"id": conn_id, "tenant_id": tenant_id},
    )
    db.commit()
    return result.rowcount > 0


def _update_status(
    db: Session,
    conn_id: str,
    status: str,
    error: str = "",
) -> None:
    db.execute(
        text(
            """
            UPDATE cicd_jenkins_connections
            SET last_status = :status,
                last_error = :error,
                last_tested_at = NOW(),
                updated_at = NOW()
            WHERE id = :id
            """
        ),
        {"id": conn_id, "status": status, "error": error[:1024]},
    )
    db.commit()


def client_from_row(row: dict[str, Any]) -> JenkinsClient:
    token = decrypt_token(row["token_encrypted"])
    return JenkinsClient(
        base_url=row["base_url"],
        username=row["username"],
        token=token,
    )


async def test_connection(db: Session, conn_id: str, tenant_id: str) -> dict[str, Any]:
    row = get_connection(db, conn_id, tenant_id)
    if not row:
        return {"ok": False, "error": "Bağlantı bulunamadı"}
    client = client_from_row(row)
    try:
        info = await client.ping()
        _update_status(db, conn_id, "ok", "")
        return {"ok": True, **info}
    except JenkinsClientError as exc:
        _update_status(db, conn_id, "error", str(exc))
        return {"ok": False, "error": str(exc)}


async def trigger_build(
    db: Session,
    conn_id: str,
    tenant_id: str,
    job_name: str,
    parameters: Optional[dict[str, str]] = None,
) -> dict[str, Any]:
    row = get_connection(db, conn_id, tenant_id)
    if not row:
        return {"ok": False, "error": "Bağlantı bulunamadı"}
    client = client_from_row(row)
    try:
        result = await client.trigger_build(job_name, parameters)
        return {"ok": True, **result}
    except JenkinsClientError as exc:
        return {"ok": False, "error": str(exc)}


async def last_build(
    db: Session, conn_id: str, tenant_id: str, job_name: str
) -> dict[str, Any]:
    row = get_connection(db, conn_id, tenant_id)
    if not row:
        return {"ok": False, "error": "Bağlantı bulunamadı"}
    client = client_from_row(row)
    try:
        result = await client.last_build(job_name)
        return {"ok": True, **result}
    except JenkinsClientError as exc:
        return {"ok": False, "error": str(exc)}
