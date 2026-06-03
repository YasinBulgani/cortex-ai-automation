"""Production startup invariants.

Called from main.py on app startup. Fails loudly in production when critical
multi-instance dependencies are missing.
"""

from __future__ import annotations

import logging
import os

from app.config import settings

logger = logging.getLogger(__name__)


_INSECURE_PLACEHOLDERS = {
    "change-me",
    "INSECURE",
    "dev-only-do-not-use",
}

_DANGEROUS_JWT_DEFAULTS = {"secret", "changeme", "password", "admin", "test", "neurex-dev"}


def _is_prod() -> bool:
    env = (os.environ.get("APP_ENV") or os.environ.get("ENVIRONMENT") or "").lower()
    return env in {"prod", "production"}


def _is_prod_or_staging() -> bool:
    return settings.is_production_like


def check_redis_available() -> bool:
    """Try to ping Redis. Returns True if reachable, False otherwise."""
    try:
        import redis  # type: ignore

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        return bool(client.ping())
    except Exception as e:
        logger.warning("Redis ping failed: %s", e)
        return False


def assert_production_invariants() -> None:
    """Raise RuntimeError on misconfiguration in production. No-op in dev."""
    if not _is_prod():
        return

    problems: list[str] = []

    # Redis required for multi-instance session/rate-limit/job state
    if settings.require_redis_in_production and not check_redis_available():
        problems.append(
            f"REDIS_URL ({settings.redis_url}) erisilebilir degil — "
            "production multi-instance icin Redis zorunlu."
        )

    # JWT secret zayif kontrolu
    if any(p.lower() in (settings.jwt_secret or "").lower() for p in _INSECURE_PLACEHOLDERS):
        problems.append("JWT_SECRET hala default/insecure deger — degistirin.")

    # JWT secret uzunluk kontrolu
    if len(settings.jwt_secret) < 64:
        problems.append(
            "JWT_SECRET en az 64 karakter olmali (openssl rand -base64 64)"
        )

    # CORS wildcard kontrolu
    if "*" in (settings.cors_origins or ""):
        problems.append("CORS_ORIGINS wildcard (*) production'da kullanilamaz")

    # Debug mode production/staging'de kapali olmali
    if settings.debug:
        problems.append("DEBUG=True production ortaminda kullanilamaz")

    # Tehlikeli default JWT_SECRET degerleri
    if any(d in (settings.jwt_secret or "").lower() for d in _DANGEROUS_JWT_DEFAULTS):
        problems.append("JWT_SECRET guvenli olmayan default deger iceriyor — degistirin.")

    # Encryption keys production/staging'de zorunlu
    if not settings.secrets_encryption_keys:
        problems.append("SECRETS_ENCRYPTION_KEYS production'da zorunludur")

    # Artifact storage uyarisi (local backend prod'da multi-instance kirar)
    if settings.artifact_storage_backend == "local":
        logger.warning(
            "Production'da artifact_storage_backend='local' kullaniyorsunuz; "
            "multi-instance deployment icin 's3' onerilir."
        )

    if problems:
        raise RuntimeError(
            "Production yapilandirma hatalari:\n  - " + "\n  - ".join(problems)
        )

    logger.info("Production invariants OK")
