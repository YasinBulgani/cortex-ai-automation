"""
Prompt builder — rol kartı + state + önceki artifact'lerden LLM prompt üretir.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
ROLES_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "roles"
ITEMS_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "items"
TEMPLATES_DIR = REPO_ROOT / "docs" / "ai" / "pipeline" / "templates"
STATE_PATH = REPO_ROOT / "docs" / "ai" / "pipeline" / "state.json"
GROUNDING = REPO_ROOT / "docs" / "ai" / "GROUNDING.md"


# Rol slug → dosya adı mapping (roles/01-analyzer.md vs.)
ROLE_FILES = {
    "analyzer": "01-analyzer.md",
    "validator": "02-validator.md",
    "proposer": "03-proposer.md",
    "approver": "04-approver.md",
    "designer": "05-designer.md",
    "architect": "06-architect.md",
    "frontend": "07-frontend.md",
    "backend": "08-backend.md",
    "integrator": "09-integrator.md",
    "qa": "10-qa.md",
    "promoter": "11-promoter.md",
    "product_validator": "12-product-validator.md",
    "data_engineer": "13-data-engineer.md",
    "devops": "14-devops.md",
    "code_reviewer": "15-code-reviewer.md",
    "security_reviewer": "16-security-reviewer.md",
    "a11y_auditor": "17-a11y-auditor.md",
    "performance_tester": "18-performance-tester.md",
    "release_manager": "19-release-manager.md",
    "observer": "20-observer.md",
    "retrospective": "21-retrospective.md",
    "intake_triage": "22-intake-triage.md",
    "knowledge_curator": "23-knowledge-curator.md",
    "dependency_watchdog": "24-dependency-watchdog.md",
    "conflict_resolver": "25-conflict-resolver.md",
}

# Rolün çıktı dosyası (items/<ID>/ içinde)
ROLE_OUTPUT = {
    "analyzer": "gap-analysis.md",
    "proposer": "proposal.md",
    "designer": "design.md",
    "architect": "arch-ADR.md",
    "qa": "test-report.md",
    "security_reviewer": "security-review.md",
    "a11y_auditor": "a11y-report.md",
    "performance_tester": "perf-report.md",
    "observer": "observer-report.md",
    "retrospective": "retro.md",
}

# Hangi rollerden önce hangi artifact'ler okunmalı
ROLE_INPUTS = {
    "validator": ["gap-analysis.md"],
    "proposer": ["gap-analysis.md"],
    "approver": ["gap-analysis.md", "proposal.md"],
    "product_validator": ["gap-analysis.md", "proposal.md"],
    "designer": ["proposal.md"],
    "architect": ["proposal.md"],
    "frontend": ["design.md", "arch-ADR.md"],
    "backend": ["arch-ADR.md"],
    "data_engineer": ["arch-ADR.md"],
    "devops": ["arch-ADR.md"],
    "code_reviewer": ["arch-ADR.md", "design.md"],
    "integrator": ["arch-ADR.md"],
    "qa": ["arch-ADR.md", "design.md"],
    "security_reviewer": ["arch-ADR.md"],
    "a11y_auditor": ["design.md"],
    "performance_tester": ["arch-ADR.md"],
    "promoter": ["test-report.md", "security-review.md"],
    "release_manager": ["test-report.md", "arch-ADR.md"],
    "observer": ["arch-ADR.md"],
    "retrospective": ["*"],
}


@dataclass
class PromptBuilder:
    """Agent için system + user prompt'u inşa eder."""

    role: str
    item_id: str
    extra_context: Dict[str, Any] = field(default_factory=dict)

    def role_card(self) -> str:
        f = ROLE_FILES.get(self.role)
        if not f:
            return ""
        path = ROLES_DIR / f
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def grounding(self, max_chars: int = 3000) -> str:
        if not GROUNDING.exists():
            return ""
        text = GROUNDING.read_text(encoding="utf-8")
        if len(text) > max_chars:
            return text[:max_chars] + "\n... [grounding truncated]"
        return text

    def item_state(self) -> Dict[str, Any]:
        if not STATE_PATH.exists():
            return {}
        try:
            data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
            for item in data.get("items", []):
                if item.get("id") == self.item_id:
                    return item
        except Exception:
            return {}
        return {}

    def prior_artifacts(self) -> Dict[str, str]:
        """Rolden önce yazılmış artifact'leri oku."""
        out: Dict[str, str] = {}
        expected = ROLE_INPUTS.get(self.role, [])
        item_dir = ITEMS_DIR / self.item_id
        if not item_dir.exists():
            return out
        files_to_read: List[str] = []
        if expected == ["*"]:
            files_to_read = [p.name for p in item_dir.iterdir() if p.is_file() and p.suffix == ".md"]
        else:
            files_to_read = list(expected)
        for fname in files_to_read:
            f = item_dir / fname
            if f.exists():
                out[fname] = f.read_text(encoding="utf-8")
        return out

    def output_template(self) -> str:
        """Çıktı şablonu (varsa)."""
        tpl_map = {
            "analyzer": "gap-analysis.template.md",
            "proposer": "proposal.template.md",
            "designer": "design.template.md",
            "architect": "arch-ADR.template.md",
            "qa": "test-report.template.md",
            "security_reviewer": "security-review.template.md",
            "a11y_auditor": "security-review.template.md",  # benzer format
            "performance_tester": "security-review.template.md",
            "observer": "observer-report.template.md",
            "retrospective": "retrospective.template.md",
            "release_manager": "release-notes.template.md",
            "product_validator": "product-validation.template.md",
        }
        tpl = tpl_map.get(self.role)
        if not tpl:
            return ""
        p = TEMPLATES_DIR / tpl
        if p.exists():
            return p.read_text(encoding="utf-8")
        return ""

    def output_file(self) -> Optional[Path]:
        fname = ROLE_OUTPUT.get(self.role)
        if not fname:
            return None
        return ITEMS_DIR / self.item_id / fname

    # ── Actual prompt assembly ──────────────────────────────────────────────
    def build(self) -> List[Dict[str, str]]:
        """Returns messages array (system + user) for chat completion."""
        system = self._system_prompt()
        user = self._user_prompt()
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _system_prompt(self) -> str:
        role_card = self.role_card()
        grounding = self.grounding()
        lines = [
            f"You are a specialized AI agent for the `{self.role}` role in a 25-stage software delivery pipeline.",
            "You MUST follow the role card's Input→Work→Output contract strictly.",
            "You output professional, concise Turkish or English (whichever matches the repo context).",
            "Your output is a MARKDOWN artifact that will be committed to the repo.",
            "",
            "## YOUR ROLE CARD",
            "",
            role_card if role_card else "(role card missing — see docs/ai/pipeline/roles/)",
            "",
        ]
        if grounding:
            lines += [
                "## PROJECT GROUNDING",
                "",
                grounding,
                "",
            ]
        lines += [
            "## CRITICAL CONSTRAINTS",
            "- Produce ONLY the artifact content in markdown (no preamble, no commentary).",
            "- If the role card has an output template, follow it exactly.",
            "- Quote file paths with backticks.",
            f"- Add `[pipeline: {self.role} {self.item_id}]` as the last line.",
            "- If you cannot complete the task (missing info), output a markdown report starting with `# BLOCKED` and explain why.",
            "",
            "## DECISION ROLES (validator/approver/product_validator/code_reviewer/security_reviewer/a11y_auditor/performance_tester/observer)",
            "Your output MUST include a JSON block at the end (inside ```json ... ```) with fields:",
            '  { "decision": "approve"|"reject"|"revise", "confidence": 0.0-1.0, "reason": "<short>" }',
        ]
        return "\n".join(lines)

    def _user_prompt(self) -> str:
        state = self.item_state()
        priors = self.prior_artifacts()
        template = self.output_template()

        lines: List[str] = [
            f"Item ID: **{self.item_id}**",
            f"Stage: **{self.role}**",
            "",
        ]
        if state:
            lines += [
                "## ITEM CONTEXT",
                "```json",
                json.dumps({
                    "id": state.get("id"),
                    "type": state.get("type"),
                    "title": state.get("title"),
                    "priority": state.get("priority"),
                    "scope": state.get("scope"),
                    "current_stage": state.get("current_stage"),
                    "needs_human": state.get("needs_human"),
                    "feedback_loops": state.get("feedback_loops", []),
                }, indent=2),
                "```",
                "",
            ]

        if self.extra_context:
            lines += [
                "## EXTRA CONTEXT",
                "```json",
                json.dumps(self.extra_context, indent=2, default=str),
                "```",
                "",
            ]

        if priors:
            lines += ["## PRIOR ARTIFACTS", ""]
            for name, content in priors.items():
                # Truncate long artifacts
                if len(content) > 8000:
                    content = content[:8000] + "\n\n... [truncated]"
                lines += [f"### `{name}`", "", "```markdown", content, "```", ""]

        if template:
            lines += [
                "## OUTPUT TEMPLATE (follow this structure)",
                "",
                "```markdown",
                template[:5000],
                "```",
                "",
            ]

        output_file = self.output_file()
        if output_file:
            lines += [
                f"## OUTPUT TARGET",
                f"- Write the artifact to: `{output_file.relative_to(REPO_ROOT)}`",
                "",
            ]

        lines += [
            "## YOUR TASK NOW",
            f"Execute the `{self.role}` role for item `{self.item_id}` as specified in your role card.",
            "Produce the complete artifact in markdown format. Do NOT add explanations before or after.",
        ]
        return "\n".join(lines)


def build_agent_prompt(role: str, item_id: str, **extra) -> List[Dict[str, str]]:
    """Convenience function."""
    return PromptBuilder(role=role, item_id=item_id, extra_context=extra).build()
