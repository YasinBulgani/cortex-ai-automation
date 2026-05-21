"""Feature flag service — Redis-backed + memory fallback.

Neden gerekli:
    Geliştirme planının 7.3 bölümü her yeni epic'in canary + kill-switch
    ile rollout edilmesini gerektiriyor. Bu modül tüm domainlerin
    (``evals``, ``coverup``, ``ai``, ``tspm`` vs.) tek bir noktadan
    beslendiği çekirdeği sunar.

Tasarım kararları:
    * **Redis-backed.** Flag durumu ``redis`` hash'inde (``ff:flags``)
      saklanır; çoklu pod restart'ına dayanıklı, canary yüzdesi tüm
      replikalarda aynı değeri görür.
    * **Memory fallback.** Redis ulaşılamıyorsa hiçbir şey patlamaz —
      in-process dict kullanılır, sadece loglarda uyarı düşer. Dev/CI
      ortamlarında Redis olmadan çalışır.
    * **Deterministik canary.** ``is_enabled(key, tenant_id)`` için
      ``sha1(tenant_id + key)`` alınır, ilk 8 hex → int % 100. Aynı
      tenant her zaman aynı karara düşer (UI flicker önlenir).
    * **Fail-closed default.** Bilinmeyen key → ``enabled=False``.
      Yeni feature bilinçli açılmadan canlı olmaz.
    * **Audit hook.** ``set_flag`` her çağrıda opsiyonel ``audit_sink``
      callback'ini çağırır — gerçek audit entegrasyonu E3.3'te
      tamamlanacak, burada callback noktası hazır.

Kullanım:
    from app.domains.feature_flags.service import feature_flags

    if feature_flags.is_enabled("evals.runner.v1", tenant_id=user.tenant_id):
        ...
"""
from __future__ import annotations

import hashlib
import json
import logging
import threading
import time
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from .schemas import FlagEvaluation, FlagOut, FlagUpdate, RolloutOut

logger = logging.getLogger(__name__)

_REDIS_HASH_KEY = "ff:flags"


def _hash_bucket(tenant_id: str, key: str) -> int:
    """Deterministik 0-99 bucket. Aynı (tenant, key) → aynı sonuç.

    SHA-1 non-cryptographic dağılım için yeterli; ilk 8 hex → 32 bit
    integer → mod 100.
    """
    raw = f"{tenant_id}|{key}".encode("utf-8")
    digest = hashlib.sha1(raw, usedforsecurity=False).hexdigest()
    return int(digest[:8], 16) % 100


