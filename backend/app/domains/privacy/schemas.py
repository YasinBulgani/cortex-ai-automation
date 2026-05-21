"""Privacy/DSAR API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DSARDeleteRequest(BaseModel):
    dry_run: bool = True
    purge_artifact_files: bool = False
    reason: str = "dsar_request"


class DSARDeleteResponse(BaseModel):
    user_id: str
    dry_run: bool
    deleted: dict[str, int] = Field(default_factory=dict)
    artifact_files_deleted: list[str] = Field(default_factory=list)
    artifact_files_skipped: list[str] = Field(default_factory=list)


class DSARExportResponse(BaseModel):
    user_id: str
    generated_at: datetime
    counts: dict[str, int] = Field(default_factory=dict)
    workflows: list[dict[str, Any]] = Field(default_factory=list)
    llm_traces: list[dict[str, Any]] = Field(default_factory=list)
