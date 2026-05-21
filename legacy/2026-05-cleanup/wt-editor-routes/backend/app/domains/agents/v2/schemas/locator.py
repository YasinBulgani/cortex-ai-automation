"""Locator schemas — Locator Agent çıktısı."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LocatorStrategy(str, Enum):
    TESTID = "testid"
    ROLE_NAME = "role_name"
    TEXT = "text"
    CSS_SEMANTIC = "css_semantic"
    XPATH_AI = "xpath_ai"


class ElementCard(BaseModel):
    model_config = ConfigDict(extra="allow")

    idx: int
    tag: str
    visible_text: str = ""
    role: str = ""
    aria_label: str | None = None
    placeholder: str | None = None
    title: str | None = None
    testid: str | None = None
    element_id: str | None = None
    class_list: list[str] = Field(default_factory=list)
    href: str | None = None
    type: str | None = None
    name: str | None = None
    value: str | None = None
    required: bool = False
    disabled: bool = False
    bbox: tuple[float, float, float, float] | None = None
    parent_context: str | None = None
    xpath_raw: str = ""
    fingerprint: str = ""

    def element_description(self) -> str:
        parts: list[str] = []
        if self.visible_text:
            parts.append(f"'{self.visible_text[:40]}'")
        if self.role and self.role != self.tag:
            parts.append(f"role={self.role}")
        if self.testid:
            parts.append(f"testid={self.testid}")
        parts.append(f"tag={self.tag}")
        if self.parent_context:
            parts.append(f"parent={self.parent_context}")
        return " ".join(parts)


class LocatorCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    strategy: LocatorStrategy
    selector: str
    playwright_expr: str = ""
    semantic_strength: float = Field(..., ge=0.0, le=1.0)

    count: int = -1
    is_visible: bool | None = None
    is_enabled: bool | None = None

    stability_score: float = Field(0.0, ge=0.0, le=1.0)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    verified_at: datetime | None = None


class LocatorSuggestion(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    element_id: str
    element_description: str

    primary_strategy: LocatorStrategy
    primary_selector: str
    primary_playwright_expr: str = ""

    fallbacks: list[LocatorCandidate] = Field(default_factory=list)
    stability_score: float = Field(0.0, ge=0.0, le=1.0)

    verified_on_url: str = ""
    verified_at: datetime = Field(default_factory=datetime.utcnow)
    version: int = 1

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "element_description": self.element_description,
            "primary_strategy": self.primary_strategy.value,
            "primary_selector": self.primary_selector,
            "primary_playwright_expr": self.primary_playwright_expr,
            "fallbacks": [
                {
                    "strategy": f.strategy.value,
                    "selector": f.selector,
                    "score": f.stability_score,
                }
                for f in self.fallbacks
            ],
            "stability_score": self.stability_score,
            "verified_on_url": self.verified_on_url,
            "verified_at": self.verified_at.isoformat(),
        }
