"""Locator Agent — DOM → LocatorSuggestion[]."""
from __future__ import annotations

import logging

from ..state import AgentState
from ..tools.locator import LocatorPipeline
from ..tools.locator.extraction import extract_from_html
from .base import BaseAgent

logger = logging.getLogger(__name__)


class LocatorAgent(BaseAgent):
    name = "locator"
    description = "Her interaktif element için 5 fallback locator"

    async def execute(self, state: AgentState) -> AgentState:
        app_map = state.get("app_map", {})
        if not app_map or not app_map.get("pages"):
            state["locators"] = []
            return state

        pages = app_map["pages"]
        logger.info("Locator %d sayfa için", len(pages))

        pipeline = LocatorPipeline(
            tenant_id=state.get("tenant_id", "default"),
            project_id=state.get("project_id", "default"),
            enable_ai_xpath=False,
        )

        all_suggestions: list[dict] = []
        for page in pages:
            if not isinstance(page, dict):
                continue
            url = page.get("url", "/")
            dom_hash = page.get("dom_hash", "")
            # Explorer screenshot_path varsa offline extraction yok
            # Playwright'a tekrar erişemediğimiz için stub olarak sayfa başına boş bırak
            # Faz 2 Sprint 5'te Explorer ↔ Locator entegrasyonu daha sıkı olacak
            continue

        state["locators"] = all_suggestions
        logger.info("Locator tamam — %d suggestion", len(all_suggestions))
        return state


_agent = LocatorAgent()


async def locator_node(state: AgentState) -> AgentState:
    return await _agent(state)
