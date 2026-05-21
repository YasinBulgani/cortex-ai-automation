"""BaseAgent — tüm ajanların ortak iskeleti."""
from __future__ import annotations

import abc
import logging
from datetime import datetime

from ..state import AgentState
from ..config import AgentV2Config, get_config

logger = logging.getLogger(__name__)


class BaseAgent(abc.ABC):
    name: str = "base"
    description: str = ""

    def __init__(self, config: AgentV2Config | None = None):
        self.config = config or get_config()

    @abc.abstractmethod
    async def execute(self, state: AgentState) -> AgentState:
        ...

    async def __call__(self, state: AgentState) -> AgentState:
        start = datetime.utcnow()
        trace_id = self._start_trace(state)

        try:
            logger.info("Agent %s başlıyor (run_id=%s)", self.name, state.get("run_id"))
            new_state = await self.execute(state)
            new_state.setdefault("agent_traces", []).append({
                "agent": self.name,
                "trace_id": trace_id,
                "start": start.isoformat(),
                "end": datetime.utcnow().isoformat(),
                "status": "ok",
            })
            return new_state
        except Exception as e:
            logger.exception("Agent %s hata: %s", self.name, e)
            state.setdefault("errors", []).append({
                "agent": self.name,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.utcnow().isoformat(),
                "trace_id": trace_id,
            })
            return state
        finally:
            self._end_trace(trace_id, start)

    def _start_trace(self, state: AgentState) -> str:
        if not self.config.langfuse_enabled:
            return ""
        try:
            return f"trace-{self.name}-{state.get('run_id', 'unknown')[:8]}"
        except Exception:
            return ""

    def _end_trace(self, trace_id: str, start: datetime) -> None:
        if not trace_id:
            return
        duration_ms = (datetime.utcnow() - start).total_seconds() * 1000
        logger.debug("Trace %s bitti (%dms)", trace_id, duration_ms)

    def track_cost(
        self, state: AgentState, tokens_input: int, tokens_output: int, model: str
    ) -> None:
        state["tokens_used"] = state.get("tokens_used", 0) + tokens_input + tokens_output
        state["llm_calls_count"] = state.get("llm_calls_count", 0) + 1
        cost = self._calculate_cost(tokens_input, tokens_output, model)
        state["cost_usd"] = state.get("cost_usd", 0.0) + cost

    def _calculate_cost(self, input_t: int, output_t: int, model: str) -> float:
        if model.startswith(("qwen", "llama", "bge")):
            return 0.0
        CLOUD_PRICING = {
            "gemini-1.5-flash": (0.075, 0.30),
            "gemini-1.5-pro": (1.25, 5.00),
            "claude-3.5-sonnet": (3.00, 15.00),
            "gpt-4o-mini": (0.15, 0.60),
            "groq:llama3-70b-8192": (0.59, 0.79),
        }
        in_price, out_price = CLOUD_PRICING.get(model, (1.0, 1.0))
        return (input_t * in_price + output_t * out_price) / 1_000_000
