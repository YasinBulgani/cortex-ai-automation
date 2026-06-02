"""Symmetric encryption for secrets at-rest (Fernet, multi-key rotation).

Usage:
    from app.infra.crypto import encrypt_secret, decrypt_secret

    ct = encrypt_secret("my-api-key")
    pt = decrypt_secret(ct)

Or as a SQLAlchemy column type:
    from app.infra.crypto import EncryptedString
    api_key: Mapped[str] = mapped_column(EncryptedString(512))

Key management:
- SECRETS_ENCRYPTION_KEYS env var = comma-separated Fernet keys
- First key = current (used for encryption)
- All keys tried in order for decryption (enables rotation)
- Missing keys -> falls back to insecure dev key with WARNING

To rotate:
    1. Generate new key, prepend to SECRETS_ENCRYPTION_KEYS
    2. Restart workers
    3. Re-encrypt rows (run rotation script) -> old key can be dropped
"""

from __future__ import annotations

import base64
import hashlib
import logging
from functools import lru_cache
from typing import Optional

from sqlalchemy import String, TypeDecorator

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _multi_fernet():
    try:
        from cryptography.fernet import Fernet, MultiFernet  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "cryptography paketi yok — `pip install cryptography`"
        ) from e

    raw = (settings.secrets_encryption_keys or "").strip()
    if not raw:
        # DEV fallback — derive deterministic key from jwt_secret. NOT for prod.
        logger.warning(
            "SECRETS_ENCRYPTION_KEYS bos — jwt_secret'ten dev-fallback uretiliyor. "
            "Production icin gercek Fernet key uretip ayarlayin."
        )
        digest = hashlib.sha256(settings.jwt_secret.encode()).digest()
        dev_key = base64.urlsafe_b64encode(digest)
        return MultiFernet([Fernet(dev_key)])

    keys = [k.strip() for k in raw.split(",") if k.strip()]
    fernets = []
    for k in keys:
        try:
            fernets.append(Fernet(k.encode() if not k.endswith("=") else k.encode()))
        except Exception as e:
            logger.error("Invalid Fernet key skipped: %s", e)
    if not fernets:
        raise RuntimeError("SECRETS_ENCRYPTION_KEYS hicbir gecerli Fernet anahtari icermiyor")
    return MultiFernet(fernets)


def encrypt_secret(plaintext: str) -> str:
    """Returns urlsafe-base64 ciphertext (str)."""
    if plaintext is None:
        return plaintext  # type: ignore[return-value]
    return _multi_fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt_secret(ciphertext: str) -> str:
    if ciphertext is None:
        return ciphertext  # type: ignore[return-value]
    return _multi_fernet().decrypt(ciphertext.encode("ascii")).decode("utf-8")


def reset_crypto_cache() -> None:
    _multi_fernet.cache_clear()


class EncryptedString(TypeDecorator):
    """SQLAlchemy column type: transparently encrypts/decrypts string values.

    Storage column type is VARCHAR (length = max plaintext + overhead).
    Fernet output is ~ ceil(plaintext/16)*4*4/3 + 73 chars (approx).
    """

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Optional[str], dialect):
        if value is None:
            return None
        return encrypt_secret(value)

    def process_result_value(self, value: Optional[str], dialect):
        if value is None:
            return None
        try:
            return decrypt_secret(value)
        except Exception:
            logger.exception("Failed to decrypt secret column; returning None")
            return None
