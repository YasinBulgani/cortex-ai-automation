"""Adapter paketi — eval SUT (system-under-test) çağrı noktaları.

Kayıt modeli:
    * ``dsl_retrieval``  : production `alias_index.search()` sarıcısı
    * ``static_fixture`` : test-only; inputs["_fixture"] verilen çıktıyı geri
      döner. Unit testlerde gateway'e bağımlı olmadan runner'ı koşmak için.

Yeni adapter ekleme:
    1. Bu pakete modül ekle, ``Adapter`` protokolünü uygula
    2. ``_REGISTRY`` içine yaz (alfabetik sırada)

``get_adapter(name)`` bilinmeyen adapter için ``KeyError`` raise eder —
runner bunu yakalayıp suite'i meaningful error ile raporlar.
"""
from __future__ import annotations

from typing import Dict

from ..schemas import Adapter
from . import (
    ai_gateway_adapter,
    dsl_retrieval,
    prompt_shield_adapter,
    self_heal_adapter,
    static_fixture,
    test_gen_adapter,
)

_REGISTRY: Dict[str, Adapter] = {
    ai_gateway_adapter.AiGatewayAdapter.name: ai_gateway_adapter.AiGatewayAdapter(),
    ai_gateway_adapter.AiGatewayLiveAdapter.name: ai_gateway_adapter.AiGatewayLiveAdapter(),
    dsl_retrieval.DslRetrievalAdapter.name: dsl_retrieval.DslRetrievalAdapter(),
    static_fixture.StaticFixtureAdapter.name: static_fixture.StaticFixtureAdapter(),
    # Dalga 1 · yeni eval suites
    test_gen_adapter.TestGenAdapter.name: test_gen_adapter.TestGenAdapter(),
    self_heal_adapter.SelfHealAdapter.name: self_heal_adapter.SelfHealAdapter(),
    prompt_shield_adapter.PromptShieldAdapter.name: prompt_shield_adapter.PromptShieldAdapter(),
}


def get_adapter(name: str) -> Adapter:
    if name not in _REGISTRY:
        raise KeyError(
            f"Adapter bulunamadı: '{name}'. Mevcutlar: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def register_adapter(adapter: Adapter) -> None:
    """Test/extensibility için manuel kayıt. Aynı isim varsa override eder."""
    _REGISTRY[adapter.name] = adapter


def list_adapters() -> list[str]:
    return sorted(_REGISTRY)
