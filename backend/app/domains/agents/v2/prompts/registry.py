"""Prompt registry bridge for agents/v2.

agents/v2 has strict agent-local output contracts. The bridge keeps those
contracts, while prepending the centrally governed prompt policy when the DB
registry or prompt_center manifest is available.
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


def resolve_agent_system_prompt(
    prompt_id: str,
    fallback_contract: str,
    *,
    tenant_id: str | None = None,
    env: str | None = None,
) -> str:
    """Resolve a governed prompt and append the agent-specific contract.

    The DB prompt registry wins when reachable. File-backed prompt_center is the
    deterministic fallback for local/dev/test environments. If neither source is
    available, the existing agent contract remains the only prompt body.
    """
    governed = _resolve_db_prompt(prompt_id, tenant_id=tenant_id, env=env)
    if not governed:
        governed = _resolve_file_prompt(prompt_id)
    if not governed:
        return fallback_contract
    if fallback_contract.strip() in governed:
        return governed
    return f"{governed.strip()}\n\nAGENT CONTRACT:\n{fallback_contract.strip()}\n"


def _resolve_db_prompt(
    prompt_id: str,
    *,
    tenant_id: str | None,
    env: str | None,
) -> str | None:
    try:
        from app.domains.prompts.service import resolve

        resolved = resolve(
            prompt_id,
            tenant_id=tenant_id,
            env=(env or os.getenv("PROMPT_REGISTRY_ENV") or "prod"),  # type: ignore[arg-type]
        )
    except Exception as exc:
        logger.debug("agents/v2 prompt registry DB fallback for %s: %s", prompt_id, exc)
        return None
    if resolved and resolved.system_prompt.strip():
        return resolved.system_prompt
    return None


def _resolve_file_prompt(prompt_id: str) -> str | None:
    try:
        from prompt_center.registry import registry, PromptNotFoundError, PromptDriftError
        return registry.build(prompt_id)
    except PromptNotFoundError:
        return None
    except PromptDriftError as exc:
        logger.warning("agents/v2 prompt_center drift for %s: %s", prompt_id, exc)
        return None
    except Exception as exc:
        logger.debug("agents/v2 prompt_center fallback unavailable for %s: %s", prompt_id, exc)
        return None
