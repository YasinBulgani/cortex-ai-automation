"""
Backend self-healing servisi.

Başarısız test locator'larını accessibility tree üzerinden analiz ederek
yeni locator önerisi üretir. E2E utils/self-healer.ts tarafından çağrılır.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HEALING_LOG = _REPO_ROOT / "reports" / "healing-log.json"
_LOCATOR_FINGERPRINTS = _REPO_ROOT / "engine" / "locators" / "ai_healing" / "locator_fingerprints.json"


HEALER_SYSTEM_PROMPT = """\
Sen web UI elementleri için locator uzmanısın.

Sana bir accessibility tree (JSON) ve bulunamayan bir locator verilecek.
Görevin: hedef elemente en uygun yeni locator'ı bulmak.

Kurallar:
1. Önce data-testid ara (en güvenilir)
2. Sonra ARIA role + name kombinasyonunu dene
3. Sonra label veya text ile eşleştir
4. CSS selector'ı son çare olarak kullan
5. Sadece TEK BİR locator döndür, açıklama ekleme
6. Locator formatı: Playwright locator string (ör. [data-testid="login-btn-submit"] veya role=button[name="Giriş"])
"""


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

    def heal(
        self,
        failed_locator: str,
        accessibility_tree: str,
        error_message: str = "",
        page_url: str = "",
    ) -> HealingResult:
        # 1) Fingerprint DB'den daha önce heal edilmiş mi bak
        cached = self._fingerprints.get(failed_locator)
        if cached:
            return HealingResult(
                healed=True,
                old_locator=failed_locator,
                new_locator=cached["new_locator"],
                strategy="fingerprint_cache",
                confidence=0.85,
                summary=f"Cache'den heal: {failed_locator} → {cached['new_locator']}",
            )

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
                self._save_fingerprint(failed_locator, new_locator)
                self._log_healing(failed_locator, new_locator, "llm_assisted", page_url)

                return HealingResult(
                    healed=True,
                    old_locator=failed_locator,
                    new_locator=new_locator,
                    strategy="llm_assisted",
                    confidence=0.7,
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

    # ── persistence ─────────────────────────────────────────────────────────

    def _load_fingerprints(self) -> dict:
        if _LOCATOR_FINGERPRINTS.exists():
            try:
                return json.loads(_LOCATOR_FINGERPRINTS.read_text())
            except (json.JSONDecodeError, OSError) as exc:
                logger.debug("Could not load locator fingerprints: %s", exc)
        return {}

    def _save_fingerprint(self, old: str, new: str):
        self._fingerprints[old] = {"new_locator": new, "timestamp": datetime.now().isoformat()}
        try:
            _LOCATOR_FINGERPRINTS.parent.mkdir(parents=True, exist_ok=True)
            _LOCATOR_FINGERPRINTS.write_text(json.dumps(self._fingerprints, indent=2, ensure_ascii=False))
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
