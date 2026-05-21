"""Heal schemas."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FailureCategory(str, Enum):
    LOCATOR_CHANGED = "locator_changed"
    TIMING_ISSUE = "timing_issue"
    DATA_DEPENDENCY = "data_dependency"
    ENV_ISSUE = "env_issue"
    REAL_BUG = "real_bug"
    FLAKY = "flaky"
    TEST_BUG = "test_bug"
    UNKNOWN = "unknown"


class FixHypothesis(BaseModel):
    model_config = ConfigDict(extra="allow")

    strategy: str
    new_selector: str
    reasoning: str = ""
    confidence: float = Field(0.0, ge=0.0, le=1.0)

    verified: bool = False
    pass_count: int = 0
    total_runs: int = 0
    verification_duration_ms: int = 0
    final_score: float = 0.0


class HealingAttempt(BaseModel):
    model_config = ConfigDict(extra="allow")

    test_id: str
    failure_category: FailureCategory = FailureCategory.UNKNOWN
    broken_selector: str = ""
    hypotheses: list[FixHypothesis] = Field(default_factory=list)
    winner_index: int | None = None

    pr_url: str | None = None
    branch: str | None = None
    auto_merged: bool = False
    hitl_required: bool = False
    hitl_reason: str | None = None

    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None


class HealingResult(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    attempts: list[HealingAttempt] = Field(default_factory=list)
    successful_fixes: int = 0
    pr_urls: list[str] = Field(default_factory=list)
    hitl_queue: list[str] = Field(default_factory=list)
    jira_bugs: list[str] = Field(default_factory=list)

    def success_rate(self) -> float:
        if not self.attempts:
            return 0.0
        return self.successful_fixes / len(self.attempts)

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "attempts": [a.model_dump(mode="json") for a in self.attempts],
            "successful_fixes": self.successful_fixes,
            "pr_urls": self.pr_urls,
            "hitl_queue": self.hitl_queue,
        }
