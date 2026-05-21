"""Structured error types for the banking agent system.

Provides a hierarchy of agent-specific exceptions with metadata
(agent name, recoverability, original cause) so callers can make
informed decisions instead of catching bare ``Exception``.
"""

from __future__ import annotations


class AgentError(Exception):
    """Base exception for all agent errors."""

    def __init__(self, agent_name: str, message: str, recoverable: bool = False):
        self.agent_name = agent_name
        self.recoverable = recoverable
        super().__init__(f"[{agent_name}] {message}")


class LLMConnectionError(AgentError):
    """Ollama/OpenAI unreachable — network or timeout error."""

    def __init__(self, agent_name: str, model: str, original: Exception):
        self.model = model
        self.original = original
        super().__init__(
            agent_name,
            f"LLM bağlantı hatası ({model}): {original}",
            recoverable=True,
        )


class LLMResponseError(AgentError):
    """LLM returned an invalid or empty response."""

    def __init__(self, agent_name: str, model: str, raw_response: str = ""):
        self.model = model
        self.raw_response = raw_response[:500]
        super().__init__(
            agent_name,
            f"Geçersiz LLM yanıtı ({model})",
            recoverable=True,
        )


class JSONParseError(AgentError):
    """LLM response could not be parsed as JSON."""

    def __init__(self, agent_name: str, raw: str):
        self.raw = raw[:500]
        super().__init__(agent_name, "JSON parse hatası", recoverable=True)


class ContextBuildError(AgentError):
    """Project context could not be built from a given source."""

    def __init__(self, agent_name: str, source: str, original: Exception):
        self.source = source
        self.original = original
        super().__init__(
            agent_name,
            f"Bağlam oluşturma hatası ({source}): {original}",
            recoverable=True,
        )


class PipelinePhaseError(AgentError):
    """A pipeline phase failed — wraps the original cause and any partial data."""

    def __init__(
        self,
        phase: str,
        agent_name: str,
        original: Exception,
        partial_data: dict | None = None,
    ):
        self.phase = phase
        self.original = original
        self.partial_data = partial_data or {}
        super().__init__(
            agent_name,
            f"Pipeline faz hatası ({phase}): {original}",
            recoverable=True,
        )
