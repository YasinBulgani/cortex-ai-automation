"""
Nexus QA — Gemini Provider
Google Gemini 1.5 Flash. Ücretsiz tier: 15 RPM, 1.5M TPD.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncGenerator

import httpx

from app.core.config import settings
from app.core.models import AIRequest
from .base import BaseProvider

logger = logging.getLogger(__name__)

_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
# API key header'da — URL'de olursa access log'lara düşer.
GEMINI_API_URL = f"{_GEMINI_BASE}/{{model}}:generateContent"
GEMINI_STREAM_URL = f"{_GEMINI_BASE}/{{model}}:streamGenerateContent?alt=sse"


class GeminiProvider(BaseProvider):
    """Google Gemini 1.5 Flash — ücretsiz ve kapasiteli."""

    name = "gemini"
    supports_streaming = True

    @property
    def model(self) -> str:
        return settings.GEMINI_MODEL

    async def is_available(self) -> bool:
        if not settings.GEMINI_ENABLED:
            return False
        if not settings.GEMINI_API_KEY:
            logger.debug("Gemini: API key eksik, atlanıyor.")
            return False
        return True

    def _build_gemini_messages(self, request: AIRequest) -> tuple[str | None, list[dict]]:
        """Mesajları Gemini formatına çevir. (system_instruction, contents) döndürür."""
        system_instruction = None
        contents = []

        for msg in request.messages:
            if msg.role == "system":
                system_instruction = msg.content
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": msg.content}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": msg.content}]})

        # Gemini en az bir user mesajı ister
        if not contents:
            contents.append({"role": "user", "parts": [{"text": "Merhaba"}]})

        return system_instruction, contents

    async def complete(self, request: AIRequest) -> str:
        """Gemini REST API ile tamamlama."""
        system_instruction, contents = self._build_gemini_messages(request)

        gen_config: dict = {
            "temperature": request.temperature,
            "maxOutputTokens": min(request.max_tokens, 8192),
        }
        if request.json_mode:
            gen_config["responseMimeType"] = "application/json"

        payload: dict = {
            "contents": contents,
            "generationConfig": gen_config,
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        url = GEMINI_API_URL.format(model=settings.GEMINI_MODEL)
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY}

        try:
            async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Gemini isteği zaman aşımı: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"Gemini yanıtı JSON formatta değil: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Gemini HTTP hatası: {exc}") from exc

        try:
            content = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Gemini yanıtı beklenen formatta değil: {data}") from exc
        logger.info(f"Gemini başarılı. Model: {settings.GEMINI_MODEL}")
        return content

    async def stream_complete(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Gemini SSE streaming — token token yanıt yield eder."""
        system_instruction, contents = self._build_gemini_messages(request)

        gen_config: dict = {
            "temperature": request.temperature,
            "maxOutputTokens": min(request.max_tokens, 8192),
        }
        if request.json_mode:
            gen_config["responseMimeType"] = "application/json"

        payload: dict = {"contents": contents, "generationConfig": gen_config}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        url = GEMINI_STREAM_URL.format(model=settings.GEMINI_MODEL)
        headers = {"x-goog-api-key": settings.GEMINI_API_KEY}

        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT_SECONDS) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_part = line[5:].strip()
                    if data_part == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_part)
                        text = chunk["candidates"][0]["content"]["parts"][0]["text"]
                        if text:
                            yield text
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
