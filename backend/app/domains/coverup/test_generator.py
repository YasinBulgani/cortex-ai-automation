"""
CoverUp Test Generator — Kapsanmayan kod için AI destekli test uretimi.

Akis:
  1. Coverage gap'lerini al (GapDetector'dan)
  2. Her gap için kaynak kodu oku (varsa)
  3. LLM'e gönder: "Bu kapsanmayan kod için test yaz"
  4. Framework'e uygun test kodu üret (Playwright/pytest/Jest/Vitest)
  5. Uretilen testlerin syntax dogrulamasini yap
"""
from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from app.config import settings
from app.domains.agents.banking_team.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)

# Proje koku — coverup/ backend/app/domains/coverup/test_generator.py
REPO_ROOT = Path(__file__).resolve().parents[4]

# ── Framework bazli system prompt'lari ──────────────────────────────────────

SYSTEM_PLAYWRIGHT = """\
Sen kidemli bir Playwright Test Muhendisisin.
Kapsanmayan UI kodu için Playwright TypeScript testleri yaz.

## Kurallar
- TypeScript kullan, async/await pattern
- Page Object Model (POM) tercih et
- data-testid > role > aria-label > text sırasında secici kullan
- Her test bagimsiz olmali (beforeEach ile setup)
- expect() ile guclu assertion'lar: toBeVisible, toHaveText, toContainText
- Turkce yorum satirlari, Ingilizce kod
- KVKK/PCI-DSS uyumlu veri maskeleme test'leri ekle (bankaci baglam varsa)

## Cikti Formati
MUTLAKA asagidaki JSON formatinda yanıt ver:
{
  "test_file": "tests/coverup/<dosya>.spec.ts",
  "test_code": "import { test, expect } from '@playwright/test';\\n...",
  "description": "Bu test neyi kapsiyor",
  "target_lines": [12, 13, 14]
}
"""

SYSTEM_PYTEST = """\
Sen kidemli bir Python Test Muhendisisin.
Kapsanmayan Python API kodu için pytest testleri yaz.

## Kurallar
- pytest + httpx formatinda yaz
- Fixture'larla authentication ve base_url ayarla
- Her test bagimsiz
- Assert + soft assert — status code + response body + schema validation
- Turkce yorum satirlari, Ingilizce kod
- BDDK reguelasyon test'leri ekle (bankaci baglam varsa)
- Mock kullanimi gerektigi yerde pytest-mock veya unittest.mock kullan

## Cikti Formati
MUTLAKA asagidaki JSON formatinda yanıt ver:
{
  "test_file": "tests/coverup/<dosya>_test.py",
  "test_code": "import pytest\\n...",
  "description": "Bu test neyi kapsiyor",
  "target_lines": [12, 13, 14]
}
"""

SYSTEM_JEST = """\
Sen kidemli bir JavaScript/TypeScript Test Muhendisisin.
Kapsanmayan JS/TS kodu için Jest veya Vitest testleri yaz.

## Kurallar
- Modern ES module syntax kullan
- describe/it bloklari ile organize et
- jest.mock() veya vi.mock() ile dependency injection
- expect().toBe/.toEqual/.toThrow ile assertion'lar
- Turkce yorum satirlari, Ingilizce kod
- Async islemler için async/await + resolves/rejects

## Cikti Formati
MUTLAKA asagidaki JSON formatinda yanıt ver:
{
  "test_file": "tests/coverup/<dosya>.test.ts",
  "test_code": "import { describe, it, expect } from 'vitest';\\n...",
  "description": "Bu test neyi kapsiyor",
  "target_lines": [12, 13, 14]
}
"""

_FRAMEWORK_PROMPTS: dict[str, str] = {
    "playwright": SYSTEM_PLAYWRIGHT,
    "pytest": SYSTEM_PYTEST,
    "jest": SYSTEM_JEST,
    "vitest": SYSTEM_JEST,  # Jest ve Vitest ayni prompt'u kullanir
}