class _FlagRecord:
    """İç temsil — Redis'ten okunan ham JSON objesi ile aynı şekle sahip."""

    __slots__ = (
        "key",
        "enabled",
        "description",
        "percent",
        "allow_tenants",
        "updated_at",
        "updated_by",
    )

    def __init__(
        self,
        key: str,
        enabled: bool = False,
        description: str = "",
        percent: int = 0,
        allow_tenants: Optional[List[str]] = None,
        updated_at: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> None:
        self.key = key
        self.enabled = enabled
        self.description = description
        self.percent = max(0, min(100, int(percent)))
        self.allow_tenants = list(allow_tenants or [])
        self.updated_at = updated_at
        self.updated_by = updated_by

    def to_json(self) -> str:
        return json.dumps(
            {
                "enabled": self.enabled,
                "description": self.description,
                "percent": self.percent,
                "allow_tenants": self.allow_tenants,
                "updated_at": self.updated_at,
                "updated_by": self.updated_by,
            },
            ensure_ascii=False,
        )

    @classmethod
    def from_json(cls, key: str, raw: str) -> "_FlagRecord":
        data = json.loads(raw)
        return cls(
            key=key,
            enabled=bool(data.get("enabled", False)),
            description=str(data.get("description", "")),
            percent=int(data.get("percent", 0) or 0),
            allow_tenants=list(data.get("allow_tenants") or []),
            updated_at=data.get("updated_at"),
            updated_by=data.get("updated_by"),
        )

    def to_out(self) -> FlagOut:
        updated_at_dt: Optional[datetime] = None
        if self.updated_at:
            try:
                updated_at_dt = datetime.fromisoformat(self.updated_at)
            except ValueError:
                updated_at_dt = None
        return FlagOut(
            key=self.key,
            enabled=self.enabled,
            description=self.description,
            rollout=RolloutOut(percent=self.percent, allow_tenants=list(self.allow_tenants)),
            updated_at=updated_at_dt,
            updated_by=self.updated_by,
        )


class FeatureFlagService:
    """Thread-safe feature flag store.

    İç state dışarı açılmaz — tüm erişim metotlar üzerinden. Testlerde
    ``clear()`` ile sıfırlanabilir.
    """

    def __init__(
        self,
        redis_client=None,  # type: ignore[no-untyped-def]
        *,
        audit_sink: Optional[Callable[[str, dict], None]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self._memory: Dict[str, _FlagRecord] = {}
        self._redis = redis_client
        self._redis_failed_at: Optional[float] = None
        self._audit_sink = audit_sink
        # Memory cache'in Redis ile hizalandığını işaretlemek için — ikinci
        # hydrate'i engeller. Cache invalidation: set_flag/delete/clear.
        self._hydrated = redis_client is None

    def bind_redis(self, redis_client) -> None:  # type: ignore[no-untyped-def]
        """Uygulama başlangıcında redis client enjekte edilir."""
        with self._lock:
            self._redis = redis_client
            self._redis_failed_at = None
            self._hydrated = False

    def _redis_available(self) -> bool:
        if self._redis is None:
            return False
        # Son 30 sn içinde hata aldıysak tekrar denemeyelim — log gürültüsü azaltır
        if self._redis_failed_at and (time.monotonic() - self._redis_failed_at) < 30:
            return False
        return True

    def _redis_fail(self, exc: Exception, op: str) -> None:
        self._redis_failed_at = time.monotonic()
        logger.warning(
            "FeatureFlags: Redis %s başarısız, memory fallback (%s)", op, exc
        )

    # ── Public API ────────────────────────────────────────────────────────

    def is_enabled(
        self,
        key: str,
        *,
        tenant_id: Optional[str] = None,
        default: bool = False,
    ) -> bool:
        """Kısa-yol: sadece bool. Detay için ``evaluate()``."""
        return self.evaluate(key, tenant_id=tenant_id, default=default).enabled

    def evaluate(
        self,
        key: str,
        *,
        tenant_id: Optional[str] = None,
        default: bool = False,
    ) -> FlagEvaluation:
        """Karar + gerekçe. Eval order:

        1. Flag yoksa → ``default`` (genelde False — fail-closed)
        2. ``enabled=False`` → False, reason=disabled
        3. ``tenant_id`` allow_tenants içindeyse → True, reason=tenant_allowlist
        4. ``percent=100`` → True, reason=rollout_percent
        5. ``tenant_id`` None + percent<100 → False (anonim canary'e alınmaz)
        6. ``hash_bucket(tenant_id, key) < percent`` → True, reason=rollout_percent
        7. Aksi → False, reason=rollout_percent
        """
        rec = self._get(key)
        if rec is None:
            return FlagEvaluation(key=key, enabled=default, reason="not_found")

        if not rec.enabled:
            return FlagEvaluation(
                key=key, enabled=False, reason="disabled", percent=rec.percent
            )

        if tenant_id and tenant_id in rec.allow_tenants:
            return FlagEvaluation(
                key=key, enabled=True, reason="tenant_allowlist", percent=rec.percent
            )

        if rec.percent >= 100:
            return FlagEvaluation(
                key=key, enabled=True, reason="rollout_percent", percent=rec.percent
            )

        if rec.percent <= 0 or not tenant_id:
            return FlagEvaluation(
                key=key, enabled=False, reason="rollout_percent", percent=rec.percent
            )

        bucket = _hash_bucket(tenant_id, key)
        return FlagEvaluation(
            key=key,
            enabled=bucket < rec.percent,
            reason="rollout_percent",
            percent=rec.percent,
        )

    def list_flags(self) -> List[FlagOut]:
        with self._lock:
            self._hydrate_from_redis()
            return [
                rec.to_out()
                for rec in sorted(self._memory.values(), key=lambda r: r.key)
            ]

    def get(self, key: str) -> Optional[FlagOut]:
        rec = self._get(key)
        return rec.to_out() if rec else None

    def set_flag(
        self,
        key: str,
        update: FlagUpdate,
        *,
        actor: Optional[str] = None,
    ) -> FlagOut:
        """Partial update. Olmayan flag ise oluşturulur (upsert)."""
        if not key or not key.strip():
            raise ValueError("Flag key boş olamaz")
        key = key.strip()

        with self._lock:
            self._hydrate_from_redis()
            # Yeni flag default'u: percent=100 ("enabled=True → herkese açık").
            # Canary isteyen operator kasten percent verir. Mevcut flag'lerin
            # percent değeri korunur — bu sadece ilk kayıt için geçerli.
            rec = self._memory.get(key) or _FlagRecord(key=key, percent=100)

            if update.enabled is not None:
                rec.enabled = bool(update.enabled)
            if update.description is not None:
                rec.description = update.description
            if update.percent is not None:
                rec.percent = max(0, min(100, int(update.percent)))
            if update.allow_tenants is not None:
                rec.allow_tenants = list(update.allow_tenants)

            rec.updated_at = datetime.now(timezone.utc).isoformat()
            rec.updated_by = actor

            self._memory[key] = rec
            self._persist(rec)

            if self._audit_sink:
                try:
                    self._audit_sink(
                        "feature_flag.updated",
                        {
                            "key": key,
                            "enabled": rec.enabled,
                            "percent": rec.percent,
                            "allow_tenants": list(rec.allow_tenants),
                            "actor": actor,
                        },
                    )
                except Exception as exc:  # pragma: no cover - audit best-effort
                    logger.warning("FeatureFlags: audit sink hata: %s", exc)

            return rec.to_out()

    def delete(self, key: str) -> bool:
        with self._lock:
            self._hydrate_from_redis()
            existed = key in self._memory
            self._memory.pop(key, None)
            if self._redis_available():
                try:
                    self._redis.hdel(_REDIS_HASH_KEY, key)  # type: ignore[union-attr]
                except Exception as exc:
                    self._redis_fail(exc, "hdel")
            return existed

    def clear(self) -> None:
        """Test-only — Redis ve memory state'i tamamen boşalt."""
        with self._lock:
            self._memory.clear()
            self._hydrated = self._redis is None
            if self._redis_available():
                try:
                    self._redis.delete(_REDIS_HASH_KEY)  # type: ignore[union-attr]
                except Exception as exc:
                    self._redis_fail(exc, "delete")

    # ── Internal ──────────────────────────────────────────────────────────

    def _get(self, key: str) -> Optional[_FlagRecord]:
        with self._lock:
            self._hydrate_from_redis()
            return self._memory.get(key)

    def _hydrate_from_redis(self) -> None:
        """Memory cache ilk çağrıda Redis'ten doldurulur. Best-effort.

        ``_hydrated`` flag'i sayesinde her çağrıda Redis'e gitmeyiz —
        ``set_flag/delete/clear`` üzerinden memory zaten güncel tutuluyor.
        """
        if self._hydrated:
            return
        if not self._redis_available():
            self._hydrated = True
            return
        try:
            raw_map = self._redis.hgetall(_REDIS_HASH_KEY)  # type: ignore[union-attr]
        except Exception as exc:
            self._redis_fail(exc, "hgetall")
            self._hydrated = True
            return
        for raw_key, raw_val in (raw_map or {}).items():
            k = raw_key.decode("utf-8") if isinstance(raw_key, (bytes, bytearray)) else str(raw_key)
            v = raw_val.decode("utf-8") if isinstance(raw_val, (bytes, bytearray)) else str(raw_val)
            try:
                self._memory[k] = _FlagRecord.from_json(k, v)
            except (json.JSONDecodeError, TypeError, ValueError) as exc:
                logger.warning("FeatureFlags: Redis'teki '%s' kaydı bozuk: %s", k, exc)
        self._hydrated = True

    def _persist(self, rec: _FlagRecord) -> None:
        if not self._redis_available():
            return
        try:
            self._redis.hset(_REDIS_HASH_KEY, rec.key, rec.to_json())  # type: ignore[union-attr]
        except Exception as exc:
            self._redis_fail(exc, "hset")


# Proses ömrü boyunca paylaşılan singleton — main.py startup'ta bind_redis çağırır
feature_flags = FeatureFlagService()
