"""agents/v2 prompt registry bridge tests."""

from __future__ import annotations

from app.domains.agents.v2.prompts.analyst import ANALYST_SYSTEM_PROMPT
from app.domains.agents.v2.prompts.registry import resolve_agent_system_prompt


def test_prompt_registry_bridge_prepends_prompt_center_policy():
    prompt = resolve_agent_system_prompt("analyze_document", ANALYST_SYSTEM_PROMPT)

    assert "Nexus QA / BGTS" in prompt
    assert "AGENT CONTRACT:" in prompt
    assert ANALYST_SYSTEM_PROMPT.strip() in prompt


def test_prompt_registry_bridge_falls_back_to_agent_contract_for_unknown_prompt():
    fallback = "Strict local contract"

    prompt = resolve_agent_system_prompt("missing-prompt-id", fallback)

    assert prompt == fallback
