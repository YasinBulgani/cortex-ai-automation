"""Test üretimi adapter — LLM ile test kodu üretir veya fixture döner.

Mod seçimi:
    * ``inputs._fixture`` varsa → fixture aynen döner (CI deterministik)
    * ``inputs.requirement`` + ENV ``EVAL_RUN_LLM=1`` varsa → gerçek LLM (maliyetli)
    * Aksi halde → not-available (suite skip)

Fixture format:
    {
      "code": "...",            # AST scorer bunu parse edecek
      "framework": "pytest" | "pytest-bdd" | "playwright-ts",
    }
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)


class TestGenAdapter:
    name = "test_gen"

    def available(self) -> bool:
        # Fixture modu her zaman mevcut; gerçek LLM opt-in.
        return True

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        fixture = inputs.get("_fixture")
        if isinstance(fixture, dict):
            return dict(fixture)

        if os.environ.get("EVAL_RUN_LLM") != "1":
            return {
                "code": "",
                "framework": inputs.get("framework", "pytest"),
                "note": "EVAL_RUN_LLM=1 gerekli — skip",
            }

        # Gerçek LLM çağrısı — nl_test_generator üzerinden
        try:
            from app.domains.ai.gateway_client import gateway_complete
            requirement = inputs.get("requirement") or ""
            framework = inputs.get("framework", "pytest")
            if not requirement:
                return {"code": "", "note": "empty_requirement"}
            content = gateway_complete(
                task_type="generate_test_cases",
                user_message=(
                    f"Framework: {framework}\nGereksinim: {requirement}\n"
                    "Sadece kod bloğu döndür."
                ),
            )
            return {"code": content, "framework": framework}
        except Exception as exc:
            logger.warning("test_gen adapter LLM hata: %s", exc)
            return {"code": "", "error": str(exc)}
