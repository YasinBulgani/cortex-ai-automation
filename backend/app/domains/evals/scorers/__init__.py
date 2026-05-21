"""Scorer paketi — pure, yan etkisiz skorlama fonksiyonları.

Yeni scorer eklerken:
    1. Aynı dizine yeni bir modül aç
    2. ``Scorer`` protokolünü (``schemas.Scorer``) uygula
    3. ``scorers/__init__.py`` içindeki registry'e kaydet

Registry ile çalışmak suite YAML'lerinin Python import yapmadan sadece
isim ile referans verebilmesini sağlar.
"""
from __future__ import annotations

from typing import Dict

from ..schemas import Scorer
from . import (
    code_validity,
    exact_match,
    gateway_contract,
    injection_blocked,
    locator_match,
    retrieval_metrics,
)

_REGISTRY: Dict[str, Scorer] = {
    exact_match.ExactMatchScorer.name: exact_match.ExactMatchScorer(),
    retrieval_metrics.PrecisionAtKScorer.name: retrieval_metrics.PrecisionAtKScorer(k=1),
    "precision_at_5": retrieval_metrics.PrecisionAtKScorer(name="precision_at_5", k=5),
    retrieval_metrics.MRRScorer.name: retrieval_metrics.MRRScorer(),
    retrieval_metrics.RecallAtKScorer.name: retrieval_metrics.RecallAtKScorer(k=5),
    # Dalga 1 · code validity
    code_validity.PythonAstValidScorer.name: code_validity.PythonAstValidScorer(),
    code_validity.PythonHasAssertScorer.name: code_validity.PythonHasAssertScorer(),
    code_validity.PythonHasTestIdScorer.name: code_validity.PythonHasTestIdScorer(),
    # Dalga 1 · self-heal
    locator_match.LocatorExactScorer.name: locator_match.LocatorExactScorer(),
    locator_match.LocatorContainsAnyScorer.name: locator_match.LocatorContainsAnyScorer(),
    # Dalga 1 · safety
    injection_blocked.InjectionBlockedScorer.name: injection_blocked.InjectionBlockedScorer(),
    injection_blocked.PiiRedactedScorer.name: injection_blocked.PiiRedactedScorer(),
    injection_blocked.NoForbiddenPhraseScorer.name: injection_blocked.NoForbiddenPhraseScorer(),
    # Dalga 2 · AI Gateway contract
    gateway_contract.GatewayContentContainsScorer.name: gateway_contract.GatewayContentContainsScorer(),
    gateway_contract.GatewayJsonValidScorer.name: gateway_contract.GatewayJsonValidScorer(),
    gateway_contract.GatewayProviderAllowedScorer.name: gateway_contract.GatewayProviderAllowedScorer(),
    gateway_contract.GatewayAttemptsHealthyScorer.name: gateway_contract.GatewayAttemptsHealthyScorer(),
    gateway_contract.GatewayLatencyBudgetScorer.name: gateway_contract.GatewayLatencyBudgetScorer(),
}


def get_scorer(name: str) -> Scorer:
    """İsme göre scorer döner. Bilinmiyorsa ``KeyError``."""
    if name not in _REGISTRY:
        raise KeyError(
            f"Scorer bulunamadı: '{name}'. Mevcutlar: {sorted(_REGISTRY)}"
        )
    return _REGISTRY[name]


def register_scorer(scorer: Scorer) -> None:
    """Test/extensibility için manuel kayıt. Aynı isim varsa override eder."""
    _REGISTRY[scorer.name] = scorer


def list_scorers() -> list[str]:
    return sorted(_REGISTRY)
