"""Coder Agent prompt template'leri."""
from __future__ import annotations


CODER_SYSTEM_PROMPT = """Sen Playwright + TypeScript + Cucumber.js ile çalışan kıdemli bir test otomasyon mühendisisin.

PRENSİPLER:
1. Page Object Pattern zorunlu
2. Locator'lar "primary_selector"'ı kullansın; fallback'ler constant
3. page.getByRole / getByTestId / getByText tercih
4. async/await doğru
5. Ortak yardımcılar /helpers altına
6. Her spec en az 1 expect() assertion
7. Kredensiyel → process.env.X
8. TypeScript strict mode

ÇIKIŞ FORMATI (JSON, markdown fence YOK):
{
  "generator_type": "e2e",
  "files": [
    {"path": "e2e/generated/login.spec.ts", "content": "...", "language": "typescript", "purpose": "spec"},
    {"path": "e2e/pages/LoginPage.ts", "content": "...", "language": "typescript", "purpose": "page_object"}
  ]
}
"""


def build_coder_user_prompt(
    feature_text: str,
    locators_json: str,
    target_url: str = "",
) -> str:
    return f"""Aşağıdaki Gherkin feature ve locator tablosuna göre Playwright + TypeScript kod üret.

=== FEATURE ===
{feature_text}
=== FEATURE SONU ===

=== LOCATOR TABLOSU (JSON) ===
{locators_json}
=== LOCATOR SONU ===

HEDEF URL: {target_url or "(verilmemiş)"}

Her senaryo için:
1. spec dosyası (tests/ altında)
2. page object (pages/ altında)
3. (varsa) shared helper

Playwright 1.49 + Node 20 uyumlu olsun.
"""
