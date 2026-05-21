"""
LLM Bridge — core/ modüllerini services/LLMGateway'e bağlayan köprü.

LLMGateway mevcutsa PII sanitization, caching ve maliyet takibiyle çalışır.
Yoksa mevcut AIEngine._call_llm() fallback'ine düşer.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.llm_gateway import LLMGateway

logger = logging.getLogger(__name__)

_gateway: LLMGateway | None = None


def set_gateway(gateway: LLMGateway) -> None:
    """Modül seviyesinde LLMGateway ayarla."""
    global _gateway
    _gateway = gateway


def get_gateway() -> LLMGateway | None:
    """Mevcut gateway'i döndür. Yoksa services'dan almayı dene."""
    global _gateway
    if _gateway is not None:
        return _gateway
    try:
        from services import get_llm_gateway
        gw = get_llm_gateway()
        if gw.available:
            _gateway = gw
            return _gateway
    except Exception as exc:
        logger.debug("LLM gateway lazy load atlandı: %s", exc)
    return None


def call_llm(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    model: str | None = None,
    max_tokens: int = 2000,
) -> str:
    """
    Unified LLM çağrısı. Gateway varsa onu kullanır, yoksa AIEngine fallback.

    Returns:
        LLM yanıt metni (string)
    """
    gw = get_gateway()
    if gw is not None:
        try:
            resp = gw.complete(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.content.strip()
        except Exception as e:
            logger.warning("LLMGateway call failed, falling back to AIEngine: %s", e)

    from core.ai_engine import AIEngine
    engine = AIEngine()
    return engine._call_llm(messages, temperature=temperature)
