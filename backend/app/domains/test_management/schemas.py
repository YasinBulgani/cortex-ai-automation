"""Pydantic schemas for Neurex Management."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class ManagementProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    key: str = Field(..., min_length=1, max_length=32)
    description: str = ""
    tspm_project_id: Optional[str] = None


class ManagementProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    tspm_project_id: Optional[str] = None
    name: str
    key: str
    description: Optional[str] = ""
    status: str
    created_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TestSuiteCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str = ""
    order_index: int = 0


class TestSuiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    description: Optional[str] = ""
    order_index: int
    status: str
    created_at: datetime


class TestFolderCreate(BaseModel):
    suite_id: str
    name: str = Field(..., min_length=1, max_length=200)
    path: str = Field(..., min_length=1, max_length=1000)
    parent_id: Optional[str] = None
    order_index: int = 0


class TestFolderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    suite_id: str
    parent_id: Optional[str] = None
    name: str
    path: str
    order_index: int
    created_at: datetime


class TestCaseStepIn(BaseModel):
    step_no: int = Field(..., ge=1)
    action: str = Field(..., min_length=1)
    expected_result: str = Field(..., min_length=1)
    test_data: dict[str, Any] = Field(default_factory=dict)
    notes: Optional[str] = None
    is_required: bool = True


class TestCaseStepOut(TestCaseStepIn):
    model_config = ConfigDict(from_attributes=True)

    id: str
    case_id: str


class TestCaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    case_key: Optional[str] = None
    objective: str = ""
    preconditions: str = ""
    test_data: dict[str, Any] = Field(default_factory=dict)
    priority: str = "medium"
    severity: str = "major"
    type: str = "functional"
    automation_status: str = "manual"
    status: str = "draft"
    source_type: str = "manual"
    source_ref: Optional[str] = None
    owner_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    steps: list[TestCaseStepIn] = Field(default_factory=list)


class TestCaseUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=500)
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    objective: Optional[str] = None
    preconditions: Optional[str] = None
    test_data: Optional[dict[str, Any]] = None
    priority: Optional[str] = None
    severity: Optional[str] = None
    type: Optional[str] = None
    automation_status: Optional[str] = None
    status: Optional[str] = None
    owner_id: Optional[str] = None
    tags: Optional[list[str]] = None
    custom_fields: Optional[dict[str, Any]] = None
    steps: Optional[list[TestCaseStepIn]] = None
    change_summary: str = "Manual update"


class TestCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    suite_id: Optional[str] = None
    folder_id: Optional[str] = None
    case_key: str
    title: str
    objective: Optional[str] = ""
    preconditions: Optional[str] = ""
    test_data: dict[str, Any]
    priority: str
    severity: str
    type: str
    automation_status: str
    status: str
    source_type: str
    source_ref: Optional[str] = None
    owner_id: Optional[str] = None
    tags: list[str]
    custom_fields: dict[str, Any]
    current_version: int
    last_run_status: Optional[str] = None
    last_run_at: Optional[datetime] = None
    archived: bool
    created_at: datetime
    updated_at: datetime
    steps: list[TestCaseStepOut] = Field(default_factory=list)


class RepositoryOut(BaseModel):
    suites: list[TestSuiteOut]
    folders: list[TestFolderOut]
    cases: list[TestCaseOut]


class TestPlanCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    plan_type: str = "regression"
    release_name: Optional[str] = None
    scope_summary: Optional[str] = None


class TestPlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    name: str
    plan_type: str
    release_name: Optional[str] = None
    status: str
    scope_summary: Optional[str] = None
    created_by: Optional[str] = None
    created_at: datetime


class TestCycleCreate(BaseModel):
    plan_id: str
    name: str = Field(..., min_length=1, max_length=200)
    environment: Optional[str] = None
    build_version: Optional[str] = None


class TestRunCreate(BaseModel):
    cycle_id: str
    name: str = Field(..., min_length=1, max_length=300)
    case_ids: list[str] = Field(default_factory=list)
    assigned_to: Optional[str] = None


class TestRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    cycle_id: str
    name: str
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class StepResultUpdate(BaseModel):
    status: str
    actual_result: Optional[str] = None
    comment: Optional[str] = None


class RunCaseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    case_id: str
    case_version_no: int
    assigned_to: Optional[str] = None
    status: str
    actual_result: Optional[str] = None
    execution_notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None


class ExecutionSummaryOut(BaseModel):
    total: int
    not_run: int
    passed: int
    failed: int
    blocked: int
    skipped: int
    retest: int
    progress_pct: float
    pass_rate_pct: float


class RequirementLinkCreate(BaseModel):
    case_id: str
    external_source: str = "internal"
    external_key: str = Field(..., min_length=1, max_length=200)
    title_snapshot: str = Field(..., min_length=1, max_length=500)
    url: Optional[str] = None
    coverage_status: str = "covered"


class RequirementLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    case_id: str
    external_source: str
    external_key: str
    title_snapshot: str
    url: Optional[str] = None
    source_updated_at: Optional[datetime] = None
    coverage_status: str


class DefectLinkCreate(BaseModel):
    run_case_id: str
    step_result_id: Optional[str] = None
    external_source: str = "internal"
    external_key: str = Field(..., min_length=1, max_length=200)
    title: str = Field(..., min_length=1, max_length=500)
    status: str = "open"
    url: Optional[str] = None


class DefectLinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_case_id: str
    step_result_id: Optional[str] = None
    external_source: str
    external_key: str
    title: str
    status: str
    url: Optional[str] = None
    created_at: datetime


class TestImportJobCreate(BaseModel):
    filename: str = Field(..., min_length=1, max_length=500)
    mapping: dict[str, Any] = Field(default_factory=dict)
    rows: list[dict[str, Any]] = Field(default_factory=list)


class TestImportJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    filename: str
    status: str
    mapping: dict[str, Any]
    totals: dict[str, Any]
    created_by: Optional[str] = None
    created_at: datetime
