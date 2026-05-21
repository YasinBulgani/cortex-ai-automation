"""Reporter Agent — TR yönetim özeti."""
from __future__ import annotations

import logging
from datetime import datetime

from ..prompts.reporter import REPORTER_SYSTEM_PROMPT, build_reporter_user_prompt
from ..schemas.report import ReportResult
from ..state import AgentState
from ..tools.ai_gateway import ai_complete
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ReporterAgent(BaseAgent):
    name = "reporter"
    description = "Yönetim raporu + Slack/e-posta"

    async def execute(self, state: AgentState) -> AgentState:
        intent = state.get("intent_graph", {})
        scenarios = state.get("scenarios", [])
        run_result = state.get("run_result", {})
        healing = state.get("healing_result", {})

        created = state.get("created_at")
        duration_minutes = 0.0
        if isinstance(created, datetime):
            duration_minutes = (datetime.utcnow() - created).total_seconds() / 60.0

        scenario_count = sum(
            s.get("scenario_count", 0) if isinstance(s, dict) else 0
            for s in scenarios
        )

        user_prompt = build_reporter_user_prompt(
            run_id=state.get("run_id", ""),
            intent_title=intent.get("feature_area", "?") + " / " + intent.get("domain", ""),
            scenario_count=scenario_count,
            passed=run_result.get("passed_count", 0),
            failed=run_result.get("failed_count", 0),
            flaky=run_result.get("flaky_count", 0),
            healing_fixes=healing.get("successful_fixes", 0) if isinstance(healing, dict) else 0,
            total_cost_usd=state.get("cost_usd", 0.0),
            total_tokens=state.get("tokens_used", 0),
            duration_minutes=duration_minutes,
        )

        try:
            response = await ai_complete(
                user_message=user_prompt,
                system_message=REPORTER_SYSTEM_PROMPT,
                task_type="chat",
                temperature=0.3,
                max_tokens=1000,
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
            summary_tr = response.content.strip()
        except Exception as exc:
            logger.warning("Reporter: %s — fallback", exc)
            summary_tr = self._fallback_summary(state)

        report = ReportResult(
            summary_tr=summary_tr,
            slack_channel=None,
            email_sent_to=[],
        )
        state["report"] = report.to_state_dict()
        state["status"] = "completed"
        state["completed_at"] = datetime.utcnow()
        logger.info("Reporter tamam — özet %d kar", len(summary_tr))
        return state

    def _fallback_summary(self, state: AgentState) -> str:
        intent = state.get("intent_graph", {})
        run = state.get("run_result", {})
        return (
            f"TestwrightAI koşusu tamamlandı.\n\n"
            f"- Konu: {intent.get('feature_area', '?')}\n"
            f"- Üretilen senaryo: "
            f"{sum(s.get('scenario_count', 0) for s in state.get('scenarios', []) if isinstance(s, dict))}\n"
            f"- Test sonucu: {run.get('passed_count', 0)} geçti / {run.get('failed_count', 0)} kaldı\n"
            f"- Maliyet: ${state.get('cost_usd', 0):.3f} ({state.get('tokens_used', 0)} token)\n"
            f"- Durum: {state.get('status', 'running')}"
        )


_agent = ReporterAgent()


async def reporter_node(state: AgentState) -> AgentState:
    return await _agent(state)
