"""Artifact storage abstraction.

Local filesystem (dev) and S3 (production multi-instance) backends.

Usage:
    from app.infra.storage import get_storage
    storage = get_storage()
    storage.put_bytes("runs/abc/output.json", b"...")
    data = storage.get_bytes("runs/abc/output.json")
    url = storage.presigned_url("runs/abc/output.json", expires_in=3600)
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class Storage(ABC):
    @abstractmethod
    def put_bytes(self, key: str, data: bytes, *, content_type: Optional[str] = None) -> str:
        """Store bytes under key; return canonical URI/path."""

    @abstractmethod
    def get_bytes(self, key: str) -> bytes:
        """Fetch bytes for key."""

    @abstractmethod
    def exists(self, key: str) -> bool: ...

    @abstractmethod
    def delete(self, key: str) -> bool: ...

    @abstractmethod
    def presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        """Return a URL the client can fetch directly. For local backend,
        falls back to an /artifacts/{key} relative path the FE should resolve."""


# ── Local filesystem ──────────────────────────────────────────────
class LocalStorage(Storage):
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Defense against path traversal
        safe = key.lstrip("/").replace("..", "")
        p = (self.root / safe).resolve()
        if not str(p).startswith(str(self.root)):
            raise ValueError(f"Invalid key: {key}")
        return p

    def put_bytes(self, key: str, data: bytes, *, content_type: Optional[str] = None) -> str:
        p = self._path(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return f"file://{p}"

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()

    def delete(self, key: str) -> bool:
        p = self._path(key)
        if p.exists():
            p.unlink()
            return True
        return False

    def presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        # FE serves these via /artifacts route
        return f"/artifacts/{key.lstrip('/')}"


# ── S3 / S3-compatible (MinIO, etc.) ──────────────────────────────
class S3Storage(Storage):
    def __init__(
        self,
        bucket: str,
        region: str,
        endpoint_url: Optional[str],
        access_key: Optional[str],
        secret_key: Optional[str],
        prefix: str = "",
    ) -> None:
        try:
            import boto3  # type: ignore
        except ImportError as e:
            raise RuntimeError(
                "boto3 yuklu degil — `pip install boto3` ile yukleyin"
            ) from e
        self.bucket = bucket
        self.prefix = prefix
        client_kwargs: dict = {"region_name": region}
        if endpoint_url:
            client_kwargs["endpoint_url"] = endpoint_url
        if access_key and secret_key:
            client_kwargs["aws_access_key_id"] = access_key
            client_kwargs["aws_secret_access_key"] = secret_key
        self._client = boto3.client("s3", **client_kwargs)

    def _full_key(self, key: str) -> str:
        return f"{self.prefix}{key.lstrip('/')}"

    def put_bytes(self, key: str, data: bytes, *, content_type: Optional[str] = None) -> str:
        full = self._full_key(key)
        extra = {"ContentType": content_type} if content_type else {}
        self._client.put_object(Bucket=self.bucket, Key=full, Body=data, **extra)
        return f"s3://{self.bucket}/{full}"

    def get_bytes(self, key: str) -> bytes:
        full = self._full_key(key)
        obj = self._client.get_object(Bucket=self.bucket, Key=full)
        return obj["Body"].read()

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError  # type: ignore
        try:
            self._client.head_object(Bucket=self.bucket, Key=self._full_key(key))
            return True
        except ClientError:
            return False

    def delete(self, key: str) -> bool:
        self._client.delete_object(Bucket=self.bucket, Key=self._full_key(key))
        return True

    def presigned_url(self, key: str, *, expires_in: int = 3600) -> str:
        return self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": self._full_key(key)},
            ExpiresIn=expires_in,
        )


@lru_cache(maxsize=1)
def get_storage() -> Storage:
    backend = (settings.artifact_storage_backend or "local").lower()
    if backend == "s3":
        if not settings.s3_bucket:
            raise RuntimeError("S3 backend secildi ama S3_BUCKET tanimli degil")
        logger.info("Artifact storage: S3 bucket=%s", settings.s3_bucket)
        return S3Storage(
            bucket=settings.s3_bucket,
            region=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url or None,
            access_key=settings.s3_access_key_id or None,
            secret_key=settings.s3_secret_access_key or None,
            prefix=settings.s3_prefix,
        )
    logger.info("Artifact storage: local dir=%s", settings.artifacts_dir)
    return LocalStorage(settings.artifacts_dir)


def reset_storage_cache() -> None:
    """Test/runtime override icin — config degisirse cagrilir."""
    get_storage.cache_clear()
