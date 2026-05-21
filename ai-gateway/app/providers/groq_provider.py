"""
Nexus QA — Groq Provider
Groq API ile llama3-70b-8192 modeli. Ücretsiz tier: 30 RPM, 14400 TPM.
"""
from __future__ import annotations

import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings
from app.core.models import AIRequest
from .base import BaseProvider

logger = logging.getLogger(__name__)


class GroqProvider(BaseProvider):
    """Groq llama3-70b — hızlı ve ücretsiz."""

    name = "groq"
    supports_streaming = True

    @property
    def model(self) -> str:
        return settings.GROQ_MODEL

    async def is_available(self) -> bool:
        if not settings.GROQ_ENABLED:
            return False
        if not settings.GROQ_API_KEY:
            logger.debug("Groq: API key eksik, atlanıyor.")
            return False
        return True

    async def complete(self, request: AIRequest) -> str:
        """Groq OpenAI-uyumlu API ile tamamlama."""
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    f"{settings.GROQ_BASE_URL}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.GROQ_MODEL,
                        "messages": messages,
                        "temperature": request.temperature,
                        "max_tokens": min(request.max_tokens, 8192),
                        **(
                            {"response_format": {"type": "json_object"}}
                            if request.json_mode
                            else {}
                        ),
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Groq isteği zaman aşımı: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"Groq yanıtı JSON formatta değil: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Groq HTTP hatası: {exc}") from exc

        try:
            choices = data["choices"]
            message = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Groq yanıtı beklenen formatta değil: {data}") from exc

        content = message
        logger.info(f"Groq başarılı. Model: {settings.GROQ_MODEL}, "
                    f"tokens: {data.get('usage', {}).get('total_tokens', 0)}")
        return content

    async def stream_complete(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Groq OpenAI-uyumlu SSE streaming."""
        import json as _json
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                f"{settings.GROQ_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": messages,
                    "temperature": request.temperature,
                    "max_tokens": min(request.max_tokens, 8192),
                    "stream": True,
                    **({"response_format": {"type": "json_object"}} if request.json_mode else {}),
                },
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_part = line[5:].strip()
                    if data_part == "[DONE]":
                        break
                    try:
                        chunk = _json.loads(data_part)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (_json.JSONDecodeError, KeyError, IndexError):
                        continue
