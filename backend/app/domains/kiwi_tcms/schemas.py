"""Pydantic request/response models for the Kiwi TCMS integration API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class KiwiConnectionIn(BaseModel):
    base_url: str = Field(..., min_length=1, max_length=500)
    username: str = Field(..., min_length=1, max_length=200)
    # Optional on update: omit/blank keeps the stored secret unchanged.
    secret: Optional[str] = Field(default=None, max_length=1024)
    kiwi_product_id: Optional[int] = None
    verify_ssl: bool = True


class KiwiConnectionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    base_url: str
    username: str
    has_secret: bool
    kiwi_product_id: Optional[int] = None
    verify_ssl: bool
    status: str
    last_error: Optional[str] = None
    last_tested_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class KiwiProductOut(BaseModel):
    id: int
    name: str


class KiwiTestConnectionResult(BaseModel):
    ok: bool
    product_count: int = 0
    error: Optional[str] = None
    products: list[KiwiProductOut] = Field(default_factory=list)


class KiwiPreviewOut(BaseModel):
    ok: bool
    error: Optional[str] = None
    counts: dict[str, int] = Field(default_factory=dict)  # suites/cases/plans/runs/executions


class KiwiSyncStartIn(BaseModel):
    dry_run: bool = False


class KiwiSyncJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    connection_id: str
    project_id: str
    mode: str
    status: str
    dry_run: bool
    totals: dict[str, Any]
    error: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
