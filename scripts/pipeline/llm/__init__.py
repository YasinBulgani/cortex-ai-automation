"""
Pipeline LLM infrastructure — multi-provider.

Provider seçimi: LLM_PROVIDER env
    ollama (DEFAULT — lokal, token gerekmez, hızlı)
    huggingface (cloud, ücretsiz tier)

Kullanım:
    from llm import get_client, ping_all

    client = get_client()                       # provider'a göre HF veya Ollama
    resp = client.chat(messages=[...], role="analyzer")
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Union

from .hf_client import HFClient, HFConfig, HFResponse  # noqa: F401
from .ollama_client import OllamaClient, OllamaConfig, OllamaResponse  # noqa: F401
from .prompts import PromptBuilder, build_agent_prompt  # noqa: F401

__all__ = [
    "HFClient",
    "HFConfig",
    "HFResponse",
    "OllamaClient",
    "OllamaConfig",
    "OllamaResponse",
    "PromptBuilder",
    "build_agent_prompt",
    "get_client",
    "get_provider",
    "ping_all",
]


def get_provider() -> str:
    """Aktif provider adı."""
    return (os.getenv("LLM_PROVIDER", "ollama") or "ollama").lower()


_default_client: Optional[Union[HFClient, OllamaClient]] = None


def get_client(provider: Optional[str] = None):
    """Factory: provider'a göre client döner."""
    global _default_client
    if _default_client is not None and provider is None:
        return _default_client
    p = (provider or get_provider()).lower()
    if p == "ollama":
        client = OllamaClient()
    elif p in ("huggingface", "hf"):
        client = HFClient()
    else:
        raise ValueError(f"Unknown LLM_PROVIDER: {p} (expected: ollama | huggingface)")
    if provider is None:
        _default_client = client
    return client


def ping_all() -> Dict[str, Any]:
    """Aktif provider'ı pingle, genel durum raporu."""
    from .hf_client import ping as hf_ping
    from .ollama_client import ping as ollama_ping

    provider = get_provider()
    result: Dict[str, Any] = {"active_provider": provider}
    if provider == "ollama":
        result["ollama"] = ollama_ping()
    elif provider in ("huggingface", "hf"):
        result["huggingface"] = hf_ping()
    return result
