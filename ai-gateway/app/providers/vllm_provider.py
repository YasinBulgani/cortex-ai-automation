"""
Nexus QA — vLLM Provider (açık kaynak, self-hosted)
OpenAI-uyumlu API üzerinden self-hosted vLLM sunucusu.

vLLM (https://docs.vllm.ai) büyük dil modellerini PagedAttention ve continuous
batching ile sunar; ``POST /v1/chat/completions`` endpoint'i OpenAI ile
bitişik uyumludur.

Varsayılan: kapalı (opt-in). ``VLLM_ENABLED=true`` ayarı ile devreye alınır.

Önerilen modeller (Apache-2.0 / MIT ağırlıklı):
- Qwen/Qwen2.5-72B-Instruct        (ana muhakeme)
- Qwen/Qwen2.5-Coder-32B-Instruct  (kod üretimi)
- meta-llama/Llama-3.3-70B-Instruct
- deepseek-ai/DeepSeek-V3
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


class VLLMProvider(BaseProvider):
    """vLLM self-hosted inference — OpenAI-uyumlu API ile."""

    name = "vllm"
    supports_streaming = True

    @property
    def model(self) -> str:
        return settings.VLLM_MODEL

    @property
    def _api_base(self) -> str:
        """OpenAI-compat API base (VLLM_BASE_URL, /v1 dahil)."""
        return settings.VLLM_BASE_URL.rstrip("/")

    def _headers(self) -> dict[str, str]:
        """Auth header — vLLM --api-key ile başlatılmışsa gerekir."""
        headers = {"Content-Type": "application/json"}
        if settings.VLLM_API_KEY:
            headers["Authorization"] = f"Bearer {settings.VLLM_API_KEY}"
        return headers

    @staticmethod
    def _model_matches(target: str, loaded: str) -> bool:
        """İki model adının aynı modeli işaret edip etmediğini kontrol et.

        Tam eşleşme ya da quantization/variant suffix ile genişletilmiş prefix
        eşleşmesini kabul eder.  Separator boundary kontrolü ile yanlış
        pozitifi engeller:
          "Qwen2.5-72B-Instruct-AWQ" eşleşir   "Qwen2.5-72B-Instruct"  ✓
          "Qwen2"                    eşleşmez   "Qwen2.5-72B-Instruct"  ✓ (yanlış pozitif önlendi)
        """
        _SEP = frozenset("-_/:")
        if loaded == target:
            return True
        # Yüklü model, hedef modelin variant'ı: loaded = target + "-AWQ"
        if loaded.startswith(target) and len(loaded) > len(target) and loaded[len(target)] in _SEP:
            return True
        # Hedef model, yüklü modelin variant'ı: target = loaded + "-GPTQ"
        if target.startswith(loaded) and len(target) > len(loaded) and target[len(loaded)] in _SEP:
            return True
        return False

    def _pick_model(self, request: AIRequest) -> str:
        """model_override varsa onu kullan, yoksa VLLM_MODEL."""
        return request.model_override or settings.VLLM_MODEL

    async def is_available(self) -> bool:
        """vLLM ayakta mı ve hedef model yüklü mü?

        ``GET /v1/models`` OpenAI-uyumlu endpoint'ini sorgular; HTTP 200 ve
        listede hedef model varsa True.
        """
        if not settings.VLLM_ENABLED:
            return False
        if not settings.VLLM_BASE_URL:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self._api_base}/models",
                    headers=self._headers(),
                )
                if response.status_code != 200:
                    logger.debug(
                        "vLLM /models status=%s; provider kullanılamaz",
                        response.status_code,
                    )
                    return False
                data = response.json()
                loaded = [m.get("id") for m in data.get("data", []) if m.get("id")]
                if not loaded:
                    logger.debug("vLLM /models döndü ama model listesi boş")
                    return False
                target = settings.VLLM_MODEL
                for mid in loaded:
                    if self._model_matches(target, mid):
                        return True
                logger.info(
                    "vLLM çalışıyor fakat hedef '%s' yüklü değil. Yüklü: %s",
                    target,
                    loaded,
                )
                return False
        except Exception as exc:  # noqa: BLE001
            logger.debug("vLLM erişilemedi: %s", exc)
            return False

    async def complete(self, request: AIRequest) -> str:
        """vLLM OpenAI-compat /v1/chat/completions ile tamamlama."""
        model = self._pick_model(request)
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            # vLLM guided decoding — native OpenAI response_format desteği var
            payload["response_format"] = {"type": "json_object"}

        timeout = settings.VLLM_TIMEOUT_SECONDS
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{self._api_base}/chat/completions",
                json=payload,
                headers=self._headers(),
            )
            response.raise_for_status()
            data = response.json()

        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ValueError(
                f"vLLM yanıtı beklenen formatta değil: {data}"
            ) from exc

        if not content:
            raise ValueError("vLLM boş içerik döndürdü")

        logger.info("vLLM başarılı. Model: %s", model)
        return content

    async def stream_complete(self, request: AIRequest) -> AsyncGenerator[str, None]:
        """vLLM'den token token SSE chunk yield eder."""
        model = self._pick_model(request)
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        payload: dict = {
            "model": model,
            "messages": messages,
            "stream": True,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.json_mode:
            payload["response_format"] = {"type": "json_object"}

        async with httpx.AsyncClient(timeout=settings.VLLM_TIMEOUT_SECONDS) as client:
            async with client.stream(
                "POST",
                f"{self._api_base}/chat/completions",
                json=payload,
                headers=self._headers(),
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
