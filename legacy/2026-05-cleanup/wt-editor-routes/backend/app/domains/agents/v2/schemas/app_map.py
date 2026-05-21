"""AppMap — Explorer çıktısı."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FormField(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str | None = None
    label: str | None = None
    type: str = "text"
    required: bool = False
    placeholder: str | None = None
    options: list[str] = Field(default_factory=list)
    validation: dict[str, Any] = Field(default_factory=dict)


class FormDescriptor(BaseModel):
    model_config = ConfigDict(extra="allow")
    page_url: str
    form_id: str | None = None
    form_name: str | None = None
    fields: list[FormField] = Field(default_factory=list)
    submit_button: str | None = None
    action: str | None = None
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"] = "POST"


class ApiObservation(BaseModel):
    model_config = ConfigDict(extra="allow")
    method: str
    url: str
    status_code: int | None = None
    request_content_type: str | None = None
    response_content_type: str | None = None
    request_body_schema: dict[str, Any] | None = None
    response_body_schema: dict[str, Any] | None = None
    observed_count: int = 1


class PageNode(BaseModel):
    model_config = ConfigDict(extra="allow")
    url: str
    title: str = ""
    screenshot_path: str = ""
    dom_hash: str = ""
    aria_summary: str = ""
    discovered_at: datetime = Field(default_factory=datetime.utcnow)
    depth: int = 0
    requires_auth: bool = False
    interactive_element_count: int = 0
    form_count: int = 0
    link_count: int = 0


class AppMap(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    root_url: str
    pages: list[PageNode] = Field(default_factory=list)
    navigation_graph: dict[str, list[str]] = Field(default_factory=dict)
    forms: list[FormDescriptor] = Field(default_factory=list)
    apis_observed: list[ApiObservation] = Field(default_factory=list)

    auth_required: bool = False
    explored_at: datetime = Field(default_factory=datetime.utcnow)
    explorer_duration_ms: int = 0
    crawl_depth: int = 2

    def page_count(self) -> int:
        return len(self.pages)

    def form_count(self) -> int:
        return len(self.forms)

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "pages": [p.model_dump(mode="json") for p in self.pages],
            "navigation_graph": self.navigation_graph,
            "forms": [f.model_dump(mode="json") for f in self.forms],
            "apis_observed": [a.model_dump(mode="json") for a in self.apis_observed],
        }
