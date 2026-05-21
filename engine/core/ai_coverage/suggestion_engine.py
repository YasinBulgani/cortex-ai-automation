"""
TestSuggestionEngine — Coverage boşluklarından otomatik test kodu önerisi üretir.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

from core.ai_coverage.gap_analyzer import CoverageGap

logger = logging.getLogger(__name__)


@dataclass
class TestSuggestion:
    gap: CoverageGap
    framework: str  # playwright, pytest, k6
    code: str
    confidence: float


class TestSuggestionEngine:
    """Coverage gap'lerinden test kodu üretici."""

    def suggest(
        self,
        gaps: list[CoverageGap],
        framework: str = "playwright",
    ) -> list[TestSuggestion]:
        """Her gap için test kodu önerisi üret."""
        suggestions = []
        for gap in gaps:
            code = self._generate_test_code(gap, framework)
            suggestions.append(TestSuggestion(
                gap=gap,
                framework=framework,
                code=code,
                confidence=0.7 if gap.area == "api" else 0.5,
            ))
        return suggestions

    def suggest_with_ai(
        self,
        gaps: list[CoverageGap],
        framework: str = "playwright",
    ) -> list[TestSuggestion]:
        """LLM ile daha akıllı test kodu üretimi."""
        from core.llm_bridge import call_llm

        suggestions = []

        for gap in gaps[:10]:
            prompt = (
                f"Framework: {framework}\n"
                f"Eksik test alanı: {gap.area}\n"
                f"Hedef: {gap.target}\n"
                f"Açıklama: {gap.description}\n\n"
                f"{framework} ile bu alanı kapsayacak test kodu üret.\n"
                "Sadece çalıştırılabilir kod döndür."
            )

            try:
                code = call_llm(
                    [
                        {"role": "system", "content": f"Sen {framework} test uzmanısın."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                )
                if code.startswith("```"):
                    lines = code.split("\n")
                    code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

                suggestions.append(TestSuggestion(
                    gap=gap,
                    framework=framework,
                    code=code,
                    confidence=0.75,
                ))
            except Exception as e:
                logger.error("AI test suggestion failed for %s: %s", gap.target, e)

        return suggestions

    def _generate_test_code(self, gap: CoverageGap, framework: str) -> str:
        """Şablon tabanlı test kodu üretimi."""
        if framework == "playwright" and gap.area == "api":
            method, path = "GET", gap.target
            if " " in gap.target:
                method, path = gap.target.split(" ", 1)
            return _api_test_template(method, path)
        elif framework == "playwright" and gap.area == "ui":
            return _ui_test_template(gap.target)
        return f"# TODO: {gap.description}"


def _api_test_template(method: str, path: str) -> str:
    func_name = path.strip("/").replace("/", "_").replace("{", "").replace("}", "")
    return f'''import {{ test, expect }} from '@playwright/test';

test('{method} {path}', async ({{ request }}) => {{
  const response = await request.{method.lower()}('{path}');
  expect(response.ok()).toBeTruthy();
  expect(response.status()).toBe(200);
  const body = await response.json();
  expect(body).toBeDefined();
}});
'''


def _ui_test_template(target: str) -> str:
    return f'''import {{ test, expect }} from '@playwright/test';

test('{target} page loads', async ({{ page }}) => {{
  await page.goto('/{target.lower().replace(" ", "-")}');
  await expect(page).toHaveTitle(/.*/);
  // TODO: Add specific assertions
}});
'''
