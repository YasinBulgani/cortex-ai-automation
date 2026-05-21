"""
Nexus QA — Base AI Provider
Tüm sağlayıcıların implement etmesi gereken arayüz.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.core.models import AIRequest, AIResponse, ProviderAttempt


class BaseProvider(ABC):
    """Tüm AI sağlayıcılar bu sınıftan türer."""

    name: str = "base"
    model: str = "unknown"

    @abstractmethod
    async def is_available(self) -> bool:
        """Sağlayıcı kullanılabilir mi? (API key var mı, Ollama çalışıyor mu?)"""
        ...

    @abstractmethod
    async def complete(self, request: AIRequest) -> str:
        """Tamamlama isteği gönder, ham metin döndür."""
        ...

    async def safe_complete(self, request: AIRequest) -> tuple[str | None, ProviderAttempt]:
        """Hata yakalamaya alınmış tamamlama. (content, attempt) döndürür."""
        start = time.monotonic()
        attempt = ProviderAttempt(provider=self.name, success=False)
        try:
            content = await self.complete(request)
            elapsed_ms = int((time.monotonic() - start) * 1000)
            attempt.success = True
            attempt.latency_ms = elapsed_ms
            return content, attempt
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - start) * 1000)
            attempt.error = str(exc)[:200]
            attempt.latency_ms = elapsed_ms
            return None, attempt
