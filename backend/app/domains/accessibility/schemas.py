"""Accessibility analyzer için Pydantic schema'ları.

Hem HTTP boundary (ileride router eklenince) hem internal analyzer API'si
bu modelleri kullanır. axe-core çıktı formatına uyumlu:
https://github.com/dequelabs/axe-core/blob/develop/doc/API.md#results-object
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class A11yImpact(str, Enum):
    """WCAG violation severity. axe-core'un "impact" alanıyla aynı."""

    minor = "minor"
    moderate = "moderate"
    serious = "serious"
    critical = "critical"


class A11yNode(BaseModel):
    """İhlalin tespit edildiği DOM düğümü (axe-core node formatı subset)."""

    model_config = ConfigDict(extra="ignore")

    html: Optional[str] = Field(
        None,
        description="DOM düğümünün outer HTML'i (kısa tutulmalı, LLM input'a giriyor)",
    )
    target: Optional[List[str]] = Field(
        None, description="CSS selector yolu (axe-core target array)"
    )
    failure_summary: Optional[str] = Field(
        None, description="axe-core'un ürettiği İngilizce kısa özet"
    )


class A11yViolation(BaseModel):
    """Tek bir WCAG violation (axe-core violations[] elemanı)."""

    model_config = ConfigDict(extra="ignore")

    id: str = Field(..., description="axe-core rule id (ör: 'color-contrast')")
    impact: Optional[A11yImpact] = None
    help: Optional[str] = Field(
        None, description="İngilizce kural adı / kısa açıklama"
    )
    help_url: Optional[str] = Field(None, description="WCAG/axe-core dokümantasyon linki")
    description: Optional[str] = Field(
        None, description="axe-core'un ayrıntılı İngilizce açıklaması"
    )
    tags: Optional[List[str]] = Field(
        None, description="WCAG seviyeleri/kategorileri (ör: ['wcag2aa', 'wcag143'])"
    )
    nodes: List[A11yNode] = Field(default_factory=list)


class A11yRemediation(BaseModel):
    """LLM'in tek bir violation için ürettiği Türkçe düzeltme önerisi."""

    violation_id: str = Field(..., description="Karşılık gelen violation.id")
    turkish_title: str = Field(
        ..., description="Kısa Türkçe başlık (ekranda gösterim için)"
    )
    turkish_explanation: str = Field(
        ...,
        description=(
            "Kullanıcı-dostu Türkçe açıklama: etki kime, nasıl, hangi "
            "bağlamda (ekran okuyucu / klavye nav / düşük görüş)"
        ),
    )
    remediation: str = Field(
        ..., description="Somut düzeltme adımları (madde madde mümkünse)"
    )
    code_example: Optional[str] = Field(
        None,
        description="Öncesi/sonrası HTML veya kod örneği (varsa)",
    )
    wcag_reference: Optional[str] = Field(
        None, description="İlgili WCAG kriteri (ör: '1.4.3 Contrast (Minimum)')"
    )


class AnalyzeA11yRequest(BaseModel):
    """Analyzer servisine gelen istek."""

    model_config = ConfigDict(extra="ignore")

    violations: List[A11yViolation] = Field(
        ..., min_length=1, description="En az 1 violation analiz edilecek"
    )
    url: Optional[str] = Field(
        None, description="Taranan sayfa URL'si (LLM bağlamı için opsiyonel)"
    )
    max_violations: int = Field(
        10,
        ge=1,
        le=50,
        description="LLM'e tek seferde gönderilecek maksimum violation — "
        "maliyet ve context window koruması",
    )


class AnalyzeA11yResponse(BaseModel):
    """Analyzer yanıtı."""

    ok: bool
    remediations: List[A11yRemediation] = Field(default_factory=list)
    skipped_count: int = Field(
        0, description="max_violations nedeniyle gönderilmeyen ihlal sayısı"
    )
    error: Optional[str] = Field(
        None,
        description="Gateway erişilemezse veya LLM hata verirse insan-okur mesaj",
    )
    latency_ms: Optional[int] = None
