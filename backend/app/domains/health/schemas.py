"""Health endpoint Pydantic şemaları."""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class HealthLevel(str, Enum):
    """3 renkli durum modeli — frontend dot component'iyle 1:1."""

    ok = "ok"             # yeşil — bağımlılık çalışıyor
    degraded = "degraded" # sarı — çalışıyor ama yavaş veya kısmi
    down = "down"         # kırmızı — erişilemiyor


class ComponentStatus(BaseModel):
    """Tek bir bağımlılığın durumu (DB, Redis, Engine, AI Gateway, Ollama)."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(..., description="Bileşen adı (ör. 'postgres')")
    label: str = Field(..., description="Kullanıcı-dostu etiket (ör. 'Veritabanı')")
    level: HealthLevel
    detail: Optional[str] = Field(
        None, description="Sorun varsa kısa açıklama (ör. 'timeout after 3s')"
    )
    latency_ms: Optional[int] = Field(
        None, description="Check süresi (ölçülebildiyse)"
    )
    optional: bool = Field(
        False,
        description=(
            "Opsiyonel bileşen mi? True ise 'down' durumu overall'a etki "
            "etmez (ör. Ollama lokal değilse — normal)"
        ),
    )


class ExtendedHealth(BaseModel):
    """Tüm sistemin genel + bileşen-bazlı durumu."""

    model_config = ConfigDict(extra="ignore")

    overall: HealthLevel = Field(
        ...,
        description=(
            "Bileşenlerin en kötüsü — zorunlu bileşenlerden biri 'down' ise "
            "'down', 'degraded' varsa 'degraded', hepsi 'ok' ise 'ok'. "
            "Opsiyonel bileşenler overall'u aşağı çekmez."
        ),
    )
    components: List[ComponentStatus]
    checked_at_unix: float
    app_name: Optional[str] = None
