"""JWT ve parola yardimcilari — token olusturma, dogrulama, sifre hashleme."""

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional

import bcrypt
import jwt

from app.config import settings

_ACCESS_REVOKE_PREFIX = "bgts:auth:revoked-access:"
_PASSWORD_RESET_PREFIX = "bgts:auth:password-reset:"

# Redis yoksa gelistirme/test icin process-local fallback.
_revoked_tokens: dict[str, int] = {}
_password_reset_tokens: dict[str, tuple[str, int]] = {}


@lru_cache(maxsize=1)
def _get_redis_client():
    required = settings.is_production_like or os.getenv(
        "AUTH_STATE_REDIS_REQUIRED",
        "",
    ).lower() in {"1", "true", "yes"}
    try:
        import redis
    except ImportError as exc:
        if required:
            raise RuntimeError(
                "Auth state icin redis bagimliligi zorunlu (AUTH_STATE_REDIS_REQUIRED/production)."
            ) from exc
        return None

    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        if required:
            client.ping()
        return client
    except Exception as exc:
        if required:
            raise RuntimeError(
                "Auth state icin redis baglantisi zorunlu fakat ulasilamiyor."
            ) from exc
        return None


def _utc_ts() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _prune_expired() -> None:
    now = _utc_ts()
    expired_revoked = [jti for jti, exp in _revoked_tokens.items() if exp <= now]
    for jti in expired_revoked:
        _revoked_tokens.pop(jti, None)

    expired_reset = [jti for jti, (_, exp) in _password_reset_tokens.items() if exp <= now]
    for jti in expired_reset:
        _password_reset_tokens.pop(jti, None)


def _store_access_revocation(jti: str, exp_ts: int) -> None:
    ttl_seconds = max(exp_ts - _utc_ts(), 1)
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(f"{_ACCESS_REVOKE_PREFIX}{jti}", ttl_seconds, "1")
            return
        except Exception:
            pass

    _prune_expired()
    _revoked_tokens[jti] = _utc_ts() + ttl_seconds


def _is_access_revoked(jti: str) -> bool:
    if not jti:
        return False

    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            return bool(redis_client.exists(f"{_ACCESS_REVOKE_PREFIX}{jti}"))
        except Exception:
            pass

    _prune_expired()
    exp_ts = _revoked_tokens.get(jti)
    return bool(exp_ts and exp_ts > _utc_ts())


def _store_password_reset(jti: str, user_id: str, exp_ts: int) -> None:
    ttl_seconds = max(exp_ts - _utc_ts(), 1)
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(f"{_PASSWORD_RESET_PREFIX}{jti}", ttl_seconds, user_id)
            return
        except Exception:
            pass

    _prune_expired()
    _password_reset_tokens[jti] = (user_id, _utc_ts() + ttl_seconds)


def _consume_password_reset(jti: str) -> Optional[str]:
    if not jti:
        return None

    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            key = f"{_PASSWORD_RESET_PREFIX}{jti}"
            pipeline = redis_client.pipeline()
            pipeline.get(key)
            pipeline.delete(key)
            value, _ = pipeline.execute()
            return value
        except Exception:
            pass

    _prune_expired()
    payload = _password_reset_tokens.pop(jti, None)
    if payload is None:
        return None
    user_id, exp_ts = payload
    if exp_ts <= _utc_ts():
        return None
    return user_id


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def create_access_token(subject_user_id: str, extra_claims: Optional[dict] = None) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject_user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "jti": secrets.token_hex(8),  # Token ID — revocation icin
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )


def decode_token(token: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    jti = payload.get("jti", "")
    if _is_access_revoked(jti):
        raise jwt.InvalidTokenError("Token iptal edilmis")
    return payload


def revoke_token(token: str) -> None:
    """Token'i iptal et (blacklist'e ekle)."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        jti = payload.get("jti", "")
        if jti:
            exp_ts = int(payload.get("exp", _utc_ts()))
            _store_access_revocation(jti, exp_ts)
    except jwt.PyJWTError:
        pass


def create_password_reset_token(user_id: str) -> str:
    """Sifre sifirlama token'i olustur (15 dakika gecerli)."""
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.password_reset_token_expire_minutes)
    jti = secrets.token_hex(16)
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "purpose": "password_reset",
        "jti": jti,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    _store_password_reset(jti, user_id, int(exp.timestamp()))
    return token


def verify_password_reset_token(token: str) -> Optional[str]:
    """Sifre sifirlama token'ini dogrula. Gecerli ise user_id dondur."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        if payload.get("purpose") != "password_reset":
            return None
        jti = payload.get("jti", "")
        stored_user_id = _consume_password_reset(jti)
        if stored_user_id is None:
            return None
        token_user_id = payload.get("sub")
        if token_user_id != stored_user_id:
            return None
        return token_user_id
    except jwt.PyJWTError:
        return None


# ── Refresh Token ────────────────────────────────────────────────────────────

def _sha256_token(token: str) -> str:
    """Token'i SHA-256 ile hashle (DB depolama icin)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_refresh_token(user_id: str, db, user_agent: str = "") -> str:
    """Refresh token olustur, hash'ini DB'ye kaydet. Ham token'i dondur."""
    from app.infra.models import RefreshToken

    jti = secrets.token_hex(16)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(days=settings.refresh_token_expire_days)

    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": "refresh",
        "jti": jti,
    }
    raw_token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    # Hash'i DB'ye kaydet
    db_record = RefreshToken(
        id=jti,
        user_id=user_id,
        token_hash=_sha256_token(raw_token),
        expires_at=exp,
        user_agent=user_agent[:500] if user_agent else "",
    )
    db.add(db_record)
    db.flush()
    return raw_token


def verify_refresh_token(token: str, db) -> str:
    """Refresh token'i dogrula. Gecerli ise user_id dondur, degilse ValueError."""
    from app.infra.models import RefreshToken

    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except jwt.PyJWTError as e:
        raise ValueError(f"Gecersiz refresh token: {e}") from e

    if payload.get("type") != "refresh":
        raise ValueError("Bu bir refresh token degil")

    jti = payload.get("jti", "")
    if not jti:
        raise ValueError("Token JTI eksik")

    record = db.get(RefreshToken, jti)
    if record is None:
        raise ValueError("Refresh token bulunamadi")
    if record.revoked:
        raise ValueError("Refresh token iptal edilmis")
    if record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise ValueError("Refresh token suresi dolmus")

    # Hash dogrulama
    if record.token_hash != _sha256_token(token):
        raise ValueError("Token hash eslesmedi")

    return payload["sub"]


def revoke_refresh_token(token: str, db) -> None:
    """Tek bir refresh token'i iptal et."""
    from app.infra.models import RefreshToken

    try:
        payload = jwt.decode(
            token, settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},
        )
        jti = payload.get("jti", "")
        if jti:
            record = db.get(RefreshToken, jti)
            if record:
                record.revoked = True
    except jwt.PyJWTError:
        pass


def revoke_all_user_tokens(user_id: str, db) -> int:
    """Kullanicinin tum refresh token'larini iptal et. Iptal edilen sayiyi dondur."""
    from sqlalchemy import update
    from app.infra.models import RefreshToken

    result = db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
        .values(revoked=True)
    )
    return result.rowcount
