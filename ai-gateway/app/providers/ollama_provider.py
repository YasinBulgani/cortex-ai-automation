"""
Nexus QA — Ollama Provider
OpenAI-uyumlu API üzerinden local Ollama. API key gerekmez, sınırsız kullanım.
OLLAMA_BASE_URL: http://host.docker.internal:11434/v1  (OpenAI-compat endpoint)
"""
from __future__ import annotations

import json
import logging
import time
from typing import AsyncGenerator

import httpx

from app.core.config import settings
from app.core.models import AIRequest
from .base import BaseProvider

logger = logging.getLogger(__name__)

# /api/tags sorgusunu kaç saniye önbellekle — her istekte HTTP git mesin.
_MODEL_LIST_TTL: float = 60.0


class OllamaProvider(BaseProvider):
    """Ollama local LLM — OpenAI-uyumlu API ile."""

    name = "ollama"
    supports_streaming = True

    def __init__(self):
        self._model_list_cache: list[str] = []
        self._model_list_ts: float = 0.0

    @property
    def model(self) -> str:
        return settings.OLLAMA_MODEL

    @property
    def _api_base(self) -> str:
        """OpenAI-compat API base (OLLAMA_BASE_URL, /v1 dahil)."""
        return settings.OLLAMA_BASE_URL.rstrip("/")

    @property
    def _root_base(self) -> str:
        """Ollama root URL (/v1 olmadan) — /api/tags için."""
        base = self._api_base
        if base.endswith("/v1"):
            return base[:-3]
        return base

    def _pick_model(self, request: AIRequest) -> str:
        """Request'teki model_override varsa onu kullan, yoksa task_type'a göre seç."""
        if request.model_override:
            return request.model_override
        return settings.model_for_task(request.task_type)

    async def _get_model_list(self) -> list[str]:
        """Ollama'daki yüklü model listesini TTL-önbellekli olarak döndür."""
        now = time.monotonic()
        if self._model_list_cache and (now - self._model_list_ts) < _MODEL_LIST_TTL:
            return self._model_list_cache
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                response = await client.get(f"{self._root_base}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    self._model_list_cache = [m["name"] for m in data.get("models", [])]
                    self._model_list_ts = now
                    return self._model_list_cache
        except Exception as exc:
            logger.debug(f"Ollama /api/tags hatası: {exc}")
        return self._model_list_cache  # Önbellekteki eski liste (boş olabilir)

    async def is_available(self) -> bool:
        if not settings.OLLAMA_ENABLED:
            return False
        available = await self._get_model_list()
        if not available:
            logger.debug("Ollama erişilemiyor veya model listesi boş")
            return False
        # Model adı "qwen2.5:14b" gibi olabilir — tam eşleşme veya prefix
        targets = [
            settings.OLLAMA_MODEL_ANALYST,
            settings.OLLAMA_MODEL_FAST,
            settings.OLLAMA_MODEL_CODER,
            settings.OLLAMA_MODEL,
            settings.OLLAMA_FALLBACK_MODEL,
        ]
        for target in targets:
            if any(a == target or a.startswith(target.split(":")[0]) for a in available):
                return True
        logger.debug(f"Ollama çalışıyor ama hiçbir hedef model yok: {available}")
        return False

    async def _find_available_model(self, preferred: str) -> str:
        """Tercih edilen model yoksa aynı aileden veya fallback'e dön."""
        available = await self._get_model_list()
        # Tam eşleşme
        if preferred in available:
            return preferred
        # Aynı model ailesi (örn. "qwen2.5" → "qwen2.5:7b")
        family = preferred.split(":")[0]
        for a in available:
            if a.startswith(family):
                logger.info(f"Ollama: {preferred} yok, {a} kullanılıyor")
                return a
        return settings.OLLAMA_FALLBACK_MODEL

    async def complete(self, request: AIRequest) -> str:
        """Ollama OpenAI-uyumlu API (/v1/chat/completions) ile tamamlama."""
        preferred = self._pick_model(request)
        model = await self._find_available_model(preferred)

        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            # keep_alive=-1 → model RAM'de kalır, bir sonraki çağrıda yükleme süresi (~30-60s) ortadan kalkar.
            # Ollama OpenAI-compat API v0.1.33+ destekler.
            "keep_alive": -1,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        try:
            async with httpx.AsyncClient(
                timeout=settings.REQUEST_TIMEOUT_SECONDS * 2,  # Ollama local, daha yavaş
            ) as client:
                response = await client.post(
                    f"{self._api_base}/chat/completions",
                    json=payload,
                    headers={"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"},
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise TimeoutError(f"Ollama isteği zaman aşımı: {exc}") from exc
        except ValueError as exc:
            raise ValueError(f"Ollama yanıtı JSON formatta değil: {exc}") from exc
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama HTTP hatası: {exc}") from exc

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(f"Ollama yanıtı beklenen formatta değil: {data}") from exc
        logger.info(f"Ollama başarılı. Model: {model} (istenen: {preferred})")
        return content

    async def stream_complete(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """Ollama'dan token token SSE chunk yield eder."""
        preferred = self._pick_model(request)
        model = await self._find_available_model(preferred)
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "keep_alive": -1,  # model RAM'de kalır
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(
            timeout=settings.REQUEST_TIMEOUT_SECONDS * 2,
        ) as client:
            async with client.stream(
                "POST",
                f"{self._api_base}/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {settings.OLLAMA_API_KEY}"},
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_part = line[5:].strip()
                    if data_part == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_part)
                        delta = chunk["choices"][0].get("delta", {})
                        token = delta.get("content", "")
                        if token:
                            yield token
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
