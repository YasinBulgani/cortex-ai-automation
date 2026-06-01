"""products service — ürün telemetri ve dashboard mantığı.

Router, bu modülün fonksiyonlarını kullanır. Demo veri üretimini,
geçerlilik kontrollerini ve istatistik hesaplamalarını burada merkezileştirir.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone
from typing import Any

import logging

logger = logging.getLogger(__name__)

VALID_PRODUCT_IDS = {
    "one", "studio", "service", "web", "mobile",
    "data", "intelligence", "nexus-code",
}


def _sparkline(base: int, n: int = 7) -> list[int]:
    """Rastgele sparkline dizisi üretir (telemetri grafikleri için)."""
    vals: list[int] = []
    v = base
    for _ in range(n):
        v = max(0, v + random.randint(-5, 8))
        vals.append(v)
    return vals


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_product_id(product_id: str) -> None:
    """Geçersiz product_id için ValueError fırlatır."""
    if product_id not in VALID_PRODUCT_IDS:
        raise ValueError(f"Geçersiz product_id: {product_id!r}. Geçerli: {sorted(VALID_PRODUCT_IDS)}")


def get_telemetry(product_id: str) -> dict[str, Any]:
    """Ürüne özel telemetri verisi döner.

    Şu an demo/simüle veri döndürür; gerçek implementasyon için
    run/test aggregation servisleri ile entegre edilmeli.
    isDemo=True flag'i frontend'e bunun canlı veri olmadığını bildirir.
    """
    validate_product_id(product_id)

    # Ürün bazlı temel istatistikler (gelecekte DB'den gelecek)
    _STATS: dict[str, list[dict]] = {
        "intelligence": [
            {"label": "AI Senaryo", "value": 142, "unit": "adet", "trend": "up"},
            {"label": "Ortalama Skor", "value": 87, "unit": "%", "trend": "up"},
            {"label": "Hata Tespiti", "value": 23, "unit": "adet", "trend": "down"},
        ],
        "web": [
            {"label": "Test Koşusu", "value": 312, "unit": "adet", "trend": "up"},
            {"label": "Başarı Oranı", "value": 94, "unit": "%", "trend": "stable"},
            {"label": "Görsel Diff", "value": 7, "unit": "adet", "trend": "down"},
        ],
    }

    stats_template = _STATS.get(product_id, [
        {"label": "Aktif Test", "value": 50, "unit": "adet", "trend": "stable"},
        {"label": "Başarı Oranı", "value": 90, "unit": "%", "trend": "stable"},
    ])

    now = _now_iso()
    stats = [
        {
            **s,
            "value": max(0, s["value"] + random.randint(-2, 3)),
            "sparkline": _sparkline(int(s["value"])),
            "delta": random.choice([-1, 0, 1, 2]),
            "deltaLabel": "bu hafta",
        }
        for s in stats_template
    ]

    return {
        "productId": product_id,
        "stats": stats,
        "aiInsights": [],
        "recentActivity": [],
        "onboarding": [],
        "lastUpdated": now,
        "isDemo": True,  # Gerçek aggregation bağlandığında False yapılır
    }


def list_valid_products() -> list[str]:
    """Desteklenen ürün ID listesi."""
    return sorted(VALID_PRODUCT_IDS)
