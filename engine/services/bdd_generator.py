"""
Doğal dil gereksinimlerden Gherkin BDD senaryoları üreten servis.

Mevcut step definition kütüphanesini tarar ve step reuse'u maksimize eder.
Self-refine döngüsü: geçersiz Gherkin çıktısında LLM'e hataları geri gönderir
(max 2 tur). _base_generator.refine_generate() kullanır.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from ._base_generator import refine_generate, validate_gherkin
from .llm_gateway import LLMGateway
from .prompt_loader import get_engine_prompt

logger = logging.getLogger(__name__)

_ENGINE_ROOT = Path(__file__).resolve().parent.parent
BDD_SYSTEM_PROMPT = get_engine_prompt("bdd_generator")


_BDD_REFINE_PROMPT = """\
Önceki Gherkin çıktısı şu sorunları içeriyor:

{errors}

Aynı gereksinim için Gherkin feature dosyasını bu sorunları gidererek YENİDEN YAZ.
Çıktı kuralı aynı: FEATURE: ve STEPS: bölümleri, Gherkin formatı, Türkçe başlıklar.
"""


@dataclass
class BDDOutput:
    feature_content: str
    step_definitions: str
    matched_existing_steps: list[str] = field(default_factory=list)
    new_steps_needed: list[str] = field(default_factory=list)
    refine_iterations: int = 0
    validation_errors: list[str] = field(default_factory=list)


class BDDGenerator:
    """Doğal dil → Gherkin feature + step definitions (self-refine destekli)."""

    DEFAULT_MAX_REFINE = 2

    def __init__(self, gateway: LLMGateway, model: str | None = None, max_refine: int | None = None):
        self.gateway = gateway
        self.model = model or "gpt-4o"
        self.max_refine = max_refine if max_refine is not None else self.DEFAULT_MAX_REFINE
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

        raw, errors, refines = refine_generate(
            call_fn=lambda msgs: self.gateway.complete(
                msgs, model=self.model, temperature=0.2, max_tokens=3000
            ).content,
            messages=messages,
            validate_fn=validate_gherkin,
            refine_prompt=_BDD_REFINE_PROMPT,
            max_refine=self.max_refine,
            tag="BDDGenerator",
        )

        feature_content, step_definitions = self._parse_output(raw)
        matched, new_needed = self._analyze_step_coverage(feature_content)

        return BDDOutput(
            feature_content=feature_content,
            step_definitions=step_definitions,
            matched_existing_steps=matched,
            new_steps_needed=new_needed,
            refine_iterations=refines,
            validation_errors=errors,
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
