"""
Nexus QA — g4f (GPT4Free) Provider
Son çare fallback. API key gerektirmez, resmi olmayan yollarla GPT/Gemini erişimi.
NOT: Güvenilirliği düşük, sadece diğer tüm sağlayıcılar başarısız olursa kullanılır.
"""
from __future__ import annotations

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from app.core.config import settings
from app.core.models import AIRequest
from .base import BaseProvider

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


class G4FProvider(BaseProvider):
    """GPT4Free — son çare fallback sağlayıcısı."""

    name = "g4f"

    @property
    def model(self) -> str:
        return settings.G4F_MODEL

    async def is_available(self) -> bool:
        if not settings.G4F_ENABLED:
            return False
        try:
            import g4f  # noqa
            return True
        except ImportError:
            logger.debug("g4f kütüphanesi yüklü değil, atlanıyor.")
            return False

    def _sync_complete(self, messages: list[dict], model: str) -> str:
        """g4f senkron çağrısını thread pool'da çalıştır."""
        import g4f
        response = g4f.ChatCompletion.create(
            model=model,
            messages=messages,
        )
        return response

    async def complete(self, request: AIRequest) -> str:
        """g4f async wrapper."""
        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        loop = asyncio.get_event_loop()
        try:
            content = await asyncio.wait_for(
                loop.run_in_executor(
                    _executor,
                    self._sync_complete,
                    messages,
                    settings.G4F_MODEL,
                ),
                timeout=settings.REQUEST_TIMEOUT_SECONDS,
            )
        except TimeoutError as exc:
            raise TimeoutError(f"g4f isteği zaman aşımı: {settings.REQUEST_TIMEOUT_SECONDS}s") from exc
        if not content:
            raise ValueError("g4f boş yanıt döndürdü")
        logger.info(f"g4f başarılı. Model: {settings.G4F_MODEL}")
        return str(content)
