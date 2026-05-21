"""Review schemas."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ReviewAction(str, Enum):
    AUTO_APPROVE = "auto_approve"
    APPROVE_WITH_COMMENTS = "approve_with_comments"
    REQUEST_CHANGES = "request_changes"
    REJECT = "reject"


class ReviewFinding(BaseModel):
    model_config = ConfigDict(extra="allow")
    severity: str
    category: str
    message: str
    file: str | None = None
    line: int | None = None


class ReviewResult(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    code_quality_score: float = Field(0.0, ge=0.0, le=1.0)
    test_coverage_estimate: float = Field(0.0, ge=0.0, le=1.0)
    edge_cases_missed: list[str] = Field(default_factory=list)
    security_flags: list[ReviewFinding] = Field(default_factory=list)
    lint_errors: list[ReviewFinding] = Field(default_factory=list)
    findings: list[ReviewFinding] = Field(default_factory=list)
    recommended_action: ReviewAction = ReviewAction.APPROVE_WITH_COMMENTS
    reviewer_notes: str = ""

    def to_state_dict(self) -> dict:
        return {
            "code_quality_score": self.code_quality_score,
            "test_coverage_estimate": self.test_coverage_estimate,
            "edge_cases_missed": self.edge_cases_missed,
            "security_flags": [f.model_dump() for f in self.security_flags],
            "lint_errors": [f.model_dump() for f in self.lint_errors],
            "recommended_action": self.recommended_action.value,
            "reviewer_notes": self.reviewer_notes,
        }
