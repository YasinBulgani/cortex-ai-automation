"""Run schemas — Runner çıktısı."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


class TestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    BROKEN = "broken"
    ERROR = "error"
    PENDING = "pending"
    TIMEOUT = "timeout"


class FailureContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    test_id: str
    test_name: str
    spec_file: str = ""
    failed_step: str | None = None

    status: TestStatus = TestStatus.FAILED
    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""

    current_url: str = ""
    screenshot_path: str = ""
    dom_snapshot_path: str = ""
    previous_dom_path: str | None = None

    last_actions: list[dict[str, Any]] = Field(default_factory=list)
    network_log: list[dict[str, Any]] = Field(default_factory=list)
    console_errors: list[str] = Field(default_factory=list)

    locators_used: list[str] = Field(default_factory=list)
    page_objects_used: list[str] = Field(default_factory=list)

    git_commit: str = ""
    failed_at: datetime = Field(default_factory=datetime.utcnow)


class RunResult(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    run_id: str = Field(default_factory=lambda: str(uuid4()))
    status: TestStatus = TestStatus.PENDING

    passed_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0
    flaky_count: int = 0
    broken_count: int = 0
    total_count: int = 0

    duration_seconds: float = 0.0
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None

    allure_report_path: str = ""
    junit_xml_path: str = ""
    trace_urls: list[str] = Field(default_factory=list)
    video_urls: list[str] = Field(default_factory=list)
    screenshot_urls: list[str] = Field(default_factory=list)

    failure_contexts: list[FailureContext] = Field(default_factory=list)

    environment: str = "sandbox"
    browser: str = "chromium"

    def success_rate(self) -> float:
        if self.total_count == 0:
            return 0.0
        return self.passed_count / self.total_count

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "allure_report_path": self.allure_report_path,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "skipped_count": self.skipped_count,
            "flaky_count": self.flaky_count,
            "duration_seconds": self.duration_seconds,
            "trace_urls": self.trace_urls,
            "failure_contexts": [fc.model_dump(mode="json") for fc in self.failure_contexts],
        }
