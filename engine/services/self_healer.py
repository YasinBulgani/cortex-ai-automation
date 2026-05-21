"""
Backend self-healing servisi — feedback loop ile (Dalga 2).

Başarısız test locator'larını accessibility tree üzerinden analiz ederek yeni
locator önerisi üretir. E2E utils/self-healer.ts tarafından çağrılır.

Dalga 2 iyileştirmeleri:
    * **Feedback** — ``report_outcome(old, new, success)`` → cache entry'nin
      success rate + confidence alanları güncellenir.
    * **Confidence decay** — her başarısız koşumda confidence 0.1 düşer;
      0.3'ün altına inerse cache'ten silinir (stale guard).
    * **Schema versioning** — fingerprints v2 formatı: per-entry
      ``{new_locator, success_count, failure_count, confidence, updated_at}``.
      v1 (eski düz dict) otomatik migrate edilir.
    * **Observability** — heal success rate / cache staleness metrikleri.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .llm_gateway import LLMGateway
from .prompt_loader import get_engine_prompt

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HEALING_LOG = _REPO_ROOT / "reports" / "healing-log.json"
_LOCATOR_FINGERPRINTS = _REPO_ROOT / "engine" / "locators" / "ai_healing" / "locator_fingerprints.json"
HEALER_SYSTEM_PROMPT = get_engine_prompt("self_healer")


@dataclass
class HealingResult:
    healed: bool
    old_locator: str
    new_locator: str
    strategy: str
    confidence: float
    summary: str

    def to_dict(self) -> dict:
        return {
            "healed": self.healed,
            "old_locator": self.old_locator,
            "new_locator": self.new_locator,
            "strategy": self.strategy,
            "confidence": self.confidence,
            "summary": self.summary,
        }


class SelfHealer:
    """Kırık locator'ları AI ile onaran servis."""

    def __init__(self, gateway: LLMGateway, model: str | None = None):
        self.gateway = gateway
        self.model = model or "claude-3-5-sonnet-latest"
        self._fingerprints = self._load_fingerprints()

    # ── Cache & confidence ayarları ──────────────────────────────────
    # Cache'e ilk eklenen LLM-assisted heal bu skorla başlar.
    INITIAL_CONFIDENCE = 0.7
    # Başarılı rerun → +0.05 (cap 0.95). Başarısız → −0.10. 0.3 altı silinir.
    CONF_ON_SUCCESS = 0.05
    CONF_ON_FAILURE = 0.10
    CONF_MAX = 0.95
    CONF_EVICT = 0.3

    def heal(
        self,
        failed_locator: str,
        accessibility_tree: str,
        error_message: str = "",
        page_url: str = "",
    ) -> HealingResult:
        # 1) Fingerprint cache — confidence decay'den sağ kalan entry var mı?
        cached = self._fingerprints.get(failed_locator)
        if cached and isinstance(cached, dict):
            confidence = float(cached.get("confidence", self.INITIAL_CONFIDENCE))
            new_loc = cached.get("new_locator", "")
            if new_loc and confidence >= self.CONF_EVICT:
                return HealingResult(
                    healed=True,
                    old_locator=failed_locator,
                    new_locator=new_loc,
                    strategy="fingerprint_cache",
                    confidence=confidence,
                    summary=f"Cache'den heal: {failed_locator} → {new_loc} "
                            f"(conf={confidence:.2f})",
                )
            # Düşük confidence → cache'i atla, LLM'e git

        # 2) LLM ile heal dene
        messages = [
            {"role": "system", "content": HEALER_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Bulunamayan locator: {failed_locator}\n"
                    f"Hata: {error_message[:300]}\n"
                    f"Sayfa: {page_url}\n\n"
                    f"Accessibility Tree:\n{accessibility_tree[:6000]}"
                ),
            },
        ]

        try:
            resp = self.gateway.complete(messages, model=self.model, temperature=0.1, max_tokens=200)
            new_locator = resp.content.strip().strip("`").strip('"').strip("'")

            if new_locator and new_locator != failed_locator:
                self._save_fingerprint(
                    failed_locator, new_locator, confidence=self.INITIAL_CONFIDENCE,
                )
                self._log_healing(failed_locator, new_locator, "llm_assisted", page_url)

                return HealingResult(
                    healed=True,
                    old_locator=failed_locator,
                    new_locator=new_locator,
                    strategy="llm_assisted",
                    confidence=self.INITIAL_CONFIDENCE,
                    summary=f"LLM heal: {failed_locator} → {new_locator}",
                )
        except Exception as exc:
            logger.warning("LLM-assisted heal failed for locator %s: %s", failed_locator, exc)

        return HealingResult(
            healed=False,
            old_locator=failed_locator,
            new_locator="",
            strategy="failed",
            confidence=0.0,
            summary=f"Heal başarısız: {failed_locator}",
        )

    # ─────────────────────────────────────────────────────────────────────
    # Feedback loop — heal sonrasında test koşumundan gelen sinyal
    # ─────────────────────────────────────────────────────────────────────
    def report_outcome(
        self,
        *,
        old_locator: str,
        new_locator: str,
        success: bool,
    ) -> dict[str, Any]:
        """Heal edilmiş locator'ın sonraki koşumda başarılı olup olmadığını kaydet.

        Confidence recalibration:
            success → +``CONF_ON_SUCCESS`` (cap ``CONF_MAX``)
            failure → −``CONF_ON_FAILURE``; eşiğin altına düşerse entry silinir.

        Return: güncellenmiş durumun özeti (test + dashboard için).
        """
        entry = self._fingerprints.get(old_locator)
        if not isinstance(entry, dict) or entry.get("new_locator") != new_locator:
            logger.debug(
                "report_outcome: cache entry yok veya new_locator uyuşmuyor "
                "(old=%s new=%s)", old_locator, new_locator,
            )
            return {"status": "no_entry"}

        success_count = int(entry.get("success_count", 0))
        failure_count = int(entry.get("failure_count", 0))
        confidence = float(entry.get("confidence", self.INITIAL_CONFIDENCE))

        if success:
            success_count += 1
            confidence = min(self.CONF_MAX, confidence + self.CONF_ON_SUCCESS)
        else:
            failure_count += 1
            confidence = max(0.0, confidence - self.CONF_ON_FAILURE)

        entry.update({
            "new_locator": new_locator,
            "success_count": success_count,
            "failure_count": failure_count,
            "confidence": round(confidence, 3),
            "updated_at": datetime.now().isoformat(),
        })
        # eviction check
        if confidence < self.CONF_EVICT:
            logger.info(
                "Cache entry evicted (confidence=%.2f < %.2f): %s",
                confidence, self.CONF_EVICT, old_locator,
            )
            self._fingerprints.pop(old_locator, None)
            self._persist_fingerprints()
            return {
                "status": "evicted",
                "old_locator": old_locator,
                "final_confidence": round(confidence, 3),
                "reason": "confidence_below_threshold",
            }

        self._fingerprints[old_locator] = entry
        self._persist_fingerprints()

        return {
            "status": "updated",
            "old_locator": old_locator,
            "new_locator": new_locator,
            "success_count": success_count,
            "failure_count": failure_count,
            "confidence": round(confidence, 3),
        }

    # ── persistence (v2 schema) ──────────────────────────────────────────

    def _load_fingerprints(self) -> dict:
        if not _LOCATOR_FINGERPRINTS.exists():
            return {}
        try:
            raw = json.loads(_LOCATOR_FINGERPRINTS.read_text())
        except (json.JSONDecodeError, OSError) as exc:
            logger.debug("Could not load locator fingerprints: %s", exc)
            return {}

        # v1 → v2 migrate: eski entry'ler success/failure sayaçları olmadan
        # sadece {new_locator, timestamp} içeriyordu.
        migrated: dict[str, Any] = {}
        now_iso = datetime.now().isoformat()
        for key, val in raw.items():
            if not isinstance(val, dict):
                continue
            migrated[key] = {
                "new_locator": val.get("new_locator", ""),
                "success_count": int(val.get("success_count", 0)),
                "failure_count": int(val.get("failure_count", 0)),
                "confidence": float(
                    val.get("confidence", self.INITIAL_CONFIDENCE)
                ),
                "updated_at": val.get("updated_at") or val.get("timestamp") or now_iso,
            }
        return migrated

    def _save_fingerprint(
        self, old: str, new: str, *, confidence: float | None = None
    ) -> None:
        existing = self._fingerprints.get(old) if isinstance(
            self._fingerprints.get(old), dict
        ) else None
        entry = {
            "new_locator": new,
            "success_count": int((existing or {}).get("success_count", 0)),
            "failure_count": int((existing or {}).get("failure_count", 0)),
            "confidence": float(
                confidence
                if confidence is not None
                else (existing or {}).get("confidence", self.INITIAL_CONFIDENCE)
            ),
            "updated_at": datetime.now().isoformat(),
        }
        self._fingerprints[old] = entry
        self._persist_fingerprints()

    def _persist_fingerprints(self) -> None:
        try:
            _LOCATOR_FINGERPRINTS.parent.mkdir(parents=True, exist_ok=True)
            _LOCATOR_FINGERPRINTS.write_text(
                json.dumps(self._fingerprints, indent=2, ensure_ascii=False)
            )
        except OSError as exc:
            logger.warning("Locator fingerprint yazılamadı: %s", exc)

    @staticmethod
    def _log_healing(old: str, new: str, strategy: str, page_url: str):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "old_locator": old,
            "new_locator": new,
            "strategy": strategy,
            "page_url": page_url,
        }
        try:
            logs: list[dict] = []
            if _HEALING_LOG.exists():
                try:
                    raw = json.loads(_HEALING_LOG.read_text(errors="replace"))
                    logs = raw if isinstance(raw, list) else []
                except (json.JSONDecodeError, OSError, ValueError) as exc:
                    logger.debug("Healing log okunamadı, yeni liste: %s", exc)
            logs.append(log_entry)
            _HEALING_LOG.parent.mkdir(parents=True, exist_ok=True)
            _HEALING_LOG.write_text(json.dumps(logs[-500:], indent=2, ensure_ascii=False))
        except OSError as exc:
            logger.warning("Healing log yazılamadı: %s", exc)
