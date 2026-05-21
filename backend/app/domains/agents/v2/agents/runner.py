"""Runner Agent — Sandbox'ta testleri koştur."""
from __future__ import annotations

import logging

from ..schemas.run import RunResult, TestStatus
from ..state import AgentState
from ..tools.test_runner import run_playwright_tests
from .base import BaseAgent

logger = logging.getLogger(__name__)


class RunnerAgent(BaseAgent):
    name = "runner"
    description = "Playwright testlerini koştur"

    async def execute(self, state: AgentState) -> AgentState:
        code = state.get("generated_code")
        if not code:
            state["run_result"] = RunResult(
                run_id=state.get("run_id", ""), status=TestStatus.SKIPPED,
            ).to_state_dict()
            return state

        spec_files = code.get("spec_files", []) if isinstance(code, dict) else []
        if not spec_files:
            state["run_result"] = RunResult(
                run_id=state.get("run_id", ""), status=TestStatus.SKIPPED,
            ).to_state_dict()
            return state

        base_url = state.get("input_payload", {}).get("url")
        iteration = state.get("healing_iteration", 0)
        logger.info("Runner: %d spec, iter=%d", len(spec_files), iteration)

        try:
            result = await run_playwright_tests(
                test_files=spec_files,
                run_id=state.get("run_id"),
                base_url=base_url,
                environment="sandbox",
                browser="chromium",
                timeout_seconds=600,
                use_docker=self.config.sandbox_mode in {"auto", "required"},
                sandbox_required=self.config.sandbox_mode == "required",
                docker_image=self.config.sandbox_image,
                docker_cpu_limit=self.config.sandbox_cpu_limit,
                docker_memory_limit=self.config.sandbox_memory_limit,
                network_allowlist=self.config.sandbox_network_allowlist,
            )
        except Exception as exc:
            logger.exception("Runner çöktü: %s", exc)
            state.setdefault("errors", []).append({
                "agent": self.name, "error": str(exc),
                "error_type": type(exc).__name__,
            })
            state["run_result"] = RunResult(
                run_id=state.get("run_id", ""), status=TestStatus.ERROR,
            ).to_state_dict()
            return state

        state["run_result"] = result.to_state_dict()
        logger.info(
            "Runner tamam — status=%s passed=%d failed=%d",
            result.status.value, result.passed_count, result.failed_count,
        )
        return state


_agent = RunnerAgent()


async def runner_node(state: AgentState) -> AgentState:
    return await _agent(state)
