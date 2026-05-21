"""Code schemas — Coder çıktısı."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class CodeFile(BaseModel):
    model_config = ConfigDict(extra="allow")

    path: str
    content: str
    language: Literal[
        "typescript", "javascript", "python", "java", "yaml", "feature",
        "json", "markdown"
    ]
    purpose: Literal[
        "spec", "page_object", "step_definition", "feature",
        "fixture", "config", "helper"
    ] = "spec"

    def write_to_disk(self, base_dir: str | Path) -> Path:
        full = Path(base_dir) / self.path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(self.content, encoding="utf-8")
        return full


class GeneratedCode(BaseModel):
    model_config = ConfigDict(extra="allow", validate_assignment=True)

    generator_type: Literal[
        "e2e", "api", "performance", "security", "accessibility", "contract"
    ] = "e2e"
    files: list[CodeFile] = Field(default_factory=list)
    lint_clean: bool = False
    syntax_valid: bool = True

    def spec_files(self) -> list[CodeFile]:
        return [f for f in self.files if f.purpose == "spec"]

    def page_object_files(self) -> list[CodeFile]:
        return [f for f in self.files if f.purpose == "page_object"]

    def step_definition_files(self) -> list[CodeFile]:
        return [f for f in self.files if f.purpose == "step_definition"]

    def feature_files(self) -> list[CodeFile]:
        return [f for f in self.files if f.purpose == "feature"]

    def to_state_dict(self) -> dict[str, Any]:
        return {
            "spec_files": [f.path for f in self.spec_files()],
            "page_object_files": [f.path for f in self.page_object_files()],
            "step_definition_files": [f.path for f in self.step_definition_files()],
            "feature_files": [f.path for f in self.feature_files()],
            "generator_type": self.generator_type,
        }
