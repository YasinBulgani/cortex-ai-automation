"""Report schemas."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ReportResult(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    summary_tr: str = ""
    summary_en: str | None = None
    slack_message_ts: str | None = None
    slack_channel: str | None = None
    email_sent_to: list[str] = Field(default_factory=list)
    pdf_path: str | None = None
    html_path: str | None = None
    langfuse_trace_url: str | None = None

    def to_state_dict(self) -> dict:
        return self.model_dump(mode="json")
