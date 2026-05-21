"""Self-heal adapter — kırık locator + accessibility tree → yeni locator.

Mod seçimi:
    * ``inputs._fixture`` → fixture döner (CI)
    * Gerçek LLM: ENV ``EVAL_RUN_LLM=1`` + engine/self_healer

Output:
    { "new_locator": str, "strategy": str, "confidence": float }
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SelfHealAdapter:
    name = "self_heal"

    def available(self) -> bool:
        return True  # fixture modu her zaman

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        fixture = inputs.get("_fixture")
        if isinstance(fixture, dict):
            return dict(fixture)

        if os.environ.get("EVAL_RUN_LLM") != "1":
            return {
                "new_locator": "",
                "strategy": "skipped",
                "confidence": 0.0,
                "note": "EVAL_RUN_LLM=1 gerekli",
            }

        try:
            # engine/services/self_healer ayrı runtime; gateway üzerinden
            from app.domains.ai.gateway_client import gateway_complete
            failed = inputs.get("failed_locator") or ""
            tree = inputs.get("accessibility_tree") or ""
            if not failed or not tree:
                return {"new_locator": "", "error": "missing_inputs"}
            content = gateway_complete(
                task_type="chat",
                system_message="""Web UI locator uzmanı. Bulunamayan locator için
                    accessibility tree üzerinden yeni Playwright locator öner.""",
                user_message=(
                    f"Bulunamayan locator: {failed}\n"
                    f"Accessibility Tree:\n{tree[:5000]}"
                ),
            )
            new_loc = str(content or "").strip().strip("`").strip('"')
            return {
                "new_locator": new_loc,
                "strategy": "llm_assisted",
                "confidence": 0.7 if new_loc else 0.0,
            }
        except Exception as exc:
            logger.warning("self_heal adapter LLM hata: %s", exc)
            return {"new_locator": "", "error": str(exc)}
