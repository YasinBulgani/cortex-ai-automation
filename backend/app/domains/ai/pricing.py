"""Model/provider fiyatlandırma — token → USD hesabı.

.. deprecated:: 2026-Q2
    Fiyat bilgisi artık ``infra/registry/model_registry.yaml`` tek kaynağında.
    Bu modül geriye dönük uyumluluk için korunur; altta ``model_registry``'ye
    delegasyon yapar. Yeni kod ``from app.domains.ai.model_registry import
    compute_cost_usd, get_model_info`` kullanmalıdır.

Eski API (``compute_cost_usd``, ``lookup_price``, ``ModelPrice``, ``known_models``)
değişmedi; çağrı yerleri etkilenmez.
"""
from __future__ import annotations

import logging
from typing import Tuple

from app.domains.ai.model_registry import (
    ModelPrice,
    compute_cost_usd,
    known_models,
    lookup_price,
)

logger = logging.getLogger(__name__)

__all__ = ("ModelPrice", "compute_cost_usd", "known_models", "lookup_price")
