"""LLM Orchestrator - Model routing, fallback, cost tracking."""

import asyncio
import json
from typing import Dict, Any, Optional, List
from enum import Enum

from backend.app.core.logger import get_logger
from backend.app.core.http_client import httpx_client

logger = get_logger(__name__)


class TaskType(str, Enum):
    """Task types determine model selection."""
    ANALYZE = "ANALYZE"  # Long reasoning, quality > speed (qwen2.5:14b)
    CODER = "CODER"  # Code generation (qwen2.5-coder:7b)
    FAST = "FAST"  # Speed critical (llama3.1:8b)
    CHAT = "CHAT"  # General purpose (GPT-4, Claude)


class ModelConfig:
    """Model configuration."""

    ROUTING = {
        TaskType.ANALYZE: {
            "models": ["ollama/qwen2.5:14b", "groq/mixtral-8x7b", "gpt-4o"],
            "max_tokens": 2000,
            "temperature": 0.3,
            "timeout": 10,
        },
        TaskType.CODER: {
            "models": ["ollama/qwen2.5-coder:7b", "gpt-4o", "claude-opus-4.8"],
            "max_tokens": 4000,
            "temperature": 0.1,
            "timeout": 15,
        },
        TaskType.FAST: {
            "models": ["ollama/mistral:latest", "groq/mixtral-8x7b", "gpt-4o-mini"],
            "max_tokens": 500,
            "temperature": 0.5,
            "timeout": 3,
        },
        TaskType.CHAT: {
            "models": ["gpt-4o", "claude-opus-4.8", "ollama/mistral:latest"],
            "max_tokens": 2000,
            "temperature": 0.7,
            "timeout": 8,
        },
    }

    PRICING = {
        "gpt-4o": {"input": 0.03 / 1000, "output": 0.06 / 1000},
        "gpt-4o-mini": {"input": 0.0005 / 1000, "output": 0.0015 / 1000},
        "claude-opus-4.8": {"input": 0.015 / 1000, "output": 0.045 / 1000},
        "groq/mixtral-8x7b": {"input": 0.0002 / 1000, "output": 0.0006 / 1000},
        "ollama/qwen2.5:14b": {"input": 0, "output": 0},  # Free (local)
        "ollama/qwen2.5-coder:7b": {"input": 0, "output": 0},
        "ollama/mistral:latest": {"input": 0, "output": 0},
    }


class LLMOrchestrator:
    """Orchestrate LLM calls with routing, fallback, and cost tracking."""

    def __init__(self):
        self.ai_gateway_url = "http://ai-gateway:8080"  # Internal endpoint
        self.timeout = 30
        self.model_cache = {}

    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        task_type: TaskType = TaskType.ANALYZE,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Call LLM with fallback chain.

        Returns:
            {
                "output": "LLM response",
                "model": "model_name",
                "tokens_input": 123,
                "tokens_output": 456,
                "cost_usd": 0.05,
                "latency_ms": 1500,
            }
        """
        config = ModelConfig.ROUTING.get(task_type)
        if not config:
            raise ValueError(f"Unknown task type: {task_type}")

        max_tokens = max_tokens or config["max_tokens"]
        models = config["models"]

        # Try each model in fallback chain
        for model in models:
            try:
                result = await self._call_single_model(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=max_tokens,
                    temperature=config["temperature"],
                    timeout=config["timeout"],
                )
                return result
            except Exception as e:
                logger.warning(f"Model {model} failed: {e}, trying next...")
                continue

        # All models exhausted
        logger.error(f"All models failed for task {task_type}")
        raise RuntimeError(f"All LLM models failed for task {task_type}")

    async def _call_single_model(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        temperature: float,
        timeout: int,
    ) -> Dict[str, Any]:
        """Call single model via AI Gateway."""
        import time

        start_time = time.time()

        # Prepare payload
        payload = {
            "model": model,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        # Call AI Gateway
        try:
            response = await asyncio.wait_for(
                httpx_client.post(
                    f"{self.ai_gateway_url}/api/v1/complete",
                    json=payload,
                    headers={"X-Internal-Key": "secret_key_placeholder"},
                    timeout=timeout,
                ),
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            latency_ms = int((time.time() - start_time) * 1000)

            # Calculate tokens (rough estimation)
            tokens_input = len(system_prompt.split()) + len(user_prompt.split())
            tokens_output = len(data.get("output", "").split())

            # Calculate cost
            cost_usd = self.calculate_cost(model, tokens_input, tokens_output)

            return {
                "output": data.get("output", ""),
                "model": model,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "cost_usd": cost_usd,
                "latency_ms": latency_ms,
            }
        except asyncio.TimeoutError:
            raise RuntimeError(f"Model {model} timeout after {timeout}s")
        except Exception as e:
            raise RuntimeError(f"Model {model} error: {str(e)}")

    def calculate_cost(self, model: str, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost for an LLM call."""
        pricing = ModelConfig.PRICING.get(model, {"input": 0, "output": 0})
        input_cost = tokens_input * pricing["input"]
        output_cost = tokens_output * pricing["output"]
        return round(input_cost + output_cost, 6)

    def estimate_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """Rough token estimation (1 token ≈ 4 chars for English)."""
        if "gpt" in model:
            return len(text) // 4
        else:
            return len(text) // 3  # ~3 chars per token for open-source

    def enforce_token_budget(
        self,
        system_prompt: str,
        user_prompt: str,
        rag_context: List[str],
        max_context_tokens: int = 1500,
    ) -> str:
        """Enforce token budget by dropping lowest-priority RAG chunks."""
        system_tokens = self.estimate_tokens(system_prompt)
        user_tokens = self.estimate_tokens(user_prompt)
        reserved = system_tokens + user_tokens

        budget_remaining = max_context_tokens - reserved
        if budget_remaining <= 0:
            raise RuntimeError("System + user prompt already exceeds token budget")

        # Drop RAG chunks until within budget
        context_text = ""
        for chunk in rag_context:
            chunk_tokens = self.estimate_tokens(chunk)
            if len(context_text) + chunk_tokens <= budget_remaining:
                context_text += f"\n{chunk}"
            else:
                break

        return context_text
