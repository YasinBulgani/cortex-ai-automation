"""Otomasyon Süiti için Pydantic şemaları."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


Framework = Literal["playwright", "selenium", "cypress"]
RunStatus = Literal["queued", "running", "passed", "failed", "error", "cancelled"]


# ── Generate ────────────────────────────────────────────────────────────────

class SuiteGenerateRequest(BaseModel):
    """Manuel test → BDD + otomasyon kodu üret."""

    manual_test_id: int = Field(..., description="engine.manual_tests.id")
    target_url: Optional[str] = Field(
        default=None,
        description="Locator keşfi yapılacaksa hedef URL — boş bırakılabilir",
    )
    framework: Framework = "playwright"
    auto_run: bool = Field(
        default=False,
        description="Kod üretildikten sonra otomatik koşum tetiklensin mi?",
    )


class SuiteGenerateResponse(BaseModel):
    ok: bool
    test_title: str
    steps_count: int
    gherkin: str
    framework: Framework
    generated_code: Optional[str] = None
    feature_path: Optional[str] = None
    locators: Optional[Dict[str, Any]] = None
    model: Optional[str] = None
    # DSL zenginleştirme
    dsl_matched_actions: List[str] = Field(default_factory=list)
    dsl_unknown_steps: List[str] = Field(default_factory=list)
    # Auto-run sonucu
    run_id: Optional[str] = None


# ── Run ─────────────────────────────────────────────────────────────────────

class SuiteRunRequest(BaseModel):
    feature_path: Optional[str] = Field(
        default=None,
        description="engine'deki feature dosyasının göreli yolu",
    )
    suite_id: Optional[str] = Field(
        default=None,
        description="(rezerve) DB'de kayıtlı bir suite'in ID'si",
    )
    framework: Framework = "playwright"
    headless: bool = True
    tags: List[str] = Field(default_factory=list)


class SuiteRunResponse(BaseModel):
    run_id: str
    status: RunStatus
    message: str


# ── Run Status ──────────────────────────────────────────────────────────────

class SuiteRunStatus(BaseModel):
    run_id: str
    status: RunStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    feature_path: Optional[str] = None
    framework: Optional[Framework] = None
    passed: Optional[int] = None
    failed: Optional[int] = None
    error: Optional[str] = None
    report_url: Optional[str] = None
    logs_tail: List[str] = Field(default_factory=list)


# ── Catalog Suggest ─────────────────────────────────────────────────────────

class SuiteCatalogSuggestRequest(BaseModel):
    description: str = Field(..., min_length=2, max_length=2000)
    limit: int = Field(default=10, ge=1, le=50)


class SuiteCatalogSuggestItem(BaseModel):
    action_id: str
    category: Optional[str] = None
    matched_language: str
    matched_alias: str
    description: Optional[str] = None


class SuiteCatalogSuggestResponse(BaseModel):
    query: str
    total: int
    items: List[SuiteCatalogSuggestItem]


# ── Health ──────────────────────────────────────────────────────────────────

class SuiteHealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    backend: Literal["ok"] = "ok"
    engine: Dict[str, Any]
    dsl: Dict[str, Any]
