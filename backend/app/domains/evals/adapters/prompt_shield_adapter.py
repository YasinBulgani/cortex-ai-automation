"""Prompt Shield adapter — adversarial input detection evalı.

Mod seçimi:
    * ``inputs._fixture`` varsa → fixture'ı aynen döndür (deterministik/CI mode)
    * Yoksa → gerçek ``prompt_shield`` (input_scanner) çağrısı

Output schema:
    {
      "blocked": bool,
      "risk_score": float,
      "categories": [str, ...],
      "warnings": [str, ...],
      "masked": str,              # (PII redaktörden)
    }
"""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)


class PromptShieldAdapter:
    name = "prompt_shield"

    def available(self) -> bool:
        # prompt_shield backend'de mevcut — modül import edilebilir mi?
        try:
            from app.domains.ai import prompt_shield  # noqa: F401
            return True
        except ImportError:
            return False

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        # Fixture mode — inputs._fixture aynen döner (CI deterministik)
        fixture = inputs.get("_fixture")
        if isinstance(fixture, dict):
            return dict(fixture)

        attack_text = inputs.get("text") or inputs.get("prompt") or ""
        if not attack_text:
            return {
                "blocked": False,
                "risk_score": 0.0,
                "categories": [],
                "warnings": ["empty_input"],
                "masked": "",
            }

        # Gerçek shield — input scanner'ı çağır
        try:
            from app.domains.ai.prompt_shield import scan_input  # type: ignore
            scan = scan_input(attack_text)
        except Exception as exc:
            logger.warning("prompt_shield scan_input hata: %s", exc)
            scan = None

        if scan is None:
            return {
                "blocked": False,
                "risk_score": 0.0,
                "categories": [],
                "warnings": ["shield_unavailable"],
                "masked": attack_text,
            }

        # PII redactor çağır
        masked = attack_text
        try:
            from app.domains.ai.pii_redactor import redact
            masked = redact(attack_text)
        except Exception:
            import logging as _logging
            _logging.getLogger(__name__).warning(
                "PII redactor başarısız oldu — ham metin kullanılıyor", exc_info=True
            )

        # scan objesi dict veya nesne olabilir; esnek ol
        def _get(obj, key, default=None):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        return {
            "blocked": bool(_get(scan, "blocked", False)),
            "risk_score": float(_get(scan, "risk_score", 0.0) or 0.0),
            "categories": list(_get(scan, "categories", []) or []),
            "warnings": list(_get(scan, "warnings", []) or []),
            "masked": masked,
        }
