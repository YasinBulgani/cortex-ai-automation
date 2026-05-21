"""
Doğal dil gereksinimlerden Gherkin BDD senaryoları üreten servis.

Mevcut step definition kütüphanesini tarar ve step reuse'u maksimize eder.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .llm_gateway import LLMGateway

_ENGINE_ROOT = Path(__file__).resolve().parent.parent

BDD_SYSTEM_PROMPT = """\
Sen bankacılık test senaryoları için BDD Gherkin feature dosyaları üreten bir uzmansın.

Kurallar:
1. Gherkin formatı: Feature / Scenario / Given / When / Then
2. Türkçe senaryo başlıkları kullan
3. Her senaryo tek bir iş akışını test etsin
4. Edge case ve negatif senaryolar ekle
5. data-testid convention'ına uygun locator referansları kullan
   (pattern: {screen}-{element-type}-{identifier})
6. Step'ler mümkün olduğunca mevcut step kütüphanesinden eşleştirilsin
7. Bir feature'da max 10 senaryo, bir senaryoda max 10 step
8. Her senaryo en az 1 Then (assertion) içermelidir
"""


@dataclass
class BDDOutput:
    feature_content: str
    step_definitions: str
    matched_existing_steps: list[str] = field(default_factory=list)
    new_steps_needed: list[str] = field(default_factory=list)


class BDDGenerator:
    """Doğal dil → Gherkin feature + step definitions."""

    def __init__(self, gateway: LLMGateway, model: str | None = None):
        self.gateway = gateway
        self.model = model or "gpt-4o"
        self.existing_steps = self._load_existing_steps()

    def generate(self, requirement: str) -> BDDOutput:
        steps_ctx = "\n".join(f"  - {s}" for s in self.existing_steps) if self.existing_steps else "  (henüz step tanımlı değil)"

        messages = [
            {"role": "system", "content": BDD_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Mevcut step kütüphanesi:\n{steps_ctx}\n\n"
                    f"Gereksinim: {requirement}\n\n"
                    "İki bölüm üret:\n"
                    "1. FEATURE: Gherkin feature dosyası\n"
                    "2. STEPS: Eksik step definition'lar (Python pytest-bdd formatında)"
                ),
            },
        ]

        resp = self.gateway.complete(messages, model=self.model, temperature=0.2, max_tokens=3000)
        feature_content, step_definitions = self._parse_output(resp.content)
        matched, new_needed = self._analyze_step_coverage(feature_content)

        return BDDOutput(
            feature_content=feature_content,
            step_definitions=step_definitions,
            matched_existing_steps=matched,
            new_steps_needed=new_needed,
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    def _load_existing_steps(self) -> list[str]:
        steps: list[str] = []
        steps_dir = _ENGINE_ROOT / "steps"
        if not steps_dir.exists():
            return steps
        for py_file in steps_dir.rglob("*.py"):
            try:
                content = py_file.read_text(errors="replace")
            except OSError:
                continue
            patterns = re.findall(r"@(?:given|when|then)\(['\"](.+?)['\"]\)", content)
            steps.extend(patterns)
        return sorted(set(steps))

    @staticmethod
    def _parse_output(raw: str) -> tuple[str, str]:
        feature_match = re.search(r"(?:FEATURE|```gherkin)(.*?)(?:STEPS|```)", raw, re.DOTALL)
        steps_match = re.search(r"(?:STEPS|```python)(.*?)(?:```|$)", raw, re.DOTALL)
        feature = feature_match.group(1).strip() if feature_match else raw.strip()
        steps = steps_match.group(1).strip() if steps_match else ""
        return feature, steps

    def _analyze_step_coverage(self, feature: str) -> tuple[list[str], list[str]]:
        feature_steps = re.findall(r"(?:Given|When|Then|And|But)\s+(.+)", feature)
        matched: list[str] = []
        new_needed: list[str] = []
        for step in feature_steps:
            if any(self._step_matches(step, existing) for existing in self.existing_steps):
                matched.append(step)
            else:
                new_needed.append(step)
        return matched, new_needed

    @staticmethod
    def _step_matches(feature_step: str, existing_pattern: str) -> bool:
        regex = re.sub(r"\{[^}]+\}", ".+", existing_pattern)
        return bool(re.match(regex, feature_step.strip()))
