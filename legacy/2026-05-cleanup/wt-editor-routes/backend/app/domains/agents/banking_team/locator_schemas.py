"""Locator Intelligence — Pydantic semalari."""
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class LocatorEntry(BaseModel):
    """Tek bir locator kaydi."""
    id: Optional[str] = None
    name: str = ""
    selector: str
    type: str = Field(default="css", description="css|xpath|testid|text|role|aria")
    page: str = Field(default="", description="Sayfa adi")
    status: str = Field(default="unknown", description="healthy|broken|warning|unknown")


class FallbackResolveRequest(BaseModel):
    """Fallback zinciri calistirma istegi."""
    project_id: Optional[str] = Field(default=None, description="Bu locator'in ait oldugu proje ID'si")
    selector: str = Field(description="Kirilan selector")
    dom_snippet: str = Field(default="", description="DOM HTML parcasi")
    page_url: str = Field(default="", description="Sayfa URL'si")
    error_message: str = Field(default="", description="Playwright hata mesaji")
    session_id: str = Field(default="", description="Playwright MCP oturum ID")
    confidence_threshold: float = Field(default=0.75, ge=0.1, le=1.0)
    context: Dict[str, Any] = Field(default_factory=dict)


class FallbackStrategyResult(BaseModel):
    strategy: str
    selector: str
    confidence: float
    stability_score: int = 0
    found: bool
    reason: str = ""
    latency_ms: int = 0


class FallbackResolveResponse(BaseModel):
    success: bool
    best_selector: Optional[str] = None
    best_strategy: Optional[str] = None
    best_confidence: float = 0.0
    best_stability: int = 0
    original_selector: str
    strategies_tried: int
    total_latency_ms: int
    all_results: List[FallbackStrategyResult]


class StabilityAnalyzeRequest(BaseModel):
    """Locator stabilite analizi istegi."""
    locators: List[LocatorEntry]
    dom_snippet: str = Field(default="", description="DOM HTML (opsiyonel, analizi zenginlestirir)")


class StabilityDetail(BaseModel):
    selector: str
    name: str = ""
    score: int = Field(ge=0, le=5)
    risk_level: str = Field(description="healthy|warning|critical")
    reasons: List[str] = Field(default_factory=list)
    suggestion: Optional[str] = None


class StabilityAnalyzeResponse(BaseModel):
    total_locators: int
    healthy: int
    warning: int
    critical: int
    avg_score: float
    details: List[StabilityDetail]
    improvements: List[Dict[str, Any]] = Field(default_factory=list)


class ImproveSuggestRequest(BaseModel):
    """Zayif locator'lar icin iyilestirme onerisi."""
    locators: List[LocatorEntry]
    dom_snippet: str = Field(default="", description="DOM HTML")


class ImproveSuggestion(BaseModel):
    original_selector: str
    original_score: int
    suggested_selector: str
    suggested_score: int
    improvement_reason: str
    confidence: float = 0.0


class ImproveSuggestResponse(BaseModel):
    suggestions: List[ImproveSuggestion]
    total_improved: int


class POMGenerateRequest(BaseModel):
    """Page Object Model uretme istegi."""
    page_name: str = Field(description="Sayfa adi (or. LoginPage)")
    page_url: str = Field(default="", description="Sayfa URL'si")
    elements: List[Dict[str, Any]] = Field(default_factory=list, description="DOM elementleri (Playwright MCP'den)")
    session_id: str = Field(default="", description="Aktif Playwright oturum ID")
    language: str = Field(default="typescript", description="typescript|python")


class POMGenerateResponse(BaseModel):
    page_name: str
    language: str
    code: str
    element_count: int
    file_name: str


class BreakagePredictRequest(BaseModel):
    """Kirilma riski tahmini."""
    locators: List[LocatorEntry]
    recent_changes: str = Field(default="", description="Son kod degisiklikleri (git diff)")


class BreakagePrediction(BaseModel):
    selector: str
    name: str = ""
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_factors: List[str] = Field(default_factory=list)
    recommendation: str = ""


class BreakagePredictResponse(BaseModel):
    predictions: List[BreakagePrediction]
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class TrendAnalysisResponse(BaseModel):
    """Heal trend analizi."""
    total_heals: int
    by_strategy: Dict[str, int] = Field(default_factory=dict)
    by_tier: Dict[str, int] = Field(default_factory=dict)
    most_broken_selectors: List[Dict[str, Any]] = Field(default_factory=list)
    most_broken_pages: List[Dict[str, Any]] = Field(default_factory=list)
    avg_confidence: float = 0.0
    trend: str = Field(default="stable", description="improving|stable|degrading")
