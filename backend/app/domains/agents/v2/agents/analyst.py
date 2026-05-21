"""Analyst Agent — Ham girdi → IntentGraph."""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from ..prompts.analyst import ANALYST_SYSTEM_PROMPT, build_analyst_user_prompt
from ..prompts.registry import resolve_agent_system_prompt
from ..schemas.intent import IntentGraph
from ..state import AgentState
from ..tools.ai_gateway import ai_complete, parse_json_safe
from ..tools.intake import intake_to_text, IntakeError
from .base import BaseAgent

logger = logging.getLogger(__name__)


class AnalystAgent(BaseAgent):
    name = "analyst"
    description = "Gereksinim dokümanı → Intent Graph"

    async def execute(self, state: AgentState) -> AgentState:
        source_type = state.get("input_source", "text")
        payload = state.get("input_payload", {})

        source_ref = (
            payload.get("text") or payload.get("url") or payload.get("path")
            or payload.get("content") or ""
        )
        if not source_ref:
            state["intent_graph"] = self._stub_intent_graph().to_state_dict()
            return state

        try:
            text, detected_type = await intake_to_text(
                source_ref,
                source_type=source_type,
                extra_context=payload.get("extra_context"),
            )
            logger.info("Analyst: kaynak (type=%s, %d kar)", detected_type, len(text))
        except IntakeError as exc:
            state.setdefault("errors", []).append({
                "agent": self.name,
                "error": f"Intake failed: {exc}",
                "error_type": "IntakeError",
            })
            state["intent_graph"] = self._stub_intent_graph().to_state_dict()
            return state

        user_prompt = build_analyst_user_prompt(
            source_text=text,
            source_type=detected_type,
            extra_context=payload.get("extra_context"),
        )

        try:
            system_prompt = resolve_agent_system_prompt(
                "analyze_document",
                ANALYST_SYSTEM_PROMPT,
                tenant_id=state.get("tenant_id"),
            )
            response = await ai_complete(
                user_message=user_prompt,
                system_message=system_prompt,
                task_type="analyze_document",
                temperature=0.2,
                max_tokens=4000,
                json_mode=True,
                project_id=state.get("project_id"),
                correlation_id=state.get("run_id"),
            )
        except Exception as exc:
            logger.exception("Analyst LLM: %s", exc)
            state.setdefault("errors", []).append({
                "agent": self.name,
                "error": str(exc),
                "error_type": type(exc).__name__,
            })
            state["intent_graph"] = self._stub_intent_graph().to_state_dict()
            return state

        self.track_cost(
            state,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model_used,
        )

        parsed = response.parsed_json() or parse_json_safe(response.content)
        if not isinstance(parsed, dict):
            state.setdefault("errors", []).append({
                "agent": self.name,
                "error": "LLM JSON parse edilemedi",
                "raw_snippet": response.content[:500],
            })
            state["intent_graph"] = self._stub_intent_graph().to_state_dict()
            return state

        try:
            intent = IntentGraph.model_validate(parsed)
        except ValidationError as exc:
            intent = await self._repair(parsed, exc, response.content, state)

        if intent is None:
            state["intent_graph"] = self._stub_intent_graph().to_state_dict()
            return state

        state["intent_graph"] = intent.to_state_dict()
        logger.info(
            "Analyst tamam — domain=%s area=%s risk=%s ac=%d",
            intent.domain, intent.feature_area,
            intent.risk_level.value, len(intent.acceptance_criteria),
        )
        return state

    async def _repair(
        self, bad_json: dict, err: ValidationError, raw_response: str, state: AgentState,
    ) -> IntentGraph | None:
        repair_prompt = (
            "Aşağıdaki JSON çıktın şemaya uymadı. DOĞRU JSON döndür.\n\n"
            f"HATALAR:\n{err}\n\n"
            f"HATALI JSON:\n{json.dumps(bad_json, ensure_ascii=False, indent=2)[:3000]}\n\n"
            "Sadece düzeltilmiş JSON döndür."
        )
        try:
            system_prompt = resolve_agent_system_prompt(
                "analyze_document",
                ANALYST_SYSTEM_PROMPT,
                tenant_id=state.get("tenant_id"),
            )
            resp = await ai_complete(
                user_message=repair_prompt,
                system_message=system_prompt,
                task_type="analyze_document",
                temperature=0.1,
                max_tokens=4000,
                json_mode=True,
                correlation_id=state.get("run_id"),
            )
            self.track_cost(
                state,
                tokens_input=resp.usage.input_tokens,
                tokens_output=resp.usage.output_tokens,
                model=resp.model_used,
            )
            fixed = resp.parsed_json()
            if isinstance(fixed, dict):
                return IntentGraph.model_validate(fixed)
        except Exception as exc:
            logger.error("Analyst repair: %s", exc)
        return None

    def _stub_intent_graph(self) -> IntentGraph:
        return IntentGraph(
            domain="banking",
            feature_area="unknown",
            title="Analiz yapılamadı",
            summary="Analyst ajanı bu kaynaktan Intent Graph üretemedi.",
        )


_agent = AnalystAgent()


async def analyst_node(state: AgentState) -> AgentState:
    return await _agent(state)
