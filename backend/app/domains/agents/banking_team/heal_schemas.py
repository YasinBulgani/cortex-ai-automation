"""
Heal Pipeline Pydantic Schemas — API request/response modelleri.

NOT: Bu dosyada `from __future__ import annotations` KULLANILMAZ
cunku Pydantic runtime'da tip bilgisine ihtiyac duyar.
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ── Request Schemas ──────────────────────────────────────────────────────────


class HealTestEntry(BaseModel):
    """Tek bir kırık test bilgisi."""
    file: str = Field(default="", description="Test dosya yolu")
    test_name: str = Field(default="", description="Test adi")
    selector: str = Field(default="", description="Kırık selector")
    error: str = Field(default="", description="Hata mesajı")
    dom_snippet: str = Field(default="", description="DOM parcasi")
    page_url: str = Field(default="", description="Sayfa URL'si")
    line_number: int = Field(default=0, description="Hata satir numarasi")


class HealRequest(BaseModel):
    """Heal pipeline baslatma istegi."""
    project_id: Optional[str] = Field(
        default=None,
        description="Heal isleminin ait oldugu proje ID'si",
    )
    failed_tests: List[HealTestEntry] = Field(
        ...,
        description="Kırık testlerin listesi",
        min_length=1,
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Playwright MCP oturum ID'si (canli dogrulama için)",
    )
    auto_update: bool = Field(
        default=False,
        description="Dogrulanan selector'lari otomatik olarak test dosyasina yaz",
    )


# ── Response Schemas ─────────────────────────────────────────────────────────


class HealDetailEntry(BaseModel):
    """Tek bir heal sonucu detayi."""
    file: str = ""
    test_name: str = ""
    broken_selector: str = ""
    new_selector: str = ""
    healed: bool = False
    strategy: str = ""
    tier: str = ""
    confidence: float = 0.0
    verified_in_browser: bool = False
    live_dom_used: bool = False
    file_updated: bool = False
    screenshot_before: str = ""
    screenshot_after: str = ""
    error: str = ""


class HealResponse(BaseModel):
    """Heal pipeline sonuç ozeti."""
    total_broken: int = Field(default=0, description="Toplam kırık test sayisi")
    healed: int = Field(default=0, description="Tamir edilen test sayisi")
    verified: int = Field(default=0, description="Browser'da dogrulanan heal sayisi")
    updated_files: int = Field(default=0, description="Guncellenen dosya sayisi")
    duration_ms: int = Field(default=0, description="Toplam sure (milisaniye)")
    details: List[HealDetailEntry] = Field(default_factory=list)


# ── History / Stats Schemas ──────────────────────────────────────────────────


class HealHistoryEntry(BaseModel):
    """Geçmiş heal kaydi."""
    id: str = ""
    timestamp: str = ""
    broken_selector: str = ""
    healed_selector: str = ""
    strategy: str = ""
    tier: str = ""
    confidence: float = 0.0
    verified: bool = False
    file: str = ""
    test_name: str = ""


class HealHistoryResponse(BaseModel):
    """Heal gecmisi yaniti."""
    count: int = 0
    entries: List[HealHistoryEntry] = Field(default_factory=list)


class HealStatsResponse(BaseModel):
    """Toplam healing istatistikleri."""
    total_heals: int = Field(default=0, description="Toplam heal sayisi")
    success_rate: float = Field(default=0.0, description="Başarı orani (0-1)")
    verified_rate: float = Field(default=0.0, description="Browser dogrulama orani (0-1)")
    by_strategy: Dict[str, int] = Field(
        default_factory=dict,
        description="Strateji bazinda heal sayilari",
    )
    by_tier: Dict[str, int] = Field(
        default_factory=dict,
        description="Tier bazinda heal sayilari",
    )
    avg_confidence: float = Field(default=0.0, description="Ortalama guven skoru")
    last_heal_at: Optional[str] = Field(default=None, description="Son heal zamani")
