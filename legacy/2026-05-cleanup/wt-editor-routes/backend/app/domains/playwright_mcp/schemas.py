"""Playwright MCP — Pydantic semalari."""
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class BrowserSessionCreate(BaseModel):
    """Yeni browser oturumu olusturma istegi."""

    headless: bool = Field(default=True, description="Headless mod")
    viewport_width: int = Field(default=1280, ge=320, le=3840)
    viewport_height: int = Field(default=720, ge=240, le=2160)
    locale: str = Field(default="tr-TR")
    timezone: str = Field(default="Europe/Istanbul")


class BrowserSessionInfo(BaseModel):
    session_id: str
    status: str  # "active", "idle", "closed"
    current_url: Optional[str] = None
    created_at: str
    page_title: Optional[str] = None


class NavigateRequest(BaseModel):
    url: str
    wait_until: str = Field(
        default="domcontentloaded",
        description="load|domcontentloaded|networkidle",
    )
    timeout_ms: int = Field(default=30000, ge=1000, le=120000)


class NavigateResponse(BaseModel):
    url: str
    title: str
    status_code: Optional[int] = None
    load_time_ms: int


class SelectorValidateRequest(BaseModel):
    selectors: List[str] = Field(description="Dogrulanacak selector'lar")
    timeout_ms: int = Field(default=5000, ge=500, le=30000)


class SelectorResult(BaseModel):
    selector: str
    found: bool
    count: int = 0
    visible: bool = False
    tag_name: Optional[str] = None
    attributes: Dict[str, str] = Field(default_factory=dict)
    bounding_box: Optional[Dict[str, float]] = None
    stability_score: int = Field(
        default=0, ge=0, le=5, description="0-5 stabilite skoru"
    )
    suggested_alternatives: List[str] = Field(default_factory=list)


class SelectorValidateResponse(BaseModel):
    results: List[SelectorResult]
    page_url: str
    validated_at: str


class DOMSnapshotRequest(BaseModel):
    selector: Optional[str] = Field(
        default=None, description="Belirli element icin CSS selector"
    )
    max_depth: int = Field(default=5, ge=1, le=15)
    include_styles: bool = False
    include_hidden: bool = False


class DOMNode(BaseModel):
    tag: str
    attributes: Dict[str, str] = Field(default_factory=dict)
    text: Optional[str] = None
    children: List["DOMNode"] = Field(default_factory=list)
    bounding_box: Optional[Dict[str, float]] = None


DOMNode.model_rebuild()


class DOMSnapshotResponse(BaseModel):
    url: str
    title: str
    root: Optional[DOMNode] = None
    element_count: int = 0
    snapshot_at: str


class ScreenshotRequest(BaseModel):
    selector: Optional[str] = None
    full_page: bool = False
    format: str = Field(default="png", description="png|jpeg")
    quality: int = Field(default=80, ge=10, le=100)


class ScreenshotResponse(BaseModel):
    image_base64: str
    format: str
    width: int
    height: int
    url: str


class ActionRequest(BaseModel):
    """Genel browser aksiyonu."""

    action: str = Field(
        description="click|fill|select|hover|press|scroll|wait"
    )
    selector: str
    value: Optional[str] = None
    timeout_ms: int = Field(default=5000, ge=500, le=30000)


class ActionResponse(BaseModel):
    action: str
    selector: str
    success: bool
    error: Optional[str] = None
    duration_ms: int
    screenshot_after: Optional[str] = None  # base64 if requested


class SelectorSuggestRequest(BaseModel):
    """Hedef element icin AI destekli selector onerisi."""

    target_description: str = Field(
        description="Hedef elementin aciklamasi (or. 'Login butonu')"
    )
    dom_context: Optional[str] = None
    page_url: Optional[str] = None


class SelectorSuggestResponse(BaseModel):
    suggestions: List[SelectorResult]
    ai_analysis: Optional[str] = None


class HealVerifyRequest(BaseModel):
    """Healing sonrasi dogrulama."""

    original_selector: str
    healed_selector: str
    expected_tag: Optional[str] = None
    expected_text: Optional[str] = None


class HealVerifyResponse(BaseModel):
    original_found: bool
    healed_found: bool
    healed_matches_expected: bool
    confidence: float = 0.0
    recommendation: str = ""
