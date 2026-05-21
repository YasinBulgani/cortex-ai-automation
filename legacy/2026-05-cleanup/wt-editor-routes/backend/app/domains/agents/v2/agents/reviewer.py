"""Reviewer Agent."""
from __future__ import annotations

import logging

from ..prompts.reviewer import REVIEWER_SYSTEM_PROMPT, build_reviewer_user_prompt
from ..schemas.review import ReviewAction, ReviewFinding, ReviewResult
from ..state import AgentState
from ..tools.ai_gateway import ai_complete
from .base import BaseAgent

logger = logging.getLogger(__name__)


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    description = "Kod + run sonucu değerlendir"

    async def execute(self, state: AgentState) -> AgentState:
        intent = state.get("intent_graph", {})
        run_result = state.get("run_result", {})
        generated_code = state.get("generated_code", {})

        intent_summary = (
            f"Domain: {intent.get('domain', '?')}\n"
            f"Feature: {intent.get('feature_area', '?')}\n"
            f"Risk: {intent.get('risk_level', '?')}\n"
            f"Goals: {', '.join(intent.get('goals', [])[:5])}\n"
            f"AC: {len(intent.get('acceptance_criteria', []))}"
        )

        code_summary = (
            f"Generator: {generated_code.get('generator_type', '?')}\n"
            f"Spec: {len(generated_code.get('spec_files', []))}\n"
            f"PO: {len(generated_code.get('page_object_files', []))}\n"
            f"Steps: {len(generated_code.get('step_definition_files', []))}"
        )

        run_summary = (
            f"Status: {run_result.get('status', '?')}\n"
            f"Geçen: {run_result.get('passed_count', 0)}\n"
            f"Kalan: {run_result.get('failed_count', 0)}\n"
            f"Atlanan: {run_result.get('skipped_count', 0)}\n"
            f"Süre: {run_result.get('duration_seconds', 0)} sn"
        )

        user_prompt = build_reviewer_user_prompt(
            code_summary=code_summary,
            run_result_summary=run_summary,
            intent_graph_summary=intent_summary,
        )

        try:
            response = await ai_complete(
                user_message=user_prompt,
                system_message=REVIEWER_SYSTEM_PROMPT,
                task_type="debug_test",
                temperature=0.2,
                max_tokens=2000,
                json_mode=True,
                project_id=state.get("project_id"),
                correlation_id=state.get("run_id"),
            )
        except Exception as exc:
            logger.exception("Reviewer: %s", exc)
            state["review"] = self._fallback_review(state).to_state_dict()
            return state

        self.track_cost(
            state,
            tokens_input=response.usage.input_tokens,
            tokens_output=response.usage.output_tokens,
            model=response.model_used,
        )

        parsed = response.parsed_json()
        if not isinstance(parsed, dict):
            state["review"] = self._fallback_review(state).to_state_dict()
            return state

        try:
            security = [
                ReviewFinding(**f) if isinstance(f, dict)
                else ReviewFinding(severity="info", category="other", message=str(f))
                for f in parsed.get("security_flags", [])
            ]
            lint = [
                ReviewFinding(**f) if isinstance(f, dict)
                else ReviewFinding(severity="info", category="lint", message=str(f))
                for f in parsed.get("lint_errors", [])
            ]
            findings = [
                ReviewFinding(**f) if isinstance(f, dict)
                else ReviewFinding(severity="info", category="other", message=str(f))
                for f in parsed.get("findings", [])
            ]
            action_str = parsed.get("recommended_action", "approve_with_comments")
            try:
                action = ReviewAction(action_str)
            except ValueError:
                action = ReviewAction.APPROVE_WITH_COMMENTS

            review = ReviewResult(
                code_quality_score=float(parsed.get("code_quality_score", 0.5)),
                test_coverage_estimate=float(parsed.get("test_coverage_estimate", 0.5)),
                edge_cases_missed=parsed.get("edge_cases_missed", []),
                security_flags=security,
                lint_errors=lint,
                findings=findings,
                recommended_action=action,
                reviewer_notes=parsed.get("reviewer_notes", ""),
            )
        except Exception as exc:
            logger.warning("Reviewer Pydantic: %s", exc)
            review = self._fallback_review(state)

        state["review"] = review.to_state_dict()
        logger.info(
            "Reviewer tamam — quality=%.2f coverage=%.2f action=%s",
            review.code_quality_score, review.test_coverage_estimate,
            review.recommended_action.value,
        )
        return state

    def _fallback_review(self, state: AgentState) -> ReviewResult:
        run_result = state.get("run_result", {})
        total = run_result.get("passed_count", 0) + run_result.get("failed_count", 0)
        success_rate = (run_result.get("passed_count", 0) / total) if total else 0.0

        if success_rate >= 0.95:
            action = ReviewAction.AUTO_APPROVE
        elif success_rate >= 0.75:
            action = ReviewAction.APPROVE_WITH_COMMENTS
        elif success_rate >= 0.50:
            action = ReviewAction.REQUEST_CHANGES
        else:
            action = ReviewAction.REJECT

        return ReviewResult(
            code_quality_score=success_rate,
            test_coverage_estimate=success_rate * 0.8,
            recommended_action=action,
            reviewer_notes=f"Otomatik değerlendirme — başarı %{success_rate * 100:.0f}",
        )


_agent = ReviewerAgent()


async def reviewer_node(state: AgentState) -> AgentState:
    return await _agent(state)
