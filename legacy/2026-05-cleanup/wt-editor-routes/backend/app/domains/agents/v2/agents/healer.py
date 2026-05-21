"""Healer Agent — Kırık testi onar, auto-PR."""
from __future__ import annotations

import json
import logging
from datetime import datetime

from ..prompts.healer import (
    HEALER_CLASSIFY_SYSTEM_PROMPT, HEALER_FIX_SYSTEM_PROMPT,
    build_healer_classify_user_prompt, build_healer_fix_user_prompt,
)
from ..schemas.heal import (
    FailureCategory, FixHypothesis, HealingAttempt, HealingResult,
)
from ..state import AgentState
from ..tools.ai_gateway import ai_complete, parse_json_safe
from .base import BaseAgent

logger = logging.getLogger(__name__)


class HealerAgent(BaseAgent):
    name = "healer"
    description = "Kırık locator → 3 fix hypothesis → en iyisini seç → auto-PR"

    async def execute(self, state: AgentState) -> AgentState:
        run_result = state.get("run_result")
        if not run_result or run_result.get("failed_count", 0) == 0:
            state["healing_result"] = HealingResult().to_state_dict()
            return state

        failure_contexts = run_result.get("failure_contexts", [])
        if not failure_contexts:
            state["healing_result"] = HealingResult().to_state_dict()
            return state

        logger.info("Healer: %d fail için çalışıyor", len(failure_contexts))
        result = HealingResult()

        for fc in failure_contexts:
            try:
                attempt = await self._heal_one(fc, state)
                result.attempts.append(attempt)
                if attempt.winner_index is not None:
                    result.successful_fixes += 1
                    if attempt.pr_url:
                        result.pr_urls.append(attempt.pr_url)
                if attempt.hitl_required and attempt.test_id:
                    result.hitl_queue.append(attempt.test_id)
            except Exception as exc:
                logger.exception("Healer — %s: %s", fc.get("test_id"), exc)

        state["healing_result"] = result.to_state_dict()
        logger.info(
            "Healer tamam — %d fix, %d HITL, %d PR",
            result.successful_fixes, len(result.hitl_queue), len(result.pr_urls),
        )
        return state

    async def _heal_one(self, fc: dict, state: AgentState) -> HealingAttempt:
        attempt = HealingAttempt(
            test_id=fc.get("test_id", "unknown"),
            broken_selector=(fc.get("locators_used") or [""])[0],
        )

        if self._requires_hitl(fc):
            attempt.hitl_required = True
            attempt.hitl_reason = "Kritik test — auto-fix disabled"
            attempt.completed_at = datetime.utcnow()
            return attempt

        category = await self._classify(fc, state)
        attempt.failure_category = category

        if category != FailureCategory.LOCATOR_CHANGED:
            attempt.hitl_required = True
            attempt.hitl_reason = f"Kategori: {category.value}"
            attempt.completed_at = datetime.utcnow()
            return attempt

        hypotheses = await self._generate_fixes(fc, state)
        attempt.hypotheses = hypotheses

        if not hypotheses:
            attempt.hitl_required = True
            attempt.hitl_reason = "Fix hypothesis üretilemedi"
            attempt.completed_at = datetime.utcnow()
            return attempt

        ranked = sorted(enumerate(hypotheses), key=lambda x: -x[1].confidence)
        winner_idx, winner = ranked[0]

        if winner.confidence < self.config.healing_confidence_threshold:
            attempt.hitl_required = True
            attempt.hitl_reason = (
                f"Confidence {winner.confidence:.2f} < "
                f"eşik {self.config.healing_confidence_threshold}"
            )
            attempt.completed_at = datetime.utcnow()
            return attempt

        attempt.winner_index = winner_idx
        winner.verified = True
        winner.final_score = winner.confidence

        if self.config.auto_pr_enabled:
            attempt.pr_url = await self._create_pr_stub(fc, winner, state)
            attempt.branch = f"heal/{attempt.test_id.replace('::', '_')[:40]}"

        attempt.completed_at = datetime.utcnow()
        return attempt

    async def _classify(self, fc: dict, state: AgentState) -> FailureCategory:
        user_prompt = build_healer_classify_user_prompt(
            error_type=fc.get("error_type", ""),
            error_message=fc.get("error_message", ""),
            stack_trace=fc.get("stack_trace", ""),
            last_actions=fc.get("last_actions", []),
            console_errors=fc.get("console_errors", []),
            dom_changed=bool(fc.get("previous_dom_path")),
        )
        try:
            response = await ai_complete(
                user_message=user_prompt,
                system_message=HEALER_CLASSIFY_SYSTEM_PROMPT,
                task_type="debug_test",
                temperature=0.1,
                max_tokens=20,
                json_mode=False,
                model_override=self.config.reporter_model,
                correlation_id=state.get("run_id"),
            )
            self.track_cost(
                state,
                tokens_input=response.usage.input_tokens,
                tokens_output=response.usage.output_tokens,
                model=response.model_used,
            )
            raw = response.content.strip().lower().replace(" ", "_")
            try:
                return FailureCategory(raw)
            except ValueError:
                return FailureCategory.UNKNOWN
        except Exception as exc:
            logger.warning("Classify: %s", exc)
            return FailureCategory.UNKNOWN

    async def _generate_fixes(self, fc: dict, state: AgentState) -> list[FixHypothesis]:
        user_prompt = build_healer_fix_user_prompt(
            element_description=(fc.get("locators_used") or [""])[0],
            broken_selector=(fc.get("locators_used") or [""])[0],
            dom_snippet=fc.get("error_message", ""),
        )
        try:
            response = await ai_complete(
                user_message=user_prompt,
                system_message=HEALER_FIX_SYSTEM_PROMPT,
                task_type="debug_test",
                temperature=0.2,
                max_tokens=1500,
                json_mode=True,
                model_override=self.config.coder_model,
                correlation_id=state.get("run_id"),
            )
            self.track_cost(
                state,
                tokens_input=response.usage.input_tokens,
                tokens_output=response.usage.output_tokens,
                model=response.model_used,
            )
        except Exception as exc:
            logger.warning("Fix-gen: %s", exc)
            return []

        parsed = response.parsed_json() or parse_json_safe(response.content)
        if not isinstance(parsed, list):
            return []

        hypotheses: list[FixHypothesis] = []
        for h in parsed:
            if not isinstance(h, dict):
                continue
            try:
                hypotheses.append(FixHypothesis(
                    strategy=h.get("strategy", "unknown"),
                    new_selector=h.get("new_selector", ""),
                    reasoning=h.get("reasoning", ""),
                    confidence=float(h.get("confidence", 0.0)),
                ))
            except Exception:
                pass
        return hypotheses

    def _requires_hitl(self, fc: dict) -> bool:
        name = (fc.get("test_name", "") + " " + fc.get("test_id", "")).lower()
        for kw in self.config.hitl_critical_keywords:
            if kw.lower() in name:
                return True
        return False

    async def _create_pr_stub(
        self, fc: dict, winner: FixHypothesis, state: AgentState
    ) -> str:
        return (
            f"stub://healer-pr/{state.get('run_id', 'run')[:8]}"
            f"/{fc.get('test_id', 'unknown')[:20]}"
        )


_agent = HealerAgent()


async def healer_node(state: AgentState) -> AgentState:
    return await _agent(state)
