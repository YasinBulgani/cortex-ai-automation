"""Gherkin scenario schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class GherkinStep(BaseModel):
    model_config = ConfigDict(extra="allow")
    keyword: Literal["Given", "When", "Then", "And", "But"]
    text: str
    dsl_ref: str | None = None
    data_table: list[list[str]] | None = None
    doc_string: str | None = None


class GherkinScenario(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    tags: list[str] = Field(default_factory=list)
    steps: list[GherkinStep] = Field(default_factory=list)
    examples: list[dict[str, Any]] | None = None
    is_outline: bool = False


class GherkinFeature(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    name: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    background: list[GherkinStep] | None = None
    scenarios: list[GherkinScenario] = Field(default_factory=list)
    language: str = "tr"

    def to_gherkin_text(self) -> str:
        lines: list[str] = []
        if self.language and self.language != "en":
            lines.append(f"# language: {self.language}")
        for t in self.tags:
            lines.append(f"@{t}")
        feature_kw = "Özellik" if self.language == "tr" else "Feature"
        lines.append(f"{feature_kw}: {self.name}")
        if self.description:
            for ln in self.description.splitlines():
                lines.append(f"  {ln}")
            lines.append("")

        if self.background:
            bg_kw = "Artalan" if self.language == "tr" else "Background"
            lines.append(f"  {bg_kw}:")
            for step in self.background:
                lines.append(f"    {step.keyword} {step.text}")
            lines.append("")

        for sc in self.scenarios:
            for t in sc.tags:
                lines.append(f"  @{t}")
            sc_kw = (
                ("Senaryo Taslağı" if sc.is_outline else "Senaryo")
                if self.language == "tr"
                else ("Scenario Outline" if sc.is_outline else "Scenario")
            )
            lines.append(f"  {sc_kw}: {sc.name}")
            for step in sc.steps:
                lines.append(f"    {step.keyword} {step.text}")
                if step.data_table:
                    for row in step.data_table:
                        lines.append(f"      | {' | '.join(row)} |")
                if step.doc_string:
                    lines.append('      """')
                    for ln in step.doc_string.splitlines():
                        lines.append(f"      {ln}")
                    lines.append('      """')
            if sc.examples:
                ex_kw = "Örnekler" if self.language == "tr" else "Examples"
                lines.append(f"    {ex_kw}:")
                if sc.examples:
                    cols = list(sc.examples[0].keys())
                    lines.append(f"      | {' | '.join(cols)} |")
                    for row in sc.examples:
                        vals = [str(row.get(c, "")) for c in cols]
                        lines.append(f"      | {' | '.join(vals)} |")
            lines.append("")

        return "\n".join(lines).rstrip() + "\n"


class ScenarioSpec(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    features: list[GherkinFeature] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    grounded_steps_count: int = 0
    novel_steps_count: int = 0

    def total_scenarios(self) -> int:
        return sum(len(f.scenarios) for f in self.features)
