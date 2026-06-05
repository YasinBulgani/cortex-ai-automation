"""
agents/v2 — LangGraph tabanlı 9 ajanlı QA otomasyon sistemi.

Plan: docs/plan/06_AGENT_ARCHITECTURE.md
"""

from .config import AgentV2Config, get_config
from .orchestrator import LANGGRAPH_AVAILABLE, build_graph, run_pipeline
from .state import AgentState, create_initial_state

__all__ = [
    "AgentState",
    "create_initial_state",
    "run_pipeline",
    "build_graph",
    "LANGGRAPH_AVAILABLE",
    "AgentV2Config",
    "get_config",
]

__version__ = "0.1.0-alpha"
