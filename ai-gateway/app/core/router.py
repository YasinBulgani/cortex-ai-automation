"""
Nexus QA — AI Gateway Router
Fallback zinciri yönetimi: vLLM → Groq → Gemini → Ollama
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
from app.core.json_repair import repair_json_safe
from app.core.models import AIRequest, AIResponse, ProviderAttempt, ProviderName
from app.core.schema_contracts import SchemaContractError, validate_structured_contract
from app.providers.base import BaseProvider
from app.providers.groq_provider import GroqProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.ollama_provider import OllamaProvider

from app.providers.vllm_provider import VLLMProvider

logger = logging.getLogger(__name__)


class AIRouter:
    """
    Tüm AI isteklerini yönlendiren merkezi sınıf.

    Fallback stratejisi (PROVIDER_ORDER'a göre, *_ENABLED flag'leri ile filtrelenir):
    1. vLLM   (self-hosted)   — VLLM_ENABLED=true ile aktif, açık kaynak, en güçlü
    2. Ollama (local)         — OLLAMA_ENABLED=true (varsayılan), sınırsız, internet yok
    3. Groq   (cloud)         — GROQ_ENABLED=true, ücretsiz API, hızlı
    4. Gemini (cloud)         — GEMINI_ENABLED=true, ücretsiz API, büyük context

    AI_PROVIDER="ollama"  → Ollama zincirin başına geçer.
    AI_PROVIDER="vllm"    → vLLM zincirin başına geçer.
    AI_PROVIDER="auto"    → vLLM (varsa) → Ollama → Groq → Gemini (varsayılan).
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {
            "vllm": VLLMProvider(),
            "groq": GroqProvider(),
            "gemini": GeminiProvider(),
            "ollama": OllamaProvider(),
        }
        self._redis: Optional[object] = None  # Redis cache (lazy init)
        # Health check sonuçlarını 30s TTL ile önbellekle — her istekte vLLM'e HTTP gitmez
        self._health_cache: dict[str, dict] = {}
        self._health_cache_ts: float = 0.0
        _HEALTH_CACHE_TTL: float = 30.0
        self._health_ttl = _HEALTH_CACHE_TTL

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
            "task_type": request.task_type.value,
            "provider": request.provider.value,
            "model_override": request.model_override,
            "tenant_id": request.tenant_id,
            "project_id": request.project_id,
            "prompt_version": request.prompt_version,
            "schema_version": request.schema_version,
            "privacy_mode": request.privacy_mode,
            "json_mode": request.json_mode,
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

    def _estimate_tokens(self, text: str) -> int:
        """4 karakter ≈ 1 token (GPT/Llama için makul yaklaşım)."""
        return max(1, len(text) // 4)

    def _enforce_input_limit(self, request: AIRequest) -> AIRequest:
        """
        Toplam giriş token sayısını MAX_INPUT_TOKENS ile sınırla.
        Limit aşılırsa son user mesajını kırp; sistem ve assistant mesajları korunur.
        Kırpılamıyorsa (tek mesaj bile limiti aşıyorsa) ValueError fırlatır.
        """
        total = sum(self._estimate_tokens(m.content) for m in request.messages)
        limit = settings.MAX_INPUT_TOKENS
        if total <= limit:
            return request

        from app.core.models import Message

        messages = list(request.messages)
        # Sistem + assistant mesajlarını koru; user mesajlarından kırp (sondan başa)
        for i in range(len(messages) - 1, -1, -1):
            if messages[i].role != "user":
                continue
            current = sum(self._estimate_tokens(m.content) for m in messages)
            excess = current - limit
            new_len = max(0, len(messages[i].content) - excess * 4)
            if new_len == 0:
                messages.pop(i)
            else:
                trimmed = messages[i].content[:new_len] + "… [token limiti nedeniyle kırpıldı]"
                messages[i] = Message(role="user", content=trimmed)
            total = sum(self._estimate_tokens(m.content) for m in messages)
            if total <= limit:
                break

        if not messages:
            raise ValueError(
                f"İstek çok uzun: tahmini {total} token, limit {limit}. "
                "İçeriği bölerek gönderin."
            )

        logger.warning(
            f"Giriş token limiti aşıldı ({total} > {limit}) — "
            f"son user mesajı kırpıldı. correlation_id={request.correlation_id}"
        )
        return request.model_copy(update={"messages": messages})

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
        self._preflight_contract(request)

        # 0. Giriş token limiti
        request = self._enforce_input_limit(request)

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
                    # JSON mode ise onar ve doğrula
                    if request.json_mode:
                        repaired = repair_json_safe(content)
                        if repaired is None:
                            logger.warning(
                                f"{provider.name} geçersiz JSON döndürdü "
                                f"(deneme {attempt_num + 1}) — sonraki denemeye geçiliyor"
                            )
                            # Sonraki retry/provider'a bırak
                            attempt.success = False
                            attempt.error = "invalid_json: Geçersiz JSON yanıtı"
                            continue
                        try:
                            repaired = validate_structured_contract(request, repaired)
                        except SchemaContractError as exc:
                            logger.warning(
                                "%s schema contract ihlali kind=%s task=%s deneme=%s",
                                provider.name,
                                exc.kind,
                                exc.task_type,
                                attempt_num + 1,
                            )
                            attempt.success = False
                            attempt.error = f"{exc.kind}: {exc.detail[:160]}"
                            continue
                        import json as _json
                        content = _json.dumps(repaired, ensure_ascii=False)

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
        terminal_contract_error = self._terminal_contract_error(request, attempts)
        if terminal_contract_error is not None:
            raise terminal_contract_error
        raise RuntimeError(
            f"Tüm AI sağlayıcıları başarısız oldu. Denenenler: {tried}. "
            f"Detaylar: {[a.error for a in attempts]}"
        )

    def _preflight_contract(self, request: AIRequest) -> None:
        if not request.json_mode:
            return
        if request.task_type not in {
            request.task_type.ANALYZE_DOCUMENT,
            request.task_type.GENERATE_TEST_CASES,
            request.task_type.SUGGEST_REGRESSION,
            request.task_type.DEBUG_TEST,
        }:
            return
        if request.schema_version is None:
            raise SchemaContractError(
                kind="missing_contract",
                task_type=request.task_type.value,
                detail="schema_version is required for structured gateway tasks.",
            )

    def _terminal_contract_error(
        self,
        request: AIRequest,
        attempts: list[ProviderAttempt],
    ) -> SchemaContractError | None:
        errors = [str(item.error or "") for item in attempts if item.error]
        if not errors:
            return None
        if all(error.startswith("schema_mismatch:") for error in errors):
            return SchemaContractError(
                kind="schema_mismatch",
                task_type=request.task_type.value,
                detail=errors[-1].split(":", 1)[1].strip(),
            )
        if all(error.startswith("invalid_json:") for error in errors):
            return SchemaContractError(
                kind="invalid_json",
                task_type=request.task_type.value,
                detail="All providers returned invalid JSON for a structured task.",
            )
        return None

    async def stream_route(self, request: AIRequest):
        """
        Streaming yanıt için async generator — SSE chunk'ları yield eder.
        Streaming destekleyen ilk uygun provider'ı kullanır.
        Hiçbiri yoksa tam yanıtı tek chunk olarak döner.
        """
        request = self._enforce_input_limit(request)
        providers = await self._get_ordered_providers(request.provider)

        for provider in providers:
            if not await provider.is_available():
                continue
            try:
                async for token in provider.stream_complete(request):
                    yield token
                return
            except Exception as exc:
                logger.warning(f"[stream] {provider.name} başarısız: {exc} — sonraki provider")
                continue

        raise RuntimeError("Streaming için uygun provider bulunamadı")

    async def health_check(self, force: bool = False) -> dict[str, dict]:
        """Tüm sağlayıcıların durumu, latency ve uyarılarını döndür.

        Sonuçları 30s TTL ile önbellekler. force=True ile TTL atlanabilir.
        """
        now = time.monotonic()
        if not force and self._health_cache and (now - self._health_cache_ts) < self._health_ttl:
            return self._health_cache

        results = {}
        for name, provider in self._providers.items():
            t0 = time.monotonic()
            try:
                available = await provider.is_available()
                latency_ms = int((time.monotonic() - t0) * 1000)
            except Exception as exc:
                available = False
                latency_ms = int((time.monotonic() - t0) * 1000)
                logger.debug("Health check hatası [%s]: %s", name, exc)
            in_chain = name in settings.PROVIDER_ORDER
            results[name] = {
                "available": available,
                "in_chain": in_chain,
                "latency_ms": latency_ms,
                "model": getattr(provider, "model", None),
            }

        self._health_cache = results
        self._health_cache_ts = now
        return results


# Singleton — uygulama boyunca tek instance
ai_router = AIRouter()
