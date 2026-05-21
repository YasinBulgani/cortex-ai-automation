"""
Doğal dil gereksinimden test kodu üreten servis.

Desteklenen framework'ler: pytest-bdd, playwright-ts, pytest
Page Object repository'si ve framework kuralları ile LLM context'i zenginleştirir.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from .llm_gateway import LLMGateway

_ENGINE_ROOT = Path(__file__).resolve().parent.parent


SYSTEM_PROMPT = """\
Sen TestwrightAI Test Platformu için test kodu üreten bir AI asistanısın.

Kurallar:
1. data-testid locator'ları kullan (pattern: {screen}-{element-type}-{identifier})
2. BasePage'den türeyen page object'lere referans ver
3. Türkçe senaryo isimleri kullan
4. Her test tek bir kullanıcı akışını doğrulasın
5. Assertion'lar page object metotları içinde olsun
6. Hardcoded değer kullanma — test data fixture'larından al
7. Locator öncelik sırası: data-testid > getByRole > getByLabel > getByText
"""


@dataclass
class GeneratedTest:
    framework: str
    code: str
    file_path: str
    validation_passed: bool
    validation_errors: list[str] = field(default_factory=list)


class AITestGenerator:
    """Doğal dil → çalıştırılabilir test kodu."""

    def __init__(self, gateway: LLMGateway, model: str | None = None):
        self.gateway = gateway
        self.model = model or "gpt-4o"

    def generate_from_requirement(
        self,
        requirement: str,
        framework: str = "pytest-bdd",
        page_objects: list[str] | None = None,
    ) -> GeneratedTest:
        context = self._build_context(framework, page_objects)
        po_summary = self._scan_page_objects(framework)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\n" + po_summary},
            {"role": "user", "content": f"{context}\n\nGereksinim: {requirement}"},
        ]

        resp = self.gateway.complete(messages, model=self.model, temperature=0.2, max_tokens=3000)
        code = self._extract_code_blocks(resp.content)
        file_path = self._determine_file_path(requirement, framework)
        errors = self._validate_code(code, framework)

        return GeneratedTest(
            framework=framework,
            code=code,
            file_path=file_path,
            validation_passed=len(errors) == 0,
            validation_errors=errors,
        )

    # ── helpers ─────────────────────────────────────────────────────────────

    def _build_context(self, framework: str, page_objects: list[str] | None) -> str:
        parts = [f"Framework: {framework}"]
        if page_objects:
            parts.append(f"Kullanılacak Page Object'ler: {', '.join(page_objects)}")
        if framework == "pytest-bdd":
            parts.append("Çıktı formatı: Gherkin feature dosyası + Python step definitions")
        elif framework == "playwright-ts":
            parts.append("Çıktı formatı: TypeScript Playwright spec dosyası (.spec.ts)")
        else:
            parts.append("Çıktı formatı: Python pytest test fonksiyonu")
        return "\n".join(parts)

    def _scan_page_objects(self, framework: str) -> str:
        """Mevcut page object'lerin özetini döndürür."""
        lines: list[str] = ["Mevcut Page Object'ler:"]

        if framework == "playwright-ts":
            pages_dir = _ENGINE_ROOT.parent / "e2e" / "pages"
        else:
            pages_dir = _ENGINE_ROOT / "pages"

        if not pages_dir.exists():
            return ""

        suffix = ".ts" if framework == "playwright-ts" else ".py"
        for f in sorted(pages_dir.glob(f"*{suffix}")):
            if f.name.startswith("_") or f.name == "index.ts":
                continue
            lines.append(f"  - {f.stem}")

        return "\n".join(lines) if len(lines) > 1 else ""

    @staticmethod
    def _extract_code_blocks(raw: str) -> str:
        blocks: list[str] = []
        in_block = False
        buf: list[str] = []
        for line in raw.split("\n"):
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            if line.startswith("```") and in_block:
                in_block = False
                blocks.append("\n".join(buf))
                buf = []
                continue
            if in_block:
                buf.append(line)
        if buf:
            blocks.append("\n".join(buf))
        return "\n\n# ---\n\n".join(blocks) if blocks else raw

    @staticmethod
    def _determine_file_path(requirement: str, framework: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "_", requirement[:60].lower()).strip("_")
        if framework == "pytest-bdd":
            return f"engine/features/ai_generated/{slug}.feature"
        if framework == "playwright-ts":
            return f"e2e/ai-generated/{slug}.spec.ts"
        return f"engine/tests/ai_generated/test_{slug}.py"

    @staticmethod
    def _validate_code(code: str, framework: str) -> list[str]:
        errors: list[str] = []
        if framework in ("pytest-bdd", "pytest"):
            for i, block in enumerate(code.split("# ---")):
                block = block.strip()
                if not block or block.startswith("Feature:") or block.startswith("Senaryo"):
                    continue
                try:
                    ast.parse(block)
                except SyntaxError as exc:
                    errors.append(f"Blok {i}: Python syntax hatası — {exc}")
        return errors