class CoverUpTestGenerator(BaseAgent):
    """Kapsanmayan kod için AI destekli test uretici."""

    name = "CoverUp Test Uretici"
    temperature = 0.25
    max_tokens = 6000
    model_fallback = ["mistral:latest", "qwen2.5:32b"]

    @property
    def model(self) -> str:  # type: ignore[override]
        return (
            settings.ollama_model_coder
            if settings.ai_provider == "ollama"
            else settings.openai_model
        )

    # ── Ana giriş noktasi ────────────────────────────────────────────────────

    def run(self, context: dict) -> AgentResult:
        """
        context keys:
          targets          — list[dict]: gap hedefleri (CoverageGapTarget dicts)
          framework        — str: playwright|pytest|jest|vitest
          language         — str: typescript|python
          banking_context  — bool: bankacilik baglamini dahil et
        """
        targets: list[dict] = context.get("targets", [])
        framework: str = context.get("framework", "playwright")
        language: str = context.get("language", "typescript")
        banking_context: bool = context.get("banking_context", True)

        if not targets:
            return AgentResult(
                agent_name=self.name,
                success=False,
                error="Hedef listesi bos — once coverage analizi yapin",
            )

        generated_tests: list[dict[str, Any]] = []
        total_gain = 0.0

        # Maksimum 10 hedef isle
        for target in targets[:10]:
            try:
                result = self._generate_single_test(
                    target, framework, language, banking_context,
                )
                if result and result.get("test_code"):
                    # Syntax dogrulamasi
                    code = result["test_code"]
                    if self._validate_test_syntax(code, language):
                        gain = self._estimate_coverage_gain(target, code)
                        result["estimated_coverage_gain"] = gain
                        total_gain += gain
                        generated_tests.append(result)
                    else:
                        logger.warning(
                            "%s: Syntax dogrulamasi başarısız — %s",
                            self.name, target.get("file_path", "?"),
                        )
                        # Syntax hatali kodu da dondur ama işaretli
                        result["estimated_coverage_gain"] = 0.0
                        result["syntax_valid"] = False
                        generated_tests.append(result)
            except Exception as exc:
                logger.warning(
                    "%s: Hedef için test uretilemedi (%s): %s",
                    self.name, target.get("file_path", "?"), exc,
                )

        self.learn(
            f"CoverUp: {len(generated_tests)} test uretildi, "
            f"tahmini kapsam artisi: {total_gain:.2f}. "
            f"Framework: {framework}, Dil: {language}",
            metadata={"framework": framework, "language": language},
        )

        return AgentResult(
            agent_name=self.name,
            success=len(generated_tests) > 0,
            data={
                "tests": generated_tests,
                "total_generated": len(generated_tests),
                "estimated_total_gain": round(min(total_gain, 0.95), 4),
                "framework": framework,
                "language": language,
            },
        )

    # ── Tekil test uretimi ───────────────────────────────────────────────────

    def _generate_single_test(
        self,
        target: dict,
        framework: str,
        language: str,
        banking_context: bool,
    ) -> dict:
        """Tek bir gap hedefi için LLM'den test kodu üret."""
        file_path = target.get("file_path", "")
        start_line = target.get("start_line", 0)
        end_line = target.get("end_line", 0)
        function_name = target.get("function_name", "")
        risk_factors = target.get("risk_factors", [])
        gap_type = target.get("gap_type", "line")

        # Kaynak kodu oku
        snippet = self._read_source_snippet(file_path, start_line, end_line)

        # System prompt sec
        system_prompt = _FRAMEWORK_PROMPTS.get(framework, SYSTEM_PYTEST)

        # Bankacilik baglami
        banking_block = ""
        if banking_context:
            banking_block = (
                "\n\n## Bankacilik Baglami\n" + self._build_banking_context()
            )

        # User prompt oluştur
        user_prompt = (
            f"Asagidaki kapsanmayan kod için {framework} test(ler)i yaz.\n\n"
            f"## Hedef Dosya\n{file_path}\n\n"
            f"## Kapsanmayan Satirlar\n{start_line}-{end_line} ({gap_type})\n\n"
        )

        if function_name:
            user_prompt += f"## Fonksiyon\n{function_name}\n\n"

        if snippet:
            user_prompt += f"## Kaynak Kod\n```\n{snippet}\n```\n\n"

        if risk_factors:
            user_prompt += (
                "## Risk Faktorleri\n"
                + "\n".join(f"- {rf}" for rf in risk_factors)
                + "\n\n"
            )

        user_prompt += banking_block

        # LLM cagrisi
        result = self.call_json(system_prompt, user_prompt)

        # Sonucu normalize et
        test_code = result.get("test_code", "")
        test_file = result.get("test_file", f"tests/coverup/{Path(file_path).stem}_test.py")
        target_lines = result.get("target_lines", list(range(start_line, end_line + 1)))
        description = result.get("description", "")

        return {
            "target_file": file_path,
            "target_function": function_name or None,
            "test_file_path": test_file,
            "test_code": test_code,
            "test_framework": framework,
            "estimated_coverage_gain": 0.0,
            "lines_targeted": target_lines,
            "description": description,
            "syntax_valid": True,
        }

    # ── Kaynak kod okuma ─────────────────────────────────────────────────────

    def _read_source_snippet(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        context_lines: int = 10,
    ) -> str:
        """Kaynak dosyadan ilgili kod parcasini oku (context satirlariyla)."""
        if not file_path:
            return ""

        full_path = REPO_ROOT / file_path
        if not full_path.is_file():
            # Alternatif: sadece dosya adini dene
            logger.debug("Dosya bulunamadi: %s", full_path)
            return ""

        try:
            lines = full_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            total = len(lines)
            if total == 0:
                return ""

            # Context satirlariyla birlikte oku
            actual_start = max(0, start_line - context_lines - 1)
            actual_end = min(total, end_line + context_lines)

            snippet_lines: list[str] = []
            for i in range(actual_start, actual_end):
                line_num = i + 1
                marker = ">>>" if start_line <= line_num <= end_line else "   "
                snippet_lines.append(f"{marker} {line_num:4d} | {lines[i]}")

            return "\n".join(snippet_lines)
        except Exception as exc:
            logger.debug("Kaynak dosya okunamadi (%s): %s", file_path, exc)
            return ""

    # ── Kapsam kazanimi tahmini ──────────────────────────────────────────────

    def _estimate_coverage_gain(self, target: dict, test_code: str) -> float:
        """Uretilen testin tahmini kapsam kazanimini hesapla."""
        start_line = target.get("start_line", 0)
        end_line = target.get("end_line", 0)
        targeted_lines = max(1, end_line - start_line + 1)

        # Toplam missed lines'i al (varsa)
        missed_total = target.get("missed_lines", targeted_lines * 5)
        if missed_total <= 0:
            missed_total = targeted_lines * 5

        # Kaba tahmin: hedeflenen satirlar / toplam kapsanmayan satirlar
        gain = targeted_lines / missed_total

        # Test kodunun uzunlugu da bir gosterge — uzun test daha fazla satir kapsar
        test_lines = len(test_code.splitlines())
        if test_lines > 30:
            gain *= 1.1  # Uzun test = daha fazla kapsam
        elif test_lines < 5:
            gain *= 0.5  # Cok kisa test = supe

        return round(min(gain, 0.95), 4)

    # ── Syntax dogrulama ─────────────────────────────────────────────────────

    def _validate_test_syntax(self, code: str, language: str) -> bool:
        """Uretilen test kodunun syntax'ini dogrula."""
        if not code or not code.strip():
            return False

        if language == "python":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False

        # TypeScript/JavaScript için basit sezgisel kontrol
        # Tam bir TS parser olmadan temel yapisal kontrol
        code_lower = code.lower()
        required_markers = ["import", "test", "expect"]
        if language in ("typescript", "javascript"):
            matches = sum(1 for m in required_markers if m in code_lower)
            # En az 2 anahtar kelime bulunmali
            if matches < 2:
                return False
            # Denge kontrolu: acilan/kapanan parantez ve suslu parantez
            if code.count("{") != code.count("}"):
                return False
            if abs(code.count("(") - code.count(")")) > 2:
                return False
            return True

        # Bilinmeyen dil — kabul et
        return True

    # ── Bankacilik baglam bilgisi ────────────────────────────────────────────

    def _build_banking_context(self) -> str:
        """Bankacilik domainine ozgu test ipuclari."""
        return (
            "Bu bir bankacilik uygulamasidir. Test yazarken su konulara dikkat et:\n"
            "- KVKK (Kişisel Verilerin Korunmasi Kanunu): "
            "Kişisel veri maskeleme testleri ekle. TC Kimlik, IBAN, telefon vb.\n"
            "- PCI-DSS: Kart bilgisi isleyen alanlarda veri sizdirmama testleri.\n"
            "- BDDK Reguelasyonlari: Finansal islem limitleri, "
            "cift dogrulama (2FA) testleri.\n"
            "- Audit Trail: Kritik islemlerin loglandigini dogrula.\n"
            "- Idempotency: Ayni islemin tekrar gonderildiginde hata vermedigini test et.\n"
            "- Concurrency: Ayni hesaba es zamanli erisim testleri.\n"
            "- Negatif senaryolar: Yetersiz bakiye, geçersiz IBAN, "
            "sure dolmus token gibi hata durumlari."
        )
