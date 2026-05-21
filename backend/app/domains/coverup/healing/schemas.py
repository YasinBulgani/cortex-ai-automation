"""Self-healing veri tipleri.

Felsefe:
    * ``FailureEvent`` tamamen serializable — webhook'tan, CI annotation'dan,
      Playwright MCP'den, hatta manual Postman çağrısından aynı şekille gelir.
    * ``HealingProposal`` LLM'in önerdiği bir aday. Bir run'da 1+ olabilir;
      en yüksek confidence olanı uygulanır.
    * ``HealingRun`` uçtan uca kaydı: hangi failure, hangi öneriler, hangisi
      seçildi, PR URL'si. Audit için eksiksiz tutuluyor (E3.3'e hazır).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


Framework = Literal["playwright", "cypress", "selenium", "other"]
LocatorKind = Literal["css", "xpath", "text", "role", "test-id", "other"]


class FailureEvent(BaseModel):
    """Bir test koşumundan gelen kırılma sinyali.

    Engine/CI/MCP gönderen kim olursa olsun bu yapıya dönüştürür. Çok sıkı
    validasyon yok çünkü kaynak çeşitliliği — eksik alanlar pipeline'ı
    kırmadan healer tarafından "yetersiz bağlam" ile reddedilir.
    """

    # ── Kimlik ────────────────────────────────────────────────────────────
    run_id: str = Field(min_length=1, description="Test koşum kimliği (GUID)")
    project_id: Optional[str] = None
    tenant_id: Optional[str] = Field(
        default=None,
        description="Budget & feature-flag scope; user.id proxy'si olabilir",
    )
    framework: Framework = "playwright"

    # ── Kırık yer ─────────────────────────────────────────────────────────
    test_file_path: str = Field(
        min_length=1,
        description="Repo köküne göre relative path, ör. 'tests/login.spec.ts'",
    )
    test_name: Optional[str] = None
    line_number: Optional[int] = Field(default=None, ge=1)
    locator: str = Field(
        min_length=1, description="Kırık selector (CSS, XPath, text=, vb.)"
    )
    locator_kind: LocatorKind = "css"

    # ── Bağlam ─────────────────────────────────────────────────────────────
    error_message: str = Field(default="", description="Test runner hata çıktısı")
    # Playwright MCP'nin aria snapshot'ı — HTML'den daha küçük ve anlamlı
    dom_snapshot: str = Field(default="", description="ARIA / DOM snapshot")
    # Hedef URL — snapshot toplama veya doğrulama için
    page_url: Optional[str] = None
    # Screenshot base64 yerine path referansı — DB sişmeyi önler
    screenshot_ref: Optional[str] = None

    # ── Meta ──────────────────────────────────────────────────────────────
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = Field(
        default="engine", description="engine | ci | mcp | manual"
    )

    @field_validator("test_file_path")
    @classmethod
    def _no_path_traversal(cls, v: str) -> str:
        """Güvenlik: relative path olmalı, '..'  ve mutlak path reddedilir.

        Patch applier sadece repo içinde yazacak; burada ek sigorta.
        """
        v = v.strip()
        if not v:
            raise ValueError("test_file_path boş olamaz")
        if v.startswith("/"):
            raise ValueError("Mutlak yol kabul edilmez: test_file_path relative olmalı")
        if ".." in v.split("/"):
            raise ValueError("test_file_path içinde '..' bileşeni olamaz")
        return v


class HealingProposal(BaseModel):
    """Healer'ın önerdiği bir aday selector.

    ``confidence`` 0..1. Uygulanmadan önce ``orchestrator`` en yüksek
    confidence'lı öneriyi seçer. ``confidence < threshold`` ise PR draft
    olarak açılır (plan §10 R2).
    """

    new_locator: str = Field(min_length=1)
    new_locator_kind: LocatorKind = "css"
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str = ""

    @field_validator("new_locator")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = (v or "").strip()
        if not v:
            raise ValueError("new_locator boş olamaz")
        return v


class HealingDecision(BaseModel):
    """Bir öneri kümesinden orchestrator'un yaptığı seçim."""

    selected: HealingProposal
    alternatives: List[HealingProposal] = Field(default_factory=list)
    strategy: str = "highest_confidence"

    def best_confidence(self) -> float:
        return self.selected.confidence


class HealingRun(BaseModel):
    """Uçtan uca kayıt — audit + dashboard için.

    ``pr_url`` proposal applied + commit pushed + PR opened sonrası dolar.
    Başarısız fazlar ``status`` ile işaretlenir.
    """

    id: str
    event: FailureEvent
    proposals: List[HealingProposal] = Field(default_factory=list)
    decision: Optional[HealingDecision] = None
    branch_name: Optional[str] = None
    pr_url: Optional[str] = None
    pr_number: Optional[int] = None
    draft: bool = False
    status: Literal[
        "queued",
        "no_proposal",
        "low_confidence_skipped",
        "patch_failed",
        "pr_failed",
        "succeeded",
        "disabled",
    ] = "queued"
    error_message: Optional[str] = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: Optional[datetime] = None

    def mark_done(self, status: str, *, error: Optional[str] = None) -> None:
        self.status = status  # type: ignore[assignment]
        self.error_message = error
        self.finished_at = datetime.now(timezone.utc)
