"""
Nexus QA — AI Gateway Router
Fallback zinciri yönetimi: groq → gemini → ollama → g4f
Rate limit tespiti, retry logic ve caching burada.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Optional

from app.core.config import settings
from app.core.models import AIRequest, AIResponse, ProviderAttempt, ProviderName
from app.providers.base import BaseProvider
from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.g4f_provider import G4FProvider
from app.providers.vllm_provider import VLLMProvider

logger = logging.getLogger(__name__)


class AIRouter:
    """
    Tüm AI isteklerini yönlendiren merkezi sınıf.

    Fallback stratejisi:
    1. Groq (llama3-70b) — hızlı, ücretsiz, tercih edilen
    2. Gemini 1.5 Flash  — güçlü, ücretsiz, iyi yedek
    3. Ollama (local)    — sınırsız, internet gerektirmez
    4. g4f               — son çare, güvenilirlik düşük
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {
            "vllm": VLLMProvider(),
            "groq": GroqProvider(),
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
            "g4f": G4FProvider(),
        }
        self._redis: Optional[object] = None  # Redis cache (lazy init)

    async def _get_redis(self):
        """Redis bağlantısını lazy başlat."""
        if self._redis is None:
            try:
                import redis.asyncio as aioredis
                self._redis = await aioredis.from_url(
                    settings.REDIS_URL, encoding="utf-8", decode_responses=True
                )
            except Exception as exc:
                logger.warning(f"Redis bağlanamadı, cache devre dışı: {exc}")
                self._redis = False  # False = devre dışı
        return self._redis if self._redis else None

    def _cache_key(self, request: AIRequest) -> str:
        """İstek için deterministik cache key üret."""
        key_data = {
            "messages": [{"role": m.role, "content": m.content} for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        raw = json.dumps(key_data, sort_keys=True, ensure_ascii=False)
        return f"nexusqa:ai:{hashlib.sha256(raw.encode()).hexdigest()[:16]}"

    async def _check_cache(self, request: AIRequest) -> Optional[str]:
        """Cache'de yanıt var mı kontrol et."""
        if request.temperature > 0.3:  # Yüksek sıcaklıkta cache kullanma
            return None
        redis = await self._get_redis()
        if not redis:
            return None
        try:
            return await redis.get(self._cache_key(request))
        except Exception:
            return None

    async def _set_cache(self, request: AIRequest, content: str) -> None:
        """Yanıtı cache'e kaydet."""
        if request.temperature > 0.3:
            return
        redis = await self._get_redis()
        if not redis:
            return
        try:
            await redis.setex(
                self._cache_key(request),
                settings.CACHE_TTL_SECONDS,
                content,
            )
        except Exception as exc:
            logger.debug(f"Cache yazma hatası: {exc}")

    def _is_rate_limit_error(self, error: str) -> bool:
        """Rate limit hatası mı? HTTP 429 veya bilinen rate limit mesajları."""
        error_lower = error.lower()
        return any(kw in error_lower for kw in [
            "rate limit", "too many requests", "429",
            "quota", "exceeded", "ratelimit", "rate_limit",
            "rateLimitExceeded",  # Gemini
            "resource_exhausted",  # Gemini gRPC kodu
            "requests per minute",  # Groq mesajı
            "please slow down",  # Ollama mesajı
            "overloaded",  # Anthropic mesajı
        ])

    def _is_timeout_error(self, error: str) -> bool:
        """Timeout veya bağlantı kesilmesi gibi geçici hatalar mı?"""
        error_lower = error.lower()
        return any(kw in error_lower for kw in (
            "timeout",
            "timed out",
            "connect timeout",
            "read timeout",
            "write timeout",
            "connection error",
            "network is unreachable",
            "temporarily unavailable",
        ))

    async def _get_ordered_providers(self, preferred: ProviderName) -> list[BaseProvider]:
        """Sıralı sağlayıcı listesini döndür."""
        if preferred != ProviderName.AUTO:
            # Belirli sağlayıcı istendi
            provider = self._providers.get(preferred.value)
            if provider:
                return [provider]
            raise ValueError(f"Bilinmeyen sağlayıcı: {preferred}")

        # Otomatik sıra: AI_PROVIDER=ollama ise Ollama önce, yoksa config sırası
        ordered = []
        for name in settings.PROVIDER_ORDER:
            p = self._providers.get(name)
            if p:
                ordered.append(p)
        return ordered

    async def route(self, request: AIRequest) -> AIResponse:
        """
        İsteği uygun sağlayıcıya yönlendir.
        Tüm fallback'ler başarısız olursa RuntimeError fırlatır.
        """
        start_total = time.monotonic()
        attempts: list[ProviderAttempt] = []

        # 1. Cache kontrolü
        cached = await self._check_cache(request)
        if cached:
            logger.info(f"Cache hit! correlation_id={request.correlation_id}")
            return AIResponse(
                content=cached,
                provider_used="cache",
                model_used="cache",
                attempts=[],
                cached=True,
                latency_ms=0,
                correlation_id=request.correlation_id,
            )

        # 2. Sağlayıcı sırasını belirle
        providers = await self._get_ordered_providers(request.provider)
        if not providers:
            raise RuntimeError("Kullanılabilir AI sağlayıcısı bulunamadı.")

        # 3. Fallback zinciri
        for provider in providers:
            if not await provider.is_available():
                logger.debug(f"Sağlayıcı atlandı (mevcut değil): {provider.name}")
                attempts.append(
                    ProviderAttempt(
                        provider=provider.name,
                        success=False,
                        error="provider_unavailable",
                        latency_ms=0,
                    )
                )
                continue

            # Retry loop (max 3)
            for attempt_num in range(settings.MAX_RETRIES):
                content, attempt = await provider.safe_complete(request)
                attempts.append(attempt)

                if content is not None:
                    # Başarı!
                    total_ms = int((time.monotonic() - start_total) * 1000)
                    await self._set_cache(request, content)
                    logger.info(
                        f"AI yanıtı alındı. sağlayıcı={provider.name} "
                        f"deneme={attempt_num + 1} süre={total_ms}ms"
                    )
                    return AIResponse(
                        content=content,
                        provider_used=provider.name,
                        model_used=provider.model,
                        attempts=attempts,
                        latency_ms=total_ms,
                        correlation_id=request.correlation_id,
                    )

                if not attempt.error:
                    continue

                # Rate limit veya timeout ise kısa backoff ile aynı sağlayıcıda retry
                if (
                    self._is_rate_limit_error(attempt.error)
                    or self._is_timeout_error(attempt.error)
                ):
                    wait = settings.RETRY_DELAY_SECONDS * (2 ** attempt_num)
                    logger.warning(
                        f"{provider.name} geçici hata — {wait:.1f}s bekleniyor "
                        f"(deneme {attempt_num + 1}/{settings.MAX_RETRIES})"
                    )
                    await asyncio.sleep(wait)
                else:
                    # Rate limit değil, bir sonraki sağlayıcıya geç
                    logger.warning(
                        f"{provider.name} başarısız: {attempt.error} — "
                        f"sonraki sağlayıcıya geçiliyor"
                    )
                    break

        # Tüm sağlayıcılar başarısız
        tried = [a.provider for a in attempts if a.provider != "cache" and a.success is False]
        raise RuntimeError(
            f"Tüm AI sağlayıcıları başarısız oldu. Denenenler: {tried}. "
            f"Detaylar: {[a.error for a in attempts]}"
        )

    async def health_check(self) -> dict[str, bool]:
        """Tüm sağlayıcıların durumunu kontrol et."""
        results = {}
        for name, provider in self._providers.items():
            try:
                results[name] = await provider.is_available()
            except Exception:
                results[name] = False
        return results


# Singleton — uygulama boyunca tek instance
ai_router = AIRouter()
