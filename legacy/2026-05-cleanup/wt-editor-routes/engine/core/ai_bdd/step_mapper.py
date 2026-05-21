"""
StepDefinitionMapper — Gherkin adımlarını mevcut step definition'larla eşleştirir.

Yeni adımlar için step definition kodu önerir.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class StepMapping:
    gherkin_step: str
    mapped_definition: str | None
    is_new: bool
    suggested_code: str = ""


class StepDefinitionMapper:
    """Gherkin step'lerini mevcut veya yeni step definition'larla eşle."""

    def __init__(self, steps_dir: str | Path | None = None):
        self.steps_dir = Path(steps_dir) if steps_dir else settings.BASE_DIR / "steps"
        self._existing_steps: list[str] = []
        self._load_existing()

    def _load_existing(self) -> None:
        """Mevcut step definition dosyalarından pattern'ları yükle."""
        if not self.steps_dir.exists():
            return
        for py_file in self.steps_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                patterns = re.findall(
                    r'@(?:given|when|then)\(["\'](.+?)["\']\)', content
                )
                self._existing_steps.extend(patterns)
            except OSError:
                continue
        logger.info("Loaded %d existing step patterns", len(self._existing_steps))

    def map_feature(self, feature_content: str) -> list[StepMapping]:
        """Feature dosyasındaki tüm adımları eşleştir."""
        steps = self._extract_steps(feature_content)
        mappings = []

        for step in steps:
            matched = self._find_match(step)
            if matched:
                mappings.append(StepMapping(
                    gherkin_step=step,
                    mapped_definition=matched,
                    is_new=False,
                ))
            else:
                mappings.append(StepMapping(
                    gherkin_step=step,
                    mapped_definition=None,
                    is_new=True,
                    suggested_code=self._suggest_step_code(step),
                ))
        return mappings

    def get_unmapped_steps(self, feature_content: str) -> list[str]:
        """Eşleşmeyen (yeni) step'leri döndür."""
        return [m.gherkin_step for m in self.map_feature(feature_content) if m.is_new]

    def _extract_steps(self, feature: str) -> list[str]:
        """Gherkin feature'dan step satırlarını çıkar."""
        steps = []
        for line in feature.split("\n"):
            stripped = line.strip()
            if re.match(r"^(Given|When|Then|And|But)\s", stripped):
                steps.append(stripped)
        return steps

    def _find_match(self, step: str) -> str | None:
        """Step'i mevcut pattern'larla eşleştir."""
        clean = re.sub(r"^(Given|When|Then|And|But)\s+", "", step)
        for pattern in self._existing_steps:
            regex_pat = re.sub(r"\{[^}]+\}", ".+", pattern)
            regex_pat = re.sub(r"<[^>]+>", ".+", regex_pat)
            if re.match(regex_pat, clean, re.IGNORECASE):
                return pattern
        return None

    def _suggest_step_code(self, step: str) -> str:
        """Yeni step için Python kodu öner."""
        keyword = step.split()[0].lower()
        clean = re.sub(r"^(Given|When|Then|And|But)\s+", "", step)
        param_names = re.findall(r'"([^"]+)"', clean)
        pattern = re.sub(r'"[^"]*"', '"{value}"', clean)

        params = ", ".join(f'value{i+1}' for i in range(len(param_names)))
        func_name = re.sub(r"[^a-z0-9_]", "_", clean.lower())[:60]

        decorator = {"given": "given", "when": "when", "then": "then"}.get(keyword, "when")

        return f'''@{decorator}('{pattern}')
def {func_name}({params}):
    """Auto-generated step definition."""
    raise NotImplementedError("Step implementation needed")
'''
